import pytest
import psycopg2
import time
import os
import subprocess
import json
from datetime import datetime
import random

# --- Configuração do Teste E2E ---
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

def cleanup_db(conn, channel_id, media_item_ids):
    """Limpa os dados de teste do banco de dados."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM epg_virtual WHERE channel_id = %s;", (f"e2e_test_channel_{channel_id}",))
        cur.execute("DELETE FROM channel_master_grid WHERE id = %s;", (channel_id,))
        cur.execute("DELETE FROM media_items WHERE id = ANY(%s);", (media_item_ids,))
    conn.commit()

# --- Teste de Fluxo E2E ---

@pytest.mark.e2e
def test_scheduling_flow():
    """
    Testa o fluxo completo de agendamento.
    Este teste assume que o ambiente (docker-compose) está em execução.
    """
    conn = get_db_connection()
    # Usar timestamp para garantir IDs únicos
    timestamp = int(time.time())
    channel_id = 9999 + timestamp % 1000  # ID de teste único para o canal
    media_item_ids = []

    try:
        # 1. (Setup) Inserir dados de teste no banco de dados
        with conn.cursor() as cur:
            # Criar 3 itens de mídia (episódios de uma série)
            for i in range(1, 4):
                title = f"E2E Test Series S01E0{i}"
                metadata = {
                    "series_title": "E2E Test Series",
                    "season_number": 1,
                    "episode_number": i,
                    "duration_seconds": 1800 # 30 minutos
                }
                cur.execute(
                    """
                    INSERT INTO media_items (title, status, metadata, file_path)
                    VALUES (%s, 'processed', %s, %s)
                    RETURNING id;
                    """,
                    (title, json.dumps(metadata), f"/fake/path/{timestamp}_{title}.mp4")
                )
                media_item_ids.append(cur.fetchone()[0])

            # Criar uma regra de agendamento 'series_linear'
            rule_details = {
                "series_linear": {
                    "title": "E2E Test Series",
                    "time_slot": {"hour": datetime.now().hour, "minute": datetime.now().minute}
                }
            }
            program_state = {
                "series_linear": {
                    "E2E Test Series": {"current_season": 1, "current_episode": 1}
                }
            }
            cur.execute(
                """
                INSERT INTO channel_master_grid (id, channel_id, channel_name, is_active, rules, program_state)
                VALUES (%s, %s, 'e2e_test_channel', true, %s, %s);
                """,
                (channel_id, f"e2e_test_channel_{channel_id}", json.dumps(rule_details), json.dumps(program_state))
            )
        conn.commit()
        print(f"Dados de teste inseridos. Canal: {channel_id}, Mídias: {media_item_ids}")

        # 2. (Act) Executar o scheduler_ai como um processo
        # O caminho assume que pytest está sendo executado da raiz do projeto
        scheduler_process = subprocess.run(
            ['python', 'scheduler_ai/scheduler.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        print("Scheduler output:\n", scheduler_process.stdout)
        assert scheduler_process.returncode == 0, f"O processo do scheduler falhou: {scheduler_process.stderr}"

        # 3. (Assert) Verificar os resultados no banco de dados
        with conn.cursor() as cur:
            # Verificar se a EPG foi criada para os próximos 7 dias
            cur.execute("SELECT COUNT(*) FROM epg_virtual WHERE channel_id = %s;", (f"e2e_test_channel_{channel_id}",))
            epg_count = cur.fetchone()[0]
            # O motor do scheduler agenda para 7 dias no futuro
            assert epg_count > 0, "A EPG não foi criada para o canal de teste."
            print(f"Encontradas {epg_count} entradas na EPG.")

            # Verificar se o program_state foi atualizado
            cur.execute("SELECT program_state FROM channel_master_grid WHERE id = %s;", (channel_id,))
            new_program_state = cur.fetchone()[0]

            # O scheduler é executado uma vez e agenda 7 dias, mas o estado só avança uma vez por execução do motor
            # para o propósito deste teste de fluxo único.
            expected_episode = 2
            assert new_program_state['series_linear']['E2E Test Series']['current_episode'] == expected_episode, \
                f"O estado do programa não foi atualizado corretamente. Esperado: {expected_episode}, " \
                f"Obtido: {new_program_state['series_linear']['E2E Test Series']['current_episode']}"
            print("O estado do programa foi atualizado corretamente.")

    finally:
        # 4. (Teardown) Limpar os dados de teste
        print("Limpando dados de teste...")
        cleanup_db(conn, channel_id, media_item_ids)
        conn.close()
