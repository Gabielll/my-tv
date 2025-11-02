import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_db_connection

def fetch_scheduling_rules(conn):
    """
    Busca as regras de agendamento do banco de dados.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM channel_master_grid;")
        rules = cur.fetchall()
        return rules

def fetch_media_items(conn):
    """
    Busca todos os itens de mídia disponíveis no banco de dados.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM media_items WHERE status = 'processed';")
        media_items = cur.fetchall()
        return media_items

def main():
    """
    Função principal para executar o agendador.
    """
    print("Scheduler AI starting...")
    conn = None
    try:
        conn = get_db_connection()
        print("Database connection established successfully.")

        rules = fetch_scheduling_rules(conn)
        print(f"Found {len(rules)} scheduling rules.")

        media_items = fetch_media_items(conn)
        print(f"Found {len(media_items)} processed media items.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()
