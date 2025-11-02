import os
import re
import json
import logging
import psycopg2
import requests
import sys
from dotenv import load_dotenv

# Adiciona o diretório pai ao sys.path para permitir a importação de 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import rabbitmq_client

# --- Configuração ---
load_dotenv()  # Carrega variáveis de ambiente de um arquivo .env

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'media_server')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
TMDB_API_KEY = os.getenv('TMDB_API_KEY', 'YOUR_API_KEY') # Chave da API do The Movie Database

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

# --- Lógica de Análise e Enriquecimento ---

def parse_filename(filename):
    """
    Tenta extrair informações de série (título, temporada, episódio) ou filme de um nome de arquivo.
    Exemplos: 'Power.Rangers.S01E01.mkv', 'The.Matrix.1999.1080p.mkv'
    """
    # Regex para séries (ex: S01E01)
    series_match = re.search(r'^(.*?)[._\s]S(\d{2})E(\d{2})', filename, re.IGNORECASE)
    if series_match:
        title = series_match.group(1).replace('.', ' ').strip()
        season = int(series_match.group(2))
        episode = int(series_match.group(3))
        return {'type': 'series', 'title': title, 'season': season, 'episode': episode}

    # Regex para filmes (ex: 1999)
    movie_match = re.search(r'^(.*?)[._\s](\d{4})', filename)
    if movie_match:
        title = movie_match.group(1).replace('.', ' ').strip()
        year = int(movie_match.group(2))
        return {'type': 'movie', 'title': title, 'year': year}

    # Fallback: considera tudo como filme sem ano
    title = os.path.splitext(filename)[0].replace('.', ' ').strip()
    return {'type': 'movie', 'title': title, 'year': None}


def fetch_metadata_from_tmdb(parsed_info):
    """Busca metadados no TMDB com base nas informações analisadas."""
    if TMDB_API_KEY == 'YOUR_API_KEY':
        logging.warning("TMDB_API_KEY não configurada. Usando dados de placeholder.")
        return {'source': 'placeholder', 'data': 'Metadados de exemplo'}

    base_url = "https://api.themoviedb.org/3"
    params = {'api_key': TMDB_API_KEY, 'language': 'pt-BR'}

    try:
        if parsed_info['type'] == 'series':
            # 1. Buscar a série para obter o ID
            search_url = f"{base_url}/search/tv"
            params['query'] = parsed_info['title']
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            search_results = response.json().get('results')
            if not search_results:
                return None
            series_id = search_results[0]['id']

            # 2. Buscar detalhes do episódio específico
            episode_url = f"{base_url}/tv/{series_id}/season/{parsed_info['season']}/episode/{parsed_info['episode']}"
            response = requests.get(episode_url, params=params)
            response.raise_for_status()
            return response.json()

        elif parsed_info['type'] == 'movie':
            search_url = f"{base_url}/search/movie"
            params['query'] = parsed_info['title']
            if parsed_info.get('year'):
                params['year'] = parsed_info['year']

            response = requests.get(search_url, params=params)
            response.raise_for_status()
            search_results = response.json().get('results')
            return search_results[0] if search_results else None

    except requests.RequestException as e:
        logging.error(f"Erro ao chamar a API do TMDB: {e}")
    return None


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
        # A mensagem será rejeitada e não será re-enfileirada se a conexão com o BD falhar
        raise Exception("Não foi possível conectar ao banco de dados.")

    job_successful = False
    try:
        with conn.cursor() as cur:
            # Marca o item como 'processing' para evitar trabalho duplicado
            cur.execute("UPDATE media_items SET status = 'enriching' WHERE id = %s;", (media_item_id,))
            conn.commit()

            # 1. Obter o nome do arquivo do BD
            cur.execute("SELECT original_file_path FROM media_items WHERE id = %s;", (media_item_id,))
            result = cur.fetchone()
            if not result:
                logging.error(f"media_item_id {media_item_id} não encontrado no banco de dados.")
                return

            original_filename = os.path.basename(result[0])

            # 2. Analisar o nome do arquivo
            parsed_info = parse_filename(original_filename)
            logging.info(f"Informações analisadas: {parsed_info}")

            # 3. Buscar metadados externos
            metadata = fetch_metadata_from_tmdb(parsed_info)

            # 4. Atualizar o BD
            if metadata:
                new_title = metadata.get('title') or metadata.get('name', parsed_info['title'])
                synopsis = metadata.get('overview', '')
                tags = metadata.get('genres', [])  # TMDB usa 'genres'

                cur.execute(
                    """
                    UPDATE media_items
                    SET title = %s, synopsis = %s, tags = %s, metadata = %s, status = %s
                    WHERE id = %s;
                    """,
                    (new_title, synopsis, json.dumps(tags), json.dumps(metadata), 'pending_normalization', media_item_id)
                )
                logging.info(f"Metadados para '{new_title}' (ID: {media_item_id}) atualizados com sucesso.")
                job_successful = True
            else:
                cur.execute(
                    "UPDATE media_items SET status = %s WHERE id = %s;",
                    ('needs_review', media_item_id)
                )
                logging.warning(f"Não foram encontrados metadados para o ID: {media_item_id}. Marcado como 'needs_review'.")
                # Consideramos 'needs_review' como um final de pipeline para este item, não um erro.

            conn.commit()

            # 5. Publicar na próxima fila se o enriquecimento foi bem-sucedido
            if job_successful:
                rabbitmq_client.publish_message('normalization_jobs', str(media_item_id))

    except Exception as e:
        logging.error(f"Erro ao processar o media_item_id {media_item_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logging.info("Metadata Enricher iniciado.")
    rabbitmq_client.start_consumer('enrichment_jobs', process_message)
