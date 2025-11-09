#!/usr/bin/env python3
"""
Media Manager Web Service

Converts the media_manager worker into a web service for Render deployment.
Maintains all original functionality while providing HTTP endpoints for health checks.
"""

import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from shared.worker_app_template import create_worker_web_service
from shared.db import get_db_connection
from shared.logging_config import get_logger, generate_correlation_id, CorrelationContext
from shared.config import Config
from shared.storage_manager import StorageManager
from shared import rabbitmq_client

# --- Configuration ---
service_config = Config.get_service_config()
media_config = Config.get_media_config()

STAGING_DIR = media_config['staging_dir']
ALLOWED_EXTENSIONS = set(media_config['allowed_extensions'])

# Initialize storage manager
storage_manager = StorageManager()

# Global observer for file monitoring
observer = None
logger = None

# --- File System Event Handler ---
class NewFileHandler(FileSystemEventHandler):
    """Handles file creation events in the staging directory."""

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = event.src_path
        filename = os.path.basename(file_path)
        _, extension = os.path.splitext(filename)

        if extension.lower() in ALLOWED_EXTENSIONS:
            # Generate correlation ID for this file processing
            correlation_id = generate_correlation_id()
            with CorrelationContext(correlation_id):
                logger.info(
                    "New media file detected",
                    context={
                        'filename': filename,
                        'file_path': file_path,
                        'extension': extension,
                        'file_size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                    }
                )
                self.process_new_media(file_path)

    def process_new_media(self, file_path):
        """Process a new media file: add it to the database."""
        conn = get_db_connection()
        if not conn:
            logger.error(
                "Database connection failed for media processing",
                context={'file_path': file_path},
                severity="critical"
            )
            return

        try:
            with conn.cursor() as cur:
                # Check if file already exists to avoid duplicates
                cur.execute("SELECT id FROM media_items WHERE original_file_path = %s;", (file_path,))
                if cur.fetchone():
                    logger.warning(
                        "Duplicate file detected, skipping processing",
                        context={'file_path': file_path}
                    )
                    return

                # Insert new media item
                title = os.path.splitext(os.path.basename(file_path))[0]
                final_path_placeholder = f"/mnt/media/normalized/{os.path.basename(file_path)}"

                cur.execute(
                    """
                    INSERT INTO media_items (title, original_file_path, file_path, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (title, file_path, final_path_placeholder, 'pending_enrichment')
                )
                media_item_id = cur.fetchone()[0]
                conn.commit()
                
                logger.info(
                    "Media item inserted into database",
                    context={
                        'file_path': file_path,
                        'media_item_id': media_item_id,
                        'title': title,
                        'status': 'pending_enrichment'
                    }
                )
                logger.audit("media_item_created", str(media_item_id), context={
                    'file_path': file_path,
                    'title': title
                })

                # Publish message to queue for next stage (enrichment)
                message = str(media_item_id)
                rabbitmq_client.publish_message('enrichment_jobs', message)
                
                logger.info(
                    "Message published to enrichment queue",
                    context={
                        'media_item_id': media_item_id,
                        'queue': 'enrichment_jobs'
                    }
                )

        except Exception as e:
            logger.error(
                "Failed to process media file",
                error=e,
                context={'file_path': file_path},
                severity="operational"
            )
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

# --- Worker Function ---
def media_manager_worker():
    """
    Main worker function that runs the media manager logic.
    This function runs in a background thread within the web service.
    """
    global observer, logger
    
    # Get logger instance
    logger = get_logger('media-manager')
    
    # Ensure staging directory exists
    if not os.path.exists(STAGING_DIR):
        logger.info(f"Staging directory '{STAGING_DIR}' does not exist. Creating...")
        os.makedirs(STAGING_DIR)

    logger.info(f"Monitoring directory: {STAGING_DIR}")

    # Set up file system observer
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, STAGING_DIR, recursive=True)

    # Start monitoring
    observer.start()
    logger.info("Media Manager worker started")

    try:
        # Keep the worker running
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error("Media Manager worker error", error=e)
        if observer:
            observer.stop()
        raise

# --- Custom Health Check ---
def custom_health_check():
    """Custom health check for media manager service."""
    health_info = {
        'staging_directory': {
            'path': STAGING_DIR,
            'exists': os.path.exists(STAGING_DIR),
            'writable': os.access(STAGING_DIR, os.W_OK) if os.path.exists(STAGING_DIR) else False
        },
        'file_observer': {
            'active': observer is not None and observer.is_alive() if observer else False
        },
        'storage': storage_manager.get_storage_info()
    }
    
    # Check for recent files in staging
    if os.path.exists(STAGING_DIR):
        try:
            files = os.listdir(STAGING_DIR)
            health_info['staging_directory']['file_count'] = len(files)
        except Exception as e:
            health_info['staging_directory']['error'] = str(e)
    
    return health_info

# --- Create Web Service ---
if __name__ == '__main__':
    # Create the worker web service
    service = create_worker_web_service(
        service_name='media-manager',
        worker_function=media_manager_worker,
        include_rabbitmq=True,
        custom_health_check=custom_health_check
    )
    
    # Run the Flask application
    service.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        debug=False
    )