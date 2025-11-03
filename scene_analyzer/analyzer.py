import os
import subprocess
import logging
import re
import psycopg2
import sys

# Adiciona o diretório pai ao sys.path para permitir a importação de 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import rabbitmq_client
from shared.db import get_db_connection

# --- Configuração ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Lógica do Worker ---
def analyze_scenes(file_path):
    """
    Usa ffmpeg com o filtro 'blackdetect' para encontrar períodos de silêncio/preto.
    """
    if not os.path.exists(file_path):
        logging.error(f"Arquivo de entrada não encontrado: {file_path}")
        return []

    command = [
        'ffmpeg',
        '-i', file_path,
        '-vf', 'blackdetect=d=1.0:pic_th=0.98:pix_th=0.10',
        '-an',
        '-f', 'null',
        '-'
    ]

    cue_points = []
    try:
        logging.info(f"Iniciando a análise de cena para: {file_path}")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = process.communicate()[1]

        for line in output.splitlines():
            if 'black_start' in line:
                match = re.search(r'black_start:(\d+\.\d+)', line)
                if match:
                    cue_points.append(float(match.group(1)))

        return cue_points

    except FileNotFoundError:
        logging.error("Comando 'ffmpeg' não encontrado.")
        return []
    except Exception as e:
        logging.error(f"Uma exceção ocorreu durante a análise de cena: {e}")
        return []


def process_message(message_body):
    """Função de callback que processa uma mensagem da fila."""
    try:
        media_item_id = int(message_body)
    except (ValueError, TypeError):
        logging.error(f"Mensagem inválida: '{message_body}'")
        return

    logging.info(f"Processando media_item_id: {media_item_id}")
    conn = get_db_connection()
    if not conn:
        raise Exception("Não foi possível conectar ao banco de dados.")

    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE media_items SET status = 'analyzing' WHERE id = %s;", (media_item_id,))
            conn.commit()

            cur.execute("SELECT file_path FROM media_items WHERE id = %s;", (media_item_id,))
            result = cur.fetchone()
            if not result or not result[0]:
                logging.error(f"Caminho do arquivo não encontrado para o media_item_id {media_item_id}.")
                return

            normalized_path = result[0]
            cue_points = analyze_scenes(normalized_path)

            if cue_points:
                for cue_time in cue_points:
                    cur.execute(
                        "INSERT INTO cue_points (media_item_id, cue_time, cue_type) VALUES (%s, %s, %s);",
                        (media_item_id, cue_time, 'commercial_break')
                    )

            cur.execute("UPDATE media_items SET status = %s WHERE id = %s;", ('complete', media_item_id))
            conn.commit()

    except Exception as e:
        logging.error(f"Erro ao processar o media_item_id {media_item_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logging.info("Scene Analyzer iniciado.")
    rabbitmq_client.start_consumer('scene_analysis_jobs', process_message)
