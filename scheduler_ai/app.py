#!/usr/bin/env python3
"""
Scheduler AI Web Service

Converts the scheduler_ai worker into a web service for Render deployment.
Maintains all original functionality while providing HTTP endpoints for health checks.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from shared.worker_app_template import create_worker_web_service
from shared.db import get_db_connection
from shared.logging_config import get_logger, generate_correlation_id, CorrelationContext
from shared.config import Config

# Import scheduler engine if it exists
try:
    from scheduler_ai.engine import process_scheduling_rules
    ENGINE_AVAILABLE = True
except ImportError:
    ENGINE_AVAILABLE = False
    def process_scheduling_rules(rules, media_items):
        """Placeholder function when engine is not available."""
        return [], {}

# --- Configuration ---
service_config = Config.get_service_config()

# Global variables for health tracking
logger = None
last_run_time = None
next_run_time = None
scheduling_stats = {
    'total_runs': 0,
    'successful_runs': 0,
    'failed_runs': 0,
    'last_epg_entries_count': 0,
    'last_run_duration_ms': 0,
    'last_error': None
}

# Scheduling interval (4 hours in seconds)
SCHEDULING_INTERVAL = 4 * 60 * 60  # 4 hours

# --- Scheduling Logic ---
def fetch_scheduling_rules(conn):
    """
    Fetch scheduling rules from the database.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM channel_master_grid WHERE is_active = true;")
        rules = cur.fetchall()
        return rules

def fetch_media_items(conn):
    """
    Fetch all available media items from the database.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM media_items WHERE status = 'processed';")
        media_items = cur.fetchall()
        return media_items

def clear_epg_for_channels(conn, channel_ids):
    """
    Clear future EPG for specified channels.
    """
    logger.info(
        "Clearing future EPG for channels",
        context={
            'channel_ids': list(channel_ids),
            'channel_count': len(channel_ids)
        }
    )
    with conn.cursor() as cur:
        # Clear from now onwards to not affect history
        cur.execute(
            "DELETE FROM epg_virtual WHERE channel_id = ANY(%s) AND start_time_virtual >= NOW()",
            (list(channel_ids),)
        )

def save_epg_entries(conn, epg_entries):
    """
    Save new EPG entries to the database.
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
    Update program_state field for rules that changed.
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

def run_scheduling():
    """
    Main function to execute the scheduler.
    """
    global last_run_time, next_run_time, scheduling_stats
    
    # Generate correlation ID for this scheduling run
    correlation_id = generate_correlation_id()
    with CorrelationContext(correlation_id):
        logger.info("Scheduler AI starting...")
        
        start_time = time.time()
        scheduling_stats['total_runs'] += 1
        last_run_time = datetime.now()
        next_run_time = last_run_time + timedelta(seconds=SCHEDULING_INTERVAL)
        
        conn = None
        try:
            conn = get_db_connection()
            logger.info("Database connection established successfully.")

            # 1. Fetch data from database
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

            # 2. Call scheduling engine to generate programming
            logger.info("Starting scheduling engine processing")
            
            if ENGINE_AVAILABLE:
                epg_entries, updated_states = process_scheduling_rules(rules, media_items)
            else:
                logger.warning("Scheduling engine not available, using placeholder")
                epg_entries, updated_states = [], {}

            # 3. Save results to database
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
            
            # Update stats
            duration_ms = (time.time() - start_time) * 1000
            scheduling_stats['successful_runs'] += 1
            scheduling_stats['last_epg_entries_count'] = len(epg_entries) if epg_entries else 0
            scheduling_stats['last_run_duration_ms'] = duration_ms
            scheduling_stats['last_error'] = None
            
            logger.info(
                "Scheduling operation completed successfully",
                context={
                    'epg_entries_created': len(epg_entries) if epg_entries else 0,
                    'program_states_updated': len(updated_states) if updated_states else 0
                },
                duration_ms=duration_ms
            )

        except Exception as e:
            if conn:
                conn.rollback()
            
            # Update error stats
            scheduling_stats['failed_runs'] += 1
            scheduling_stats['last_error'] = {
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.error(
                "Scheduling operation failed",
                error=e,
                severity="critical"
            )
        finally:
            if conn:
                conn.close()
                logger.debug("Database connection closed")

# --- Worker Function ---
def scheduler_ai_worker():
    """
    Main worker function that runs the scheduler AI logic periodically.
    This function runs in a background thread within the web service.
    Executes scheduling every 4 hours in a continuous loop.
    """
    global logger, next_run_time
    
    # Get logger instance
    logger = get_logger('scheduler-ai')
    
    logger.info("Scheduler AI worker started - will run every 4 hours")
    
    try:
        while True:
            # Run the scheduling immediately on startup, then every 4 hours
            logger.info("Starting periodic EPG generation")
            run_scheduling()
            
            # Calculate next run time
            next_run_time = datetime.now() + timedelta(seconds=SCHEDULING_INTERVAL)
            logger.info(f"EPG generation completed. Next run scheduled for: {next_run_time}")
            
            # Sleep for the full interval (4 hours)
            logger.info(f"Sleeping for {SCHEDULING_INTERVAL} seconds (4 hours)")
            time.sleep(SCHEDULING_INTERVAL)
            
    except Exception as e:
        logger.error("Scheduler AI worker error", error=e)
        # Don't re-raise to keep the service alive, just log and continue
        logger.info("Restarting scheduler worker after error...")
        time.sleep(60)  # Wait 1 minute before restarting
        # The while loop will continue and try again

# --- Custom Health Check ---
def custom_health_check():
    """Custom health check for scheduler AI service."""
    current_time = datetime.now()
    
    health_info = {
        'scheduling_engine': {
            'available': ENGINE_AVAILABLE
        },
        'scheduling_stats': scheduling_stats.copy(),
        'timing': {
            'last_run_time': last_run_time.isoformat() if last_run_time else None,
            'next_run_time': next_run_time.isoformat() if next_run_time else None,
            'current_time': current_time.isoformat(),
            'interval_seconds': SCHEDULING_INTERVAL
        }
    }
    
    # Check if we're overdue for a run
    if next_run_time and current_time > next_run_time + timedelta(minutes=10):
        health_info['warning'] = 'Scheduler appears to be overdue for next run'
    
    # Check recent failure rate
    if scheduling_stats['total_runs'] > 0:
        failure_rate = scheduling_stats['failed_runs'] / scheduling_stats['total_runs']
        health_info['scheduling_stats']['failure_rate'] = round(failure_rate * 100, 2)
        
        if failure_rate > 0.5:  # More than 50% failure rate
            health_info['warning'] = 'High failure rate detected'
    
    return health_info

# --- Create Web Service ---
if __name__ == '__main__':
    # Create the worker web service
    service = create_worker_web_service(
        service_name='scheduler-ai',
        worker_function=scheduler_ai_worker,
        include_rabbitmq=False,  # Scheduler doesn't use RabbitMQ
        custom_health_check=custom_health_check
    )
    
    # Run the Flask application
    service.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8000)),
        debug=False
    )