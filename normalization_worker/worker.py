import os
import subprocess
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
media_config = Config.get_media_config()

# Configure logging
configure_logging(service_config['name'])
logger = get_logger(service_config['name'])

NORMALIZED_DIR = media_config['normalized_dir']

# --- Lógica do Worker ---
def normalize_media(input_path, output_path):
    """
    Transcodifica um arquivo de mídia para o formato padrão (H.264/AAC em um container MP4)
    usando ffmpeg.
    """
    if not os.path.exists(input_path):
        logger.error(
            "Input file not found for normalization",
            context={'input_path': input_path},
            severity="operational"
        )
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
        input_size = os.path.getsize(input_path)
        logger.info(
            "Starting media normalization",
            context={
                'input_path': input_path,
                'output_path': output_path,
                'input_size_bytes': input_size,
                'ffmpeg_command': ' '.join(command)
            }
        )
        
        import time
        start_time = time.time()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Log ffmpeg progress periodically
        for line in process.stderr:
            if 'time=' in line:  # Log progress lines
                logger.debug(
                    "FFmpeg progress",
                    context={'progress_line': line.strip(), 'input_path': input_path}
                )

        process.wait()
        duration_ms = (time.time() - start_time) * 1000

        if process.returncode == 0:
            output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            logger.info(
                "Media normalization completed successfully",
                context={
                    'input_path': input_path,
                    'output_path': output_path,
                    'input_size_bytes': input_size,
                    'output_size_bytes': output_size,
                    'compression_ratio': round(output_size / input_size, 2) if input_size > 0 else 0
                },
                duration_ms=duration_ms
            )
            return True
        else:
            logger.error(
                "FFmpeg normalization failed",
                context={
                    'input_path': input_path,
                    'output_path': output_path,
                    'return_code': process.returncode,
                    'stderr': process.stderr.read() if process.stderr else None
                },
                duration_ms=duration_ms,
                severity="operational"
            )
            return False

    except FileNotFoundError:
        logger.error(
            "FFmpeg command not found",
            context={'input_path': input_path},
            severity="critical"
        )
        return False
    except Exception as e:
        logger.error(
            "Exception occurred during normalization",
            error=e,
            context={'input_path': input_path, 'output_path': output_path},
            severity="operational"
        )
        return False


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
            "Starting media normalization processing",
            context={'media_item_id': media_item_id}
        )
        
        conn = get_db_connection()
        if not conn:
            logger.error(
                "Database connection failed for normalization",
                context={'media_item_id': media_item_id},
                severity="critical"
            )
            raise Exception("Não foi possível conectar ao banco de dados.")

        try:
            with conn.cursor() as cur:
                # Update status to normalizing
                cur.execute("UPDATE media_items SET status = 'normalizing' WHERE id = %s;", (media_item_id,))
                conn.commit()
                
                logger.info(
                    "Media item status updated to normalizing",
                    context={'media_item_id': media_item_id}
                )

                # Get original file path
                cur.execute("SELECT original_file_path FROM media_items WHERE id = %s;", (media_item_id,))
                result = cur.fetchone()
                if not result:
                    logger.error(
                        "Media item not found in database",
                        context={'media_item_id': media_item_id},
                        severity="operational"
                    )
                    return

                original_path = result[0]
                base_filename, _ = os.path.splitext(os.path.basename(original_path))
                normalized_filename = f"{base_filename}.mp4"
                normalized_path = os.path.join(NORMALIZED_DIR, normalized_filename)

                logger.info(
                    "Starting normalization process",
                    context={
                        'media_item_id': media_item_id,
                        'original_path': original_path,
                        'normalized_path': normalized_path
                    }
                )

                success = normalize_media(original_path, normalized_path)

                if success:
                    cur.execute(
                        "UPDATE media_items SET file_path = %s, status = %s WHERE id = %s;",
                        (normalized_path, 'pending_analysis', media_item_id)
                    )
                    rabbitmq_client.publish_message('scene_analysis_jobs', str(media_item_id))
                    
                    logger.info(
                        "Normalization completed successfully, queued for analysis",
                        context={
                            'media_item_id': media_item_id,
                            'normalized_path': normalized_path,
                            'next_queue': 'scene_analysis_jobs'
                        }
                    )
                    logger.audit("media_normalized", str(media_item_id), context={
                        'original_path': original_path,
                        'normalized_path': normalized_path
                    })
                else:
                    cur.execute(
                        "UPDATE media_items SET status = %s WHERE id = %s;",
                        ('normalization_failed', media_item_id)
                    )
                    logger.error(
                        "Normalization failed, status updated to failed",
                        context={
                            'media_item_id': media_item_id,
                            'original_path': original_path
                        },
                        severity="operational"
                    )

                conn.commit()

        except Exception as e:
            logger.error(
                "Error processing media item for normalization",
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
    logger.info("Normalization Worker iniciado.")
    rabbitmq_client.start_consumer('normalization_jobs', process_message)
