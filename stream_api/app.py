import os
import sys
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, abort, request, g

# Add the shared directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared')))
from db import get_db_connection
from logging_config import configure_logging, get_logger, generate_correlation_id, CorrelationContext
from health_check import create_standard_health_checker
from config import Config
from storage_manager import StorageManager

# --- Configuração ---
service_config = Config.get_service_config()

# Configure logging
configure_logging(service_config['name'])
logger = get_logger(service_config['name'])

app = Flask(__name__)

# Create health checker
health_checker = create_standard_health_checker(service_config['name'], include_rabbitmq=False)
health_checker.create_flask_endpoint(app)

# Initialize storage manager
storage_manager = StorageManager()

# --- Configuration ---
HEARTBEAT_TIMEOUT_SECONDS = 90
REAPER_INTERVAL_SECONDS = 30

# --- In-memory Store ---
# Thread-safe dictionary for active ffmpeg processes
active_streams = {}
lock = threading.Lock()

# --- Middleware para Correlation ID ---
@app.before_request
def before_request():
    # Generate or extract correlation ID
    correlation_id = request.headers.get('X-Correlation-ID') or generate_correlation_id()
    g.correlation_id = correlation_id
    
    # Set correlation ID in logger context
    logger.set_correlation_id(correlation_id)
    
    # Log request start
    logger.info(
        "Request started",
        context={
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
    )
    g.request_start_time = time.time()

@app.after_request
def after_request(response):
    # Calculate request duration
    duration_ms = (time.time() - g.request_start_time) * 1000
    
    # Log request completion
    logger.info(
        "Request completed",
        context={
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'content_length': response.content_length
        },
        duration_ms=duration_ms
    )
    
    # Add correlation ID to response headers
    response.headers['X-Correlation-ID'] = g.correlation_id
    return response

# --- Reaper Thread ---
def reaper_thread():
    """
    Periodically checks for and terminates streams that have not received a heartbeat.
    """
    while True:
        with lock:
            # Create a copy of the keys to avoid issues with modifying the dict while iterating
            channel_ids_to_reap = []
            for channel_id, stream_info in active_streams.items():
                time_since_heartbeat = datetime.now(timezone.utc) - stream_info['last_heartbeat']
                if time_since_heartbeat > timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS):
                    logger.info(
                        "Reaping stream due to heartbeat timeout",
                        context={
                            'channel_id': channel_id,
                            'time_since_heartbeat_seconds': time_since_heartbeat.total_seconds(),
                            'timeout_threshold': HEARTBEAT_TIMEOUT_SECONDS
                        }
                    )
                    try:
                        stream_info['process'].kill()
                        stream_info['process'].wait() # Wait for the process to terminate
                        # Clean up HLS files
                        hls_output_dir = f"/mnt/media/streams/hls/{channel_id}"
                        # This is a simple cleanup, a more robust solution would be needed for production
                        if os.path.exists(hls_output_dir):
                            for f in os.listdir(hls_output_dir):
                                os.remove(os.path.join(hls_output_dir, f))
                            os.rmdir(hls_output_dir)
                        
                        logger.info(
                            "Stream cleanup completed",
                            context={
                                'channel_id': channel_id,
                                'hls_output_dir': hls_output_dir
                            }
                        )
                        logger.audit("stream_reaped", channel_id, context={
                            'reason': 'heartbeat_timeout',
                            'timeout_seconds': time_since_heartbeat.total_seconds()
                        })
                    except Exception as e:
                        logger.error(
                            "Error killing stream process",
                            error=e,
                            context={'channel_id': channel_id},
                            severity="operational"
                        )
                    channel_ids_to_reap.append(channel_id)

            # Remove reaped streams from the dictionary
            for channel_id in channel_ids_to_reap:
                del active_streams[channel_id]

        time.sleep(REAPER_INTERVAL_SECONDS)

# --- API Endpoints ---
@app.route('/play/<string:channel_id>/live.m3u8')
def play_channel(channel_id):
    """
    Starts an ffmpeg stream for the requested channel based on the EPG.
    """
    with lock:
        if channel_id in active_streams:
            return f"/hls/{channel_id}/live.m3u8", 302

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT media_item_id, virtual_start_time, file_path
            FROM epg_virtual
            WHERE channel_id = %s AND virtual_start_time <= NOW()
            ORDER BY virtual_start_time DESC
            LIMIT 1;
        """
        cur.execute(query, (channel_id,))
        program = cur.fetchone()

        if not program:
            return "No program scheduled for this channel.", 404

        now_utc = datetime.now(timezone.utc)
        start_time_utc = program['virtual_start_time'].replace(tzinfo=timezone.utc)
        offset = (now_utc - start_time_utc).total_seconds()
        if offset < 0: offset = 0

        # Use StorageManager to get the correct file path (R2 URL or local path)
        relative_path = f"normalized/{program['media_item_id']}.mp4"
        media_file_url = storage_manager.get_file_url(relative_path)
        
        # For streaming, we need a local file path. If file is in R2, we need to download it first
        # or use the R2 URL directly if ffmpeg supports it
        if media_file_url.startswith('http'):
            # File is in R2, use URL directly (ffmpeg supports HTTP inputs)
            media_input = media_file_url
            logger.info(
                "Using R2 URL for streaming",
                context={
                    'channel_id': channel_id,
                    'media_item_id': program['media_item_id'],
                    'r2_url': media_file_url
                }
            )
        else:
            # File is local, use local path
            media_input = f"/mnt/media/normalized/{program['media_item_id']}.mp4"
            logger.info(
                "Using local file for streaming",
                context={
                    'channel_id': channel_id,
                    'media_item_id': program['media_item_id'],
                    'local_path': media_input
                }
            )
        
        hls_output_dir = f"/mnt/media/streams/hls/{channel_id}"
        os.makedirs(hls_output_dir, exist_ok=True)

        ffmpeg_cmd = [
            'ffmpeg', '-re',
            '-ss', str(offset),
            '-i', media_input,
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-hls_time', '10',
            '-hls_list_size', '6',
            '-hls_flags', 'delete_segments',
            '-f', 'hls',
            f'{hls_output_dir}/live.m3u8'
        ]

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with lock:
            active_streams[channel_id] = {
                'process': process,
                'start_time': now_utc,
                'last_heartbeat': now_utc
            }

        logger.info(
            "Stream started successfully",
            context={
                'channel_id': channel_id,
                'process_pid': process.pid,
                'media_input': media_input,
                'offset_seconds': offset,
                'hls_output_dir': hls_output_dir
            }
        )
        logger.audit("stream_started", channel_id, context={
            'media_item_id': program['media_item_id'],
            'offset_seconds': offset
        })
        return f"/hls/{channel_id}/live.m3u8", 302

    except Exception as e:
        logger.error(
            "Error starting stream for channel",
            error=e,
            context={'channel_id': channel_id},
            severity="operational"
        )
        abort(500, description="Internal server error")
    finally:
        if conn:
            conn.close()

@app.route('/heartbeat/<string:channel_id>', methods=['POST'])
def heartbeat(channel_id):
    """
    Updates the last_heartbeat timestamp for an active stream.
    """
    with lock:
        if channel_id in active_streams:
            active_streams[channel_id]['last_heartbeat'] = datetime.now(timezone.utc)
            logger.debug(
                "Heartbeat received for active stream",
                context={'channel_id': channel_id}
            )
            return jsonify({"status": "ok"}), 200
        else:
            logger.warning(
                "Heartbeat received for non-existent stream",
                context={'channel_id': channel_id}
            )
            return jsonify({"status": "error", "message": "stream_not_found"}), 404

if __name__ == "__main__":
    # Start the reaper thread in the background
    reaper = threading.Thread(target=reaper_thread, daemon=True)
    reaper.start()

    # Start the Flask app
    app.run(host='0.0.0.0', port=8001, debug=True)
