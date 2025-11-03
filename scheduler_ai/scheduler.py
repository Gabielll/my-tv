import sys
import os
import json

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_db_connection
from shared.logging_config import configure_logging, get_logger, generate_correlation_id, CorrelationContext
from shared.config import Config
from scheduler_ai.engine import process_scheduling_rules

# --- Configuração ---
service_config = Config.get_service_config()

# Configure logging
configure_logging(service_config['name'])
logger = get_logger(service_config['name'])

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
    logger.info(
        "Clearing future EPG for channels",
        context={
            'channel_ids': list(channel_ids),
            'channel_count': len(channel_ids)
        }
    )
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
    logger.info(
        "Saving EPG entries to database",
        context={
            'entry_count': len(epg_entries),
            'operation': 'epg_save'
        }
    )
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
    logger.info(
        "Updating program states",
        context={
            'state_count': len(updated_states),
            'rule_ids': list(updated_states.keys())
        }
    )
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
    # Generate correlation ID for this scheduling run
    correlation_id = generate_correlation_id()
    with CorrelationContext(correlation_id):
        logger.info("Scheduler AI starting...")
        conn = None
        try:
            conn = get_db_connection()
            logger.info("Database connection established successfully.")

            # 1. Buscar dados do banco de dados
            rules = fetch_scheduling_rules(conn)
            logger.info(
                "Active scheduling rules retrieved",
                context={'rules_count': len(rules)}
            )

            media_items = fetch_media_items(conn)
            logger.info(
                "Processed media items retrieved",
                context={'media_items_count': len(media_items)}
            )

            # 2. Chamar o motor de agendamento para gerar a programação
            logger.info("Starting scheduling engine processing")
            epg_entries, updated_states = process_scheduling_rules(rules, media_items)

            # 3. Salvar os resultados no banco de dados
            if epg_entries:
                channel_ids_to_clear = {e['channel_id'] for e in epg_entries}
                clear_epg_for_channels(conn, channel_ids_to_clear)
                save_epg_entries(conn, epg_entries)
                
                logger.audit("epg_updated", "epg_virtual", context={
                    'entries_count': len(epg_entries),
                    'channels_affected': len(channel_ids_to_clear)
                })

            if updated_states:
                update_program_states(conn, updated_states)
                
                logger.audit("program_states_updated", "channel_master_grid", context={
                    'rules_updated': len(updated_states)
                })

            conn.commit()
            logger.info(
                "Scheduling operation completed successfully",
                context={
                    'epg_entries_created': len(epg_entries) if epg_entries else 0,
                    'program_states_updated': len(updated_states) if updated_states else 0
                }
            )

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                "Scheduling operation failed",
                error=e,
                severity="critical"
            )
        finally:
            if conn:
                conn.close()
                logger.debug("Database connection closed")

if __name__ == "__main__":
    main()
