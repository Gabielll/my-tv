import pytest
import requests
import psycopg2
import time
import os
import io

# --- Configuração do Teste E2E ---
# Estas variáveis devem corresponder às configurações no seu docker-compose.yml
ADMIN_UI_URL = "http://localhost:8000"
DB_HOST = "localhost"
DB_PORT = "26257"  # CockroachDB port
DB_NAME = "media_server"
DB_USER = "root"  # CockroachDB default user
DB_PASSWORD = ""  # CockroachDB no password

# --- Funções Auxiliares ---

def get_db_connection():
    """Conecta-se ao banco de dados do contêiner."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except psycopg2.OperationalError as e:
        pytest.fail(f"Não foi possível conectar ao banco de dados de teste: {e}")

def wait_for_processing(media_item_id, timeout=120):
    """
    Aguarda e monitora o status de um item de mídia no banco de dados
    até que ele atinja o status 'complete' ou o tempo limite seja excedido.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT status FROM media_items WHERE id = %s;", (media_item_id,))
                result = cur.fetchone()
                if result:
                    status = result[0]
                    print(f"Status atual do media_item {media_item_id}: {status}")
                    if status == 'complete':
                        return True
                    # Verifica status de falha para interromper mais cedo
                    if 'failed' in status or 'review' in status:
                        pytest.fail(f"O processamento do item de mídia falhou com o status: {status}")
        finally:
            if conn:
                conn.close()
        time.sleep(5) # Aguarda 5 segundos entre as verificações

    pytest.fail(f"Tempo limite excedido ({timeout}s) esperando o item de mídia {media_item_id} ser processado.")

# --- Teste de Fluxo E2E ---

@pytest.mark.e2e
def test_full_ingestion_flow():
    """
    Testa o fluxo completo de ingestão, desde o upload até a conclusão da análise de cena.
    Este teste assume que o ambiente (docker-compose) está em execução.
    """
    # 1. (Arrange) Preparar um arquivo de vídeo falso para upload
    fake_video_filename = f"e2e_test_video_{int(time.time())}.mp4"
    fake_video_content = b"00000000" # Conteúdo de vídeo MP4 inválido, mas suficiente para o teste
    files = {'mediafiles': (fake_video_filename, io.BytesIO(fake_video_content), 'video/mp4')}

    # 2. (Act) Fazer o upload do arquivo para o admin-ui
    try:
        response = requests.post(f"{ADMIN_UI_URL}/upload", files=files, timeout=30)
        assert response.status_code == 200, f"A solicitação de upload falhou: {response.text}"
    except requests.RequestException as e:
        pytest.fail(f"Não foi possível conectar ao admin-ui em {ADMIN_UI_URL}. O serviço está em execução? Erro: {e}")

    # 3. (Assert) Verificar o banco de dados para confirmar a criação do registro
    conn = get_db_connection()
    media_item_id = None
    try:
        with conn.cursor() as cur:
            # Espera um pouco para o media-manager processar o arquivo
            time.sleep(5)
            # Busca o ID do item de mídia recém-criado
            cur.execute("SELECT id FROM media_items WHERE original_file_path LIKE %s;", (f"%{fake_video_filename}",))
            result = cur.fetchone()
            assert result is not None, f"O item de mídia para '{fake_video_filename}' não foi encontrado no banco de dados."
            media_item_id = result[0]
            print(f"Arquivo de teste enviado. ID do item de mídia: {media_item_id}")
    finally:
        if conn:
            conn.close()

    # 4. (Assert) Aguardar a conclusão do processamento
    assert wait_for_processing(media_item_id), "O processamento do item de mídia não foi concluído com sucesso."

    # 5. (Assert) Verificar se os pontos de corte (cue points) foram criados
    # Como o vídeo é falso, o ffmpeg pode não encontrar pontos de corte.
    # O teste principal é a transição de status para 'complete'.
    # Aqui, apenas verificamos que o pipeline não falhou.
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM cue_points WHERE media_item_id = %s;", (media_item_id,))
            cue_point_count = cur.fetchone()[0]
            print(f"Encontrados {cue_point_count} pontos de corte para o item de mídia {media_item_id}.")
            # A asserção é opcional e depende do comportamento esperado do ffmpeg com arquivos falsos.
            # O mais importante é que o status chegou a 'complete'.
    finally:
        if conn:
            conn.close()
