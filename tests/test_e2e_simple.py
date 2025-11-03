import pytest
import psycopg2
import time
import json

# --- Configuração do Teste E2E ---
DB_HOST = "localhost"
DB_PORT = "26257"  # CockroachDB port
DB_NAME = "media_server"
DB_USER = "root"  # CockroachDB default user
DB_PASSWORD = ""  # CockroachDB no password

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

@pytest.mark.e2e
def test_database_connectivity():
    """
    Testa se conseguimos conectar ao banco de dados e fazer operações básicas.
    """
    conn = get_db_connection()
    timestamp = int(time.time())
    
    try:
        with conn.cursor() as cur:
            # Testar inserção de um item de mídia
            title = f"Test Media Item {timestamp}"
            metadata = {"test": True, "timestamp": timestamp}
            file_path = f"/test/path/{timestamp}.mp4"
            
            cur.execute(
                """
                INSERT INTO media_items (title, status, metadata, file_path)
                VALUES (%s, 'pending', %s, %s)
                RETURNING id;
                """,
                (title, json.dumps(metadata), file_path)
            )
            media_id = cur.fetchone()[0]
            print(f"Criado item de mídia com ID: {media_id}")
            
            # Testar consulta
            cur.execute("SELECT title, status FROM media_items WHERE id = %s;", (media_id,))
            result = cur.fetchone()
            assert result[0] == title
            assert result[1] == 'pending'
            
            # Testar atualização
            cur.execute("UPDATE media_items SET status = 'processed' WHERE id = %s;", (media_id,))
            
            # Verificar atualização
            cur.execute("SELECT status FROM media_items WHERE id = %s;", (media_id,))
            result = cur.fetchone()
            assert result[0] == 'processed'
            
            # Limpar dados de teste
            cur.execute("DELETE FROM media_items WHERE id = %s;", (media_id,))
            
        conn.commit()
        print("Teste de conectividade do banco de dados passou!")
        
    finally:
        conn.close()

@pytest.mark.e2e
def test_full_system_integration():
    """
    Testa a integração completa do sistema sem depender do admin_ui.
    """
    conn = get_db_connection()
    timestamp = int(time.time())
    
    try:
        with conn.cursor() as cur:
            # 1. Simular ingestão de mídia
            media_items = []
            for i in range(3):
                title = f"Integration Test S01E{i+1:02d} {timestamp}"
                metadata = {
                    "series_title": "Integration Test Series",
                    "season_number": 1,
                    "episode_number": i + 1,
                    "duration_seconds": 1800
                }
                file_path = f"/test/integration/{timestamp}_{title}.mp4"
                
                cur.execute(
                    """
                    INSERT INTO media_items (title, status, metadata, file_path)
                    VALUES (%s, 'processed', %s, %s)
                    RETURNING id;
                    """,
                    (title, json.dumps(metadata), file_path)
                )
                media_items.append(cur.fetchone()[0])
            
            # 2. Criar canal de teste
            channel_id = 8888 + timestamp % 1000
            rule_details = {
                "series_linear": {
                    "title": "Integration Test Series",
                    "time_slot": {"hour": 20, "minute": 0}
                }
            }
            program_state = {
                "series_linear": {
                    "Integration Test Series": {"current_season": 1, "current_episode": 1}
                }
            }
            
            cur.execute(
                """
                INSERT INTO channel_master_grid (id, channel_id, channel_name, is_active, rules, program_state)
                VALUES (%s, %s, 'integration_test_channel', true, %s, %s);
                """,
                (channel_id, f"integration_test_{timestamp}", json.dumps(rule_details), json.dumps(program_state))
            )
            
        conn.commit()
        
        # 3. Executar scheduler
        import subprocess
        scheduler_process = subprocess.run(
            ['python', 'scheduler_ai/scheduler.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print("Scheduler output:", scheduler_process.stdout)
        if scheduler_process.stderr:
            print("Scheduler errors:", scheduler_process.stderr)
        
        assert scheduler_process.returncode == 0, f"Scheduler falhou: {scheduler_process.stderr}"
        
        # 4. Verificar resultados
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM epg_virtual WHERE channel_id = %s;", (f"integration_test_{timestamp}",))
            epg_count = cur.fetchone()[0]
            print(f"EPG entries criadas: {epg_count}")
            
            # Verificar se pelo menos uma entrada foi criada
            assert epg_count > 0, "Nenhuma entrada EPG foi criada"
            
            # Limpar dados de teste
            cur.execute("DELETE FROM epg_virtual WHERE channel_id = %s;", (f"integration_test_{timestamp}",))
            cur.execute("DELETE FROM channel_master_grid WHERE id = %s;", (channel_id,))
            cur.execute("DELETE FROM media_items WHERE id = ANY(%s);", (media_items,))
            
        conn.commit()
        print("Teste de integração completa passou!")
        
    finally:
        conn.close()