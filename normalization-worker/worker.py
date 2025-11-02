import os
import subprocess
import logging
import time
import psycopg2

# --- Configuração ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'media_server')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
NORMALIZED_DIR = os.getenv('NORMALIZED_DIR', '/mnt/media/normalized')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Funções de Conexão ---
def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Não foi possível conectar ao banco de dados: {e}")
        return None

# --- Lógica do Worker ---
def normalize_media(input_path, output_path):
    """
    Transcodifica um arquivo de mídia para o formato padrão (H.264/AAC em um container MP4)
    usando ffmpeg.
    """
    if not os.path.exists(input_path):
        logging.error(f"Arquivo de entrada não encontrado: {input_path}")
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Comando ffmpeg:
    # -i: arquivo de entrada
    # -c:v libx264: codec de vídeo H.264
    # -preset veryfast: equilíbrio entre velocidade e qualidade
    # -crf 23: qualidade de vídeo (menor é melhor)
    # -c:a aac: codec de áudio AAC
    # -b:a 128k: bitrate de áudio
    # -y: sobrescreve o arquivo de saída se ele existir
    command = [
        'ffmpeg',
        '-i', input_path,
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        output_path
    ]

    try:
        logging.info(f"Iniciando a normalização para: {input_path}")
        # Usamos Popen para não bloquear e poderemos, no futuro, monitorar o progresso
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Loga a saída do ffmpeg (útil para depuração)
        for line in process.stderr:
            logging.debug(f"ffmpeg: {line.strip()}")

        process.wait() # Espera o processo terminar

        if process.returncode == 0:
            logging.info(f"Normalização concluída com sucesso: {output_path}")
            return True
        else:
            logging.error(f"Erro na normalização de '{input_path}'. Código de saída do ffmpeg: {process.returncode}")
            return False

    except FileNotFoundError:
        logging.error("Comando 'ffmpeg' não encontrado. Certifique-se de que o ffmpeg está instalado e no PATH do sistema.")
        return False
    except Exception as e:
        logging.error(f"Uma exceção ocorreu durante a normalização: {e}")
        return False


def process_message(media_item_id):
    """Função principal que processa um item de mídia."""
    logging.info(f"Processando media_item_id: {media_item_id}")
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            # 1. Obter o caminho do arquivo original
            cur.execute("SELECT original_file_path FROM media_items WHERE id = %s;", (media_item_id,))
            result = cur.fetchone()
            if not result:
                logging.error(f"media_item_id {media_item_id} não encontrado.")
                return

            original_path = result[0]

            # 2. Definir o novo caminho e executar a normalização
            filename = os.path.basename(original_path)
            # Troca a extensão para .mp4, que é o nosso container padrão
            base_filename, _ = os.path.splitext(filename)
            normalized_filename = f"{base_filename}.mp4"
            normalized_path = os.path.join(NORMALIZED_DIR, normalized_filename)

            success = normalize_media(original_path, normalized_path)

            # 3. Atualizar o BD
            if success:
                cur.execute(
                    "UPDATE media_items SET file_path = %s, status = %s WHERE id = %s;",
                    (normalized_path, 'pending_analysis', media_item_id)
                )
                logging.info(f"BD atualizado. Novo file_path para ID {media_item_id} é '{normalized_path}'.")
                # TODO: Publicar na próxima fila (scene_analysis_jobs)
                logging.info(f"Ação futura: Publicar 'scene_analysis_job' para o media_item_id: {media_item_id}")
            else:
                cur.execute(
                    "UPDATE media_items SET status = %s WHERE id = %s;",
                    ('normalization_failed', media_item_id)
                )
                logging.error(f"Falha ao normalizar ID {media_item_id}. Status atualizado para 'normalization_failed'.")

            conn.commit()

    except Exception as e:
        logging.error(f"Erro ao processar o media_item_id {media_item_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- Simulação de Consumo de Fila ---
def simulate_queue_consumption():
    """
    Simula o consumo de uma fila, procurando por itens que o metadata-enricher marcou.
    """
    logging.info("Normalization Worker iniciado. Aguardando novos itens de mídia...")

    while True:
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM media_items WHERE status = 'pending_normalization' LIMIT 5;")
                    items_to_process = cur.fetchall()

                if items_to_process:
                    for item in items_to_process:
                        media_item_id = item[0]
                        with conn.cursor() as cur:
                            cur.execute("UPDATE media_items SET status = 'normalizing' WHERE id = %s;", (media_item_id,))
                            conn.commit()

                        process_message(media_item_id)
                else:
                    time.sleep(10)

            except Exception as e:
                logging.error(f"Erro no loop principal: {e}")
                time.sleep(15)
            finally:
                if conn:
                    conn.close()
        else:
            time.sleep(30)


if __name__ == "__main__":
    simulate_queue_consumption()
