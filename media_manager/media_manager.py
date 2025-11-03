import os
import time
import psycopg2
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Adiciona o diretório pai ao sys.path para permitir a importação de 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import rabbitmq_client
from shared.db import get_db_connection
from shared.logging_config import configure_logging, get_logger, generate_correlation_id, CorrelationContext
from shared.config import Config

# --- Configuração ---
service_config = Config.get_service_config()
media_config = Config.get_media_config()

# Configure logging
configure_logging(service_config['name'])
logger = get_logger(service_config['name'])

STAGING_DIR = media_config['staging_dir']
ALLOWED_EXTENSIONS = set(media_config['allowed_extensions'])

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
            # Generate correlation ID for this file processing
            correlation_id = generate_correlation_id()
            with CorrelationContext(correlation_id):
                logger.info(
                    "New media file detected",
                    context={
                        'filename': filename,
                        'file_path': file_path,
                        'extension': extension,
                        'file_size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    }
                )
                self.process_new_media(file_path)

    def process_new_media(self, file_path):
        """Processa um novo arquivo de mídia: o adiciona ao banco de dados."""
        conn = get_db_connection()
        if not conn:
            logger.error(
                "Database connection failed for media processing",
                context={'file_path': file_path},
                severity="critical"
            )
            return

        try:
            with conn.cursor() as cur:
                # Verifica se o arquivo já existe para evitar duplicatas
                cur.execute("SELECT id FROM media_items WHERE original_file_path = %s;", (file_path,))
                if cur.fetchone():
                    logger.warning(
                        "Duplicate file detected, skipping processing",
                        context={'file_path': file_path}
                    )
                    return

                # Insere o novo item de mídia
                title = os.path.splitext(os.path.basename(file_path))[0]
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
                
                logger.info(
                    "Media item inserted into database",
                    context={
                        'file_path': file_path,
                        'media_item_id': media_item_id,
                        'title': title,
                        'status': 'pending_enrichment'
                    }
                )
                logger.audit("media_item_created", str(media_item_id), context={
                    'file_path': file_path,
                    'title': title
                })

                # Publica uma mensagem na fila para o próximo estágio (enriquecimento)
                message = str(media_item_id)
                rabbitmq_client.publish_message('enrichment_jobs', message)
                
                logger.info(
                    "Message published to enrichment queue",
                    context={
                        'media_item_id': media_item_id,
                        'queue': 'enrichment_jobs'
                    }
                )

        except Exception as e:
            logger.error(
                "Failed to process media file",
                error=e,
                context={'file_path': file_path},
                severity="operational"
            )
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

# --- Execução Principal ---
if __name__ == "__main__":
    if not os.path.exists(STAGING_DIR):
        logger.info(f"O diretório de staging '{STAGING_DIR}' não existe. Criando...")
        os.makedirs(STAGING_DIR)

    logger.info(f"Monitorando o diretório: {STAGING_DIR}")

    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, STAGING_DIR, recursive=True)

    observer.start()
    logger.info("Media Manager iniciado.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Media Manager parado.")

    observer.join()
