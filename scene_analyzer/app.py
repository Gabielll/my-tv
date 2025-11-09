#!/usr/bin/env python3
"""
Scene Analyzer Web Service

Converts the scene_analyzer worker into a web service for Render deployment.
Maintains all original functionality while providing HTTP endpoints for health checks.
"""

import os
import sys
import subprocess
import re
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

# Global variables for health tracking
logger = None
last_processed_item = None
analysis_stats = {
    'total_processed': 0,
    'successful_analyses': 0,
    'failed_analyses': 0,
    'total_cue_points_found': 0,
    'last_processing_time': None
}

# --- Scene Analysis Logic ---
def analyze_scenes(file_path):
    """
    Uses ffmpeg with 'blackdetect' filter to find periods of silence/black.
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
    """Callback function that processes a message from the queue."""
    global last_processed_item, analysis_stats
    
    try:
        media_item_id = int(message_body)
    except (ValueError, TypeError):
        logger.error(
            "Invalid media item ID received",
            context={'message_body': str(message_body)},
            severity="operational"
        )
        analysis_stats['failed_analyses'] += 1
        return

    # Generate correlation ID for this processing task
    correlation_id = generate_correlation_id()
    with CorrelationContext(correlation_id):
        logger.info(
            "Starting scene analysis processing",
            context={'media_item_id': media_item_id}
        )
        
        analysis_stats['total_processed'] += 1
        analysis_stats['last_processing_time'] = time.time()
        last_processed_item = media_item_id
        
        conn = get_db_connection()
        if not conn:
            logger.error(
                "Database connection failed for scene analysis",
                context={'media_item_id': media_item_id},
                severity="critical"
            )
            analysis_stats['failed_analyses'] += 1
            raise Exception("Could not connect to database.")

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
                    analysis_stats['failed_analyses'] += 1
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
                    
                    analysis_stats['total_cue_points_found'] += len(cue_points)
                    
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
                
                analysis_stats['successful_analyses'] += 1
                
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
            analysis_stats['failed_analyses'] += 1
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

# --- Worker Function ---
def scene_analyzer_worker():
    """
    Main worker function that runs the scene analyzer logic.
    This function runs in a background thread within the web service.
    """
    global logger
    
    # Get logger instance
    logger = get_logger('scene-analyzer')
    
    logger.info("Scene Analyzer started")
    
    # Start consuming messages from RabbitMQ
    try:
        rabbitmq_client.start_consumer('scene_analysis_jobs', process_message)
    except Exception as e:
        logger.error("Error in scene analyzer worker", error=e)
        raise

# --- Custom Health Check ---
def custom_health_check():
    """Custom health check for scene analyzer service."""
    health_info = {
        'ffmpeg': {
            'available': check_ffmpeg_availability(),
            'blackdetect_filter': check_blackdetect_filter()
        },
        'analysis_stats': analysis_stats.copy(),
        'last_processed_item': last_processed_item
    }
    
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

def check_blackdetect_filter():
    """Check if ffmpeg has blackdetect filter available."""
    try:
        result = subprocess.run(['ffmpeg', '-filters'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return 'blackdetect' in result.stdout
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False

# --- Create Web Service ---
if __name__ == '__main__':
    # Create the worker web service
    service = create_worker_web_service(
        service_name='scene-analyzer',
        worker_function=scene_analyzer_worker,
        include_rabbitmq=True,
        custom_health_check=custom_health_check
    )
    
    # Run the Flask application
    service.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        debug=False
    )