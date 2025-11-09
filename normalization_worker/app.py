#!/usr/bin/env python3
"""
Normalization Worker Web Service

Converts the normalization_worker into a web service for Render deployment.
Maintains all original functionality while providing HTTP endpoints for health checks.
"""

import os
import sys
import subprocess
import time

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from shared.worker_app_template import create_worker_web_service
from shared.db import get_db_connection
from shared.logging_config import get_logger, generate_correlation_id, CorrelationContext
from shared.config import Config
from shared import rabbitmq_client

# --- Configuration ---
service_config = Config.get_service_config()
media_config = Config.get_media_config()

NORMALIZED_DIR = media_config['normalized_dir']

# Global variables for health tracking
logger = None
last_processed_item = None
processing_stats = {
    'total_processed': 0,
    'successful_normalizations': 0,
    'failed_normalizations': 0,
    'last_processing_time': None
}

# --- Normalization Logic ---
def normalize_media(input_path, output_path):
    """
    Transcodes a media file to standard format (H.264/AAC in MP4 container)
    using ffmpeg.
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
    """Callback function that processes a message from the queue."""
    global last_processed_item, processing_stats
    
    try:
        media_item_id = int(message_body)
    except (ValueError, TypeError):
        logger.error(
            "Invalid media item ID received",
            context={'message_body': str(message_body)},
            severity="operational"
        )
        processing_stats['failed_normalizations'] += 1
        return

    # Generate correlation ID for this processing task
    correlation_id = generate_correlation_id()
    with CorrelationContext(correlation_id):
        logger.info(
            "Starting media normalization processing",
            context={'media_item_id': media_item_id}
        )
        
        processing_stats['total_processed'] += 1
        processing_stats['last_processing_time'] = time.time()
        last_processed_item = media_item_id
        
        conn = get_db_connection()
        if not conn:
            logger.error(
                "Database connection failed for normalization",
                context={'media_item_id': media_item_id},
                severity="critical"
            )
            processing_stats['failed_normalizations'] += 1
            raise Exception("Could not connect to database.")

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
                    processing_stats['failed_normalizations'] += 1
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
                    
                    processing_stats['successful_normalizations'] += 1
                    
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
                    processing_stats['failed_normalizations'] += 1
                    
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
            processing_stats['failed_normalizations'] += 1
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

# --- Worker Function ---
def normalization_worker():
    """
    Main worker function that runs the normalization worker logic.
    This function runs in a background thread within the web service.
    """
    global logger
    
    # Get logger instance
    logger = get_logger('normalization-worker')
    
    logger.info("Normalization Worker started")
    
    # Start consuming messages from RabbitMQ
    try:
        rabbitmq_client.start_consumer('normalization_jobs', process_message)
    except Exception as e:
        logger.error("Error in normalization worker", error=e)
        raise

# --- Custom Health Check ---
def custom_health_check():
    """Custom health check for normalization worker service."""
    health_info = {
        'normalized_directory': {
            'path': NORMALIZED_DIR,
            'exists': os.path.exists(NORMALIZED_DIR),
            'writable': os.access(NORMALIZED_DIR, os.W_OK) if os.path.exists(NORMALIZED_DIR) else False
        },
        'ffmpeg': {
            'available': check_ffmpeg_availability()
        },
        'processing_stats': processing_stats.copy(),
        'last_processed_item': last_processed_item
    }
    
    # Check disk space in normalized directory
    if os.path.exists(NORMALIZED_DIR):
        try:
            stat = os.statvfs(NORMALIZED_DIR)
            free_space = stat.f_bavail * stat.f_frsize
            total_space = stat.f_blocks * stat.f_frsize
            health_info['normalized_directory']['free_space_bytes'] = free_space
            health_info['normalized_directory']['total_space_bytes'] = total_space
            health_info['normalized_directory']['free_space_percent'] = round((free_space / total_space) * 100, 2)
        except Exception as e:
            health_info['normalized_directory']['disk_check_error'] = str(e)
    
    return health_info

def check_ffmpeg_availability():
    """Check if ffmpeg is available in the system."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False

# --- Create Web Service ---
if __name__ == '__main__':
    # Create the worker web service
    service = create_worker_web_service(
        service_name='normalization-worker',
        worker_function=normalization_worker,
        include_rabbitmq=True,
        custom_health_check=custom_health_check
    )
    
    # Run the Flask application
    service.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        debug=False
    )