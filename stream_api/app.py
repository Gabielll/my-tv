import os
import sys
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, abort, request

# Add the shared directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'shared')))
from db import get_db_connection

app = Flask(__name__)

# --- Configuration ---
HEARTBEAT_TIMEOUT_SECONDS = 90
REAPER_INTERVAL_SECONDS = 30

# --- In-memory Store ---
# Thread-safe dictionary for active ffmpeg processes
active_streams = {}
lock = threading.Lock()

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
                    app.logger.info(f"Reaping stream for channel {channel_id} due to heartbeat timeout.")
                    try:
                        stream_info['process'].kill()
                        stream_info['process'].wait() # Wait for the process to terminate
                        # Clean up HLS files
                        hls_output_dir = f"/mnt/media/streams/hls/{channel_id}"
                        # This is a simple cleanup, a more robust solution would be needed for production
                        for f in os.listdir(hls_output_dir):
                            os.remove(os.path.join(hls_output_dir, f))
                        os.rmdir(hls_output_dir)
                    except Exception as e:
                        app.logger.error(f"Error killing process for channel {channel_id}: {e}")
                    channel_ids_to_reap.append(channel_id)

            # Remove reaped streams from the dictionary
            for channel_id in channel_ids_to_reap:
                del active_streams[channel_id]

        time.sleep(REAPER_INTERVAL_SECONDS)

# --- API Endpoints ---
@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

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

        media_file_path = f"/mnt/media/normalized/{program['media_item_id']}.mp4" # Assuming normalized files are mp4
        hls_output_dir = f"/mnt/media/streams/hls/{channel_id}"
        os.makedirs(hls_output_dir, exist_ok=True)

        ffmpeg_cmd = [
            'ffmpeg', '-re',
            '-ss', str(offset),
            '-i', media_file_path,
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

        app.logger.info(f"Started stream for channel {channel_id} with PID {process.pid}")
        return f"/hls/{channel_id}/live.m3u8", 302

    except Exception as e:
        app.logger.error(f"Error starting stream for channel {channel_id}: {e}")
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
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"status": "error", "message": "stream_not_found"}), 404

if __name__ == "__main__":
    # Start the reaper thread in the background
    reaper = threading.Thread(target=reaper_thread, daemon=True)
    reaper.start()

    # Start the Flask app
    app.run(host='0.0.0.0', port=8001, debug=True)
