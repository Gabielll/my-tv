import os
import subprocess
import logging
import psycopg2
import sys

# Adiciona o diretório pai ao sys.path para permitir a importação de 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import rabbitmq_client
from shared.db import get_db_connection

# --- Configuração ---
NORMALIZED_DIR = os.getenv('NORMALIZED_DIR', '/mnt/media/normalized')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in process.stderr:
            logging.debug(f"ffmpeg: {line.strip()}")

        process.wait()

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


def process_message(message_body):
    """Função de callback que processa uma mensagem da fila."""
    try:
        media_item_id = int(message_body)
    except (ValueError, TypeError):
        logging.error(f"A mensagem recebida não é um ID de item de mídia válido: '{message_body}'")
        return

    logging.info(f"Processando media_item_id: {media_item_id}")
    conn = get_db_connection()
    if not conn:
        raise Exception("Não foi possível conectar ao banco de dados.")

    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE media_items SET status = 'normalizing' WHERE id = %s;", (media_item_id,))
            conn.commit()

            cur.execute("SELECT original_file_path FROM media_items WHERE id = %s;", (media_item_id,))
            result = cur.fetchone()
            if not result:
                logging.error(f"media_item_id {media_item_id} não encontrado.")
                return

            original_path = result[0]

            base_filename, _ = os.path.splitext(os.path.basename(original_path))
            normalized_filename = f"{base_filename}.mp4"
            normalized_path = os.path.join(NORMALIZED_DIR, normalized_filename)

            success = normalize_media(original_path, normalized_path)

            if success:
                cur.execute(
                    "UPDATE media_items SET file_path = %s, status = %s WHERE id = %s;",
                    (normalized_path, 'pending_analysis', media_item_id)
                )
                rabbitmq_client.publish_message('scene_analysis_jobs', str(media_item_id))
            else:
                cur.execute(
                    "UPDATE media_items SET status = %s WHERE id = %s;",
                    ('normalization_failed', media_item_id)
                )

            conn.commit()

    except Exception as e:
        logging.error(f"Erro ao processar o media_item_id {media_item_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logging.info("Normalization Worker iniciado.")
    rabbitmq_client.start_consumer('normalization_jobs', process_message)
