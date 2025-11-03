import os
import subprocess
import re
import psycopg2
import sys

# Adiciona o diretório pai ao sys.path para permitir a importação de 'shared'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared import rabbitmq_client
from shared.db import get_db_connection
from shared.logging_config import configure_logging, get_logger, generate_correlation_id, CorrelationContext
from shared.config import Config

# --- Configuração ---
service_config = Config.get_service_config()

# Configure logging
configure_logging(service_config['name'])
logger = get_logger(service_config['name'])

# --- Lógica do Worker ---
def analyze_scenes(file_path):
    """
    Usa ffmpeg com o filtro 'blackdetect' para encontrar períodos de silêncio/preto.
    """
    if not os.path.exists(file_path):
        logger.error(
            "Input file not found for scene analysis",
            context={'file_path': file_path},
            severity="operational"
        )
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
        import time
        start_time = time.time()
        
        logger.info(
            "Starting scene analysis",
            context={
                'file_path': file_path,
                'ffmpeg_command': ' '.join(command)
            }
        )
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = process.communicate()[1]

        for line in output.splitlines():
            if 'black_start' in line:
                match = re.search(r'black_start:(\d+\.\d+)', line)
                if match:
                    cue_points.append(float(match.group(1)))

        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Scene analysis completed",
            context={
                'file_path': file_path,
                'cue_points_found': len(cue_points),
                'cue_points': cue_points
            },
            duration_ms=duration_ms
        )

        return cue_points

    except FileNotFoundError:
        logger.error(
            "FFmpeg command not found for scene analysis",
            context={'file_path': file_path},
            severity="critical"
        )
        return []
    except Exception as e:
        logger.error(
            "Exception occurred during scene analysis",
            error=e,
            context={'file_path': file_path},
            severity="operational"
        )
        return []


def process_message(message_body):
    """Função de callback que processa uma mensagem da fila."""
    try:
        media_item_id = int(message_body)
    except (ValueError, TypeError):
        logger.error(
            "Invalid media item ID received",
            context={'message_body': str(message_body)},
            severity="operational"
        )
        return

    # Generate correlation ID for this processing task
    correlation_id = generate_correlation_id()
    with CorrelationContext(correlation_id):
        logger.info(
            "Starting scene analysis processing",
            context={'media_item_id': media_item_id}
        )
        
        conn = get_db_connection()
        if not conn:
            logger.error(
                "Database connection failed for scene analysis",
                context={'media_item_id': media_item_id},
                severity="critical"
            )
            raise Exception("Não foi possível conectar ao banco de dados.")

        try:
            with conn.cursor() as cur:
                # Update status to analyzing
                cur.execute("UPDATE media_items SET status = 'analyzing' WHERE id = %s;", (media_item_id,))
                conn.commit()
                
                logger.info(
                    "Media item status updated to analyzing",
                    context={'media_item_id': media_item_id}
                )

                # Get file path
                cur.execute("SELECT file_path FROM media_items WHERE id = %s;", (media_item_id,))
                result = cur.fetchone()
                if not result or not result[0]:
                    logger.error(
                        "File path not found for media item",
                        context={'media_item_id': media_item_id},
                        severity="operational"
                    )
                    return

                normalized_path = result[0]
                logger.info(
                    "Starting scene analysis for file",
                    context={
                        'media_item_id': media_item_id,
                        'file_path': normalized_path
                    }
                )
                
                cue_points = analyze_scenes(normalized_path)

                if cue_points:
                    for cue_time in cue_points:
                        cur.execute(
                            "INSERT INTO cue_points (media_item_id, cue_time, cue_type) VALUES (%s, %s, %s);",
                            (media_item_id, cue_time, 'commercial_break')
                        )
                    
                    logger.info(
                        "Cue points inserted into database",
                        context={
                            'media_item_id': media_item_id,
                            'cue_points_count': len(cue_points)
                        }
                    )

                # Update status to complete
                cur.execute("UPDATE media_items SET status = %s WHERE id = %s;", ('processed', media_item_id))
                conn.commit()
                
                logger.info(
                    "Scene analysis completed successfully",
                    context={
                        'media_item_id': media_item_id,
                        'cue_points_found': len(cue_points),
                        'status': 'processed'
                    }
                )
                logger.audit("scene_analysis_completed", str(media_item_id), context={
                    'file_path': normalized_path,
                    'cue_points_count': len(cue_points)
                })

        except Exception as e:
            logger.error(
                "Error processing media item for scene analysis",
                error=e,
                context={'media_item_id': media_item_id},
                severity="operational"
            )
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    logger.info("Scene Analyzer iniciado.")
    rabbitmq_client.start_consumer('scene_analysis_jobs', process_message)
