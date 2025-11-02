import os
import time
import logging
import psycopg2
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Adiciona o diretório pai ao sys.path para permitir a importação de 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import rabbitmq_client

# --- Configuração ---
# Obtém as configurações do ambiente ou usa valores padrão
STAGING_DIR = os.getenv('STAGING_DIR', '/mnt/media/staging_ingest')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'media_server')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
ALLOWED_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# --- Funções de Conexão ---
def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
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
        logging.error(f"Não foi possível conectar ao banco de dados: {e}")
        return None

# --- Lógica do Manipulador de Eventos ---
class NewFileHandler(FileSystemEventHandler):
    """Manipula eventos de criação de arquivos no diretório de staging."""

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        filename = os.path.basename(file_path)
        _, extension = os.path.splitext(filename)

        if extension.lower() in ALLOWED_EXTENSIONS:
            logging.info(f"Novo arquivo de mídia detectado: {filename}")
            self.process_new_media(file_path)

    def process_new_media(self, file_path):
        """Processa um novo arquivo de mídia: o adiciona ao banco de dados."""
        conn = get_db_connection()
        if not conn:
            logging.error(f"Não foi possível processar '{file_path}' devido a um erro de conexão com o BD.")
            return

        try:
            with conn.cursor() as cur:
                # Verifica se o arquivo já existe para evitar duplicatas
                cur.execute("SELECT id FROM media_items WHERE original_file_path = %s;", (file_path,))
                if cur.fetchone():
                    logging.warning(f"O arquivo '{file_path}' já existe no banco de dados. Ignorando.")
                    return

                # Insere o novo item de mídia
                # O título é inicialmente o nome do arquivo sem extensão
                title = os.path.splitext(os.path.basename(file_path))[0]

                # O file_path final será definido pelo normalization-worker
                # Por enquanto, usamos um placeholder.
                final_path_placeholder = f"/mnt/media/normalized/{os.path.basename(file_path)}"

                cur.execute(
                    """
                    INSERT INTO media_items (title, original_file_path, file_path, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (title, file_path, final_path_placeholder, 'pending_enrichment')
                )
                media_item_id = cur.fetchone()[0]
                conn.commit()
                logging.info(f"Arquivo '{file_path}' inserido no BD com o ID: {media_item_id}")

                # Publica uma mensagem na fila para o próximo estágio (enriquecimento)
                message = str(media_item_id)
                rabbitmq_client.publish_message('enrichment_jobs', message)

        except Exception as e:
            logging.error(f"Erro ao processar o arquivo '{file_path}': {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

# --- Execução Principal ---
if __name__ == "__main__":
    if not os.path.exists(STAGING_DIR):
        logging.info(f"O diretório de staging '{STAGING_DIR}' não existe. Criando...")
        os.makedirs(STAGING_DIR)

    logging.info(f"Monitorando o diretório: {STAGING_DIR}")

    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, STAGING_DIR, recursive=True)

    observer.start()
    logging.info("Media Manager iniciado.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Media Manager parado.")

    observer.join()
