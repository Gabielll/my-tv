import os
import re
import json
import logging
import time
import psycopg2
import requests
from dotenv import load_dotenv

# --- Configuração ---
load_dotenv() # Carrega variáveis de ambiente de um arquivo .env

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


def process_message(media_item_id):
    """Função principal que processa um item de mídia."""
    logging.info(f"Processando media_item_id: {media_item_id}")
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            # 1. Obter o nome do arquivo do BD
            cur.execute("SELECT title, original_file_path FROM media_items WHERE id = %s;", (media_item_id,))
            result = cur.fetchone()
            if not result:
                logging.error(f"media_item_id {media_item_id} não encontrado no banco de dados.")
                return

            original_filename = os.path.basename(result[1])

            # 2. Analisar o nome do arquivo
            parsed_info = parse_filename(original_filename)
            logging.info(f"Informações analisadas: {parsed_info}")

            # 3. Buscar metadados externos
            metadata = fetch_metadata_from_tmdb(parsed_info)

            # 4. Atualizar o BD
            if metadata:
                new_title = metadata.get('title') or metadata.get('name', parsed_info['title'])
                synopsis = metadata.get('overview', '')
                tags = metadata.get('genres', []) # TMDB usa 'genres'

                cur.execute(
                    """
                    UPDATE media_items
                    SET title = %s, synopsis = %s, tags = %s, metadata = %s, status = %s
                    WHERE id = %s;
                    """,
                    (new_title, synopsis, json.dumps(tags), json.dumps(metadata), 'pending_normalization', media_item_id)
                )
                logging.info(f"Metadados para '{new_title}' (ID: {media_item_id}) atualizados com sucesso.")
            else:
                cur.execute(
                    "UPDATE media_items SET status = %s WHERE id = %s;",
                    ('needs_review', media_item_id)
                )
                logging.warning(f"Não foram encontrados metadados para o ID: {media_item_id}. Marcado como 'needs_review'.")

            conn.commit()

            # TODO: Publicar na próxima fila (normalization_jobs)
            logging.info(f"Ação futura: Publicar 'normalization_job' para o media_item_id: {media_item_id}")

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
    Esta função simula o consumo de uma fila. Em um sistema real,
    isso seria substituído pela lógica do Pika para consumir do RabbitMQ.
    """
    logging.info("Metadata Enricher iniciado. Aguardando novos itens de mídia...")

    while True:
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    # Procura por itens que o media-manager acabou de adicionar
                    cur.execute("SELECT id FROM media_items WHERE status = 'pending_enrichment' LIMIT 10;")
                    items_to_process = cur.fetchall()

                if items_to_process:
                    for item in items_to_process:
                        media_item_id = item[0]
                        # Marca como 'processing' para evitar que outro worker pegue
                        with conn.cursor() as cur:
                            cur.execute("UPDATE media_items SET status = 'enriching' WHERE id = %s;", (media_item_id,))
                            conn.commit()

                        process_message(media_item_id)
                else:
                    # Se não houver nada para fazer, espere um pouco
                    time.sleep(10)

            except Exception as e:
                logging.error(f"Erro no loop principal: {e}")
                time.sleep(15) # Espera mais em caso de erro
            finally:
                if conn:
                    conn.close()
        else:
            # Se não conseguir conectar ao BD, espera antes de tentar novamente
            time.sleep(30)


if __name__ == "__main__":
    # Em uma implementação real, aqui viria a lógica de conexão com RabbitMQ
    # e o início do consumo da fila. Por enquanto, simulamos.
    simulate_queue_consumption()
