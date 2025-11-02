import os
import subprocess
import logging
import re
import psycopg2
import sys

# Adiciona o diretório pai ao sys.path para permitir a importação de 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import rabbitmq_client

# --- Configuração ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'media_server')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

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
def analyze_scenes(file_path):
    """
    Usa ffmpeg com o filtro 'blackdetect' para encontrar períodos de silêncio/preto,
    que geralmente indicam breaks comerciais.
    Retorna uma lista de timestamps (em segundos) para os pontos de corte.
    """
    if not os.path.exists(file_path):
        logging.error(f"Arquivo de entrada não encontrado: {file_path}")
        return []

    # Comando ffmpeg:
    # -i: arquivo de entrada
    # -vf blackdetect=...: filtro de vídeo para detectar preto.
    #   - d=1.0: duração mínima do preto para ser detectado (1 segundo)
    #   - pic_th=0.98: limiar para considerar um pixel como preto
    #   - pix_th=0.10: porcentagem de pixels que devem ser pretos
    # -an -f null -: não processa áudio e descarta a saída de vídeo
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

        # O output do blackdetect vai para o stderr
        output = process.communicate()[1]

        # Regex para encontrar as linhas de 'black_start' e 'black_end'
        for line in output.splitlines():
            if 'black_start' in line:
                match = re.search(r'black_start:(\d+\.\d+)', line)
                if match:
                    start_time = float(match.group(1))
                    cue_points.append(start_time)
                    logging.info(f"Ponto de corte detectado (início do preto) em: {start_time}s")

        logging.info(f"Análise de cena concluída para '{file_path}'. Encontrados {len(cue_points)} pontos de corte.")
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
        logging.error(f"A mensagem recebida não é um ID de item de mídia válido: '{message_body}'")
        return

    logging.info(f"Processando media_item_id: {media_item_id}")
    conn = get_db_connection()
    if not conn:
        raise Exception("Não foi possível conectar ao banco de dados.")

    try:
        with conn.cursor() as cur:
            # Marca o item como 'processing'
            cur.execute("UPDATE media_items SET status = 'analyzing' WHERE id = %s;", (media_item_id,))
            conn.commit()

            # 1. Obter o caminho do arquivo normalizado
            cur.execute("SELECT file_path FROM media_items WHERE id = %s;", (media_item_id,))
            result = cur.fetchone()
            if not result or not result[0]:
                logging.error(f"Caminho do arquivo não encontrado para o media_item_id {media_item_id}.")
                return

            normalized_path = result[0]

            # 2. Executar a análise de cena
            cue_points = analyze_scenes(normalized_path)

            # 3. Inserir os pontos de corte no BD
            if cue_points:
                for cue_time in cue_points:
                    cur.execute(
                        "INSERT INTO cue_points (media_item_id, cue_time, cue_type) VALUES (%s, %s, %s);",
                        (media_item_id, cue_time, 'commercial_break')
                    )
                logging.info(f"{len(cue_points)} pontos de corte inseridos no BD para o ID {media_item_id}.")

            # 4. Atualizar o status final do item de mídia
            cur.execute(
                "UPDATE media_items SET status = %s WHERE id = %s;",
                ('complete', media_item_id)
            )
            logging.info(f"ID {media_item_id} processado com sucesso. Status final: 'complete'.")

            conn.commit()

            # O pipeline de ingestão para este item está concluído!
            # O media-manager poderia agora ser notificado para mover o arquivo original.

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
