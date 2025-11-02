import sys
import os
import json

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_db_connection
from scheduler_ai.engine import process_scheduling_rules

def fetch_scheduling_rules(conn):
    """
    Busca as regras de agendamento do banco de dados.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM channel_master_grid WHERE is_active = true;")
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

def clear_epg_for_channels(conn, channel_ids):
    """
    Limpa a EPG futura para os canais especificados.
    """
    print(f"Clearing future EPG for channels: {list(channel_ids)}")
    with conn.cursor() as cur:
        # Estamos limpando a partir de agora para não afetar o histórico
        cur.execute(
            "DELETE FROM epg_virtual WHERE channel_id = ANY(%s) AND start_time_virtual >= NOW()",
            (list(channel_ids),)
        )

def save_epg_entries(conn, epg_entries):
    """
    Salva as novas entradas da EPG no banco de dados.
    """
    print(f"Saving {len(epg_entries)} new EPG entries...")
    with conn.cursor() as cur:
        for entry in epg_entries:
            cur.execute(
                """
                INSERT INTO epg_virtual (channel_id, media_item_id, start_time_virtual, end_time_virtual, title, synopsis)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    entry['channel_id'],
                    entry['media_item_id'],
                    entry['start_time_virtual'],
                    entry['end_time_virtual'],
                    entry['title'],
                    entry['synopsis'],
                ),
            )

def update_program_states(conn, updated_states):
    """
    Atualiza o campo program_state para as regras que mudaram.
    """
    print(f"Updating {len(updated_states)} program states...")
    with conn.cursor() as cur:
        for rule_id, new_state in updated_states.items():
            cur.execute(
                "UPDATE channel_master_grid SET program_state = %s WHERE id = %s",
                (json.dumps(new_state), rule_id)
            )

def main():
    """
    Função principal para executar o agendador.
    """
    print("Scheduler AI starting...")
    conn = None
    try:
        conn = get_db_connection()
        print("Database connection established successfully.")

        # 1. Buscar dados do banco de dados
        rules = fetch_scheduling_rules(conn)
        print(f"Found {len(rules)} active scheduling rules.")

        media_items = fetch_media_items(conn)
        print(f"Found {len(media_items)} processed media items.")

        # 2. Chamar o motor de agendamento para gerar a programação
        epg_entries, updated_states = process_scheduling_rules(rules, media_items)

        # 3. Salvar os resultados no banco de dados
        if epg_entries:
            channel_ids_to_clear = {e['channel_id'] for e in epg_entries}
            clear_epg_for_channels(conn, channel_ids_to_clear)
            save_epg_entries(conn, epg_entries)

        if updated_states:
            update_program_states(conn, updated_states)

        conn.commit()
        print("Successfully saved new EPG and program states to the database.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()
