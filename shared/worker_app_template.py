import os
import sys
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, g, request
from typing import Callable, Dict, Any, Optional

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from shared.logging_config import configure_logging, get_logger, generate_correlation_id
from shared.health_check import create_standard_health_checker
from shared.config import Config

class WorkerWebService:
    """
    Template class for converting workers to web services.
    Wraps worker logic in a Flask app with health checks and monitoring.
    """
    
    def __init__(self, service_name: str, worker_function: Callable, 
                 include_rabbitmq: bool = True, custom_health_check: Optional[Callable] = None):
        """
        Initialize the worker web service.
        
        Args:
            service_name: Name of the service (e.g., 'media-manager')
            worker_function: The original worker function to run in background
            include_rabbitmq: Whether to include RabbitMQ in health checks
            custom_health_check: Optional custom health check function
        """
        self.service_name = service_name
        self.worker_function = worker_function
        self.include_rabbitmq = include_rabbitmq
        self.custom_health_check = custom_health_check
        
        # Service state tracking
        self.worker_thread = None
        self.worker_status = {
            'status': 'starting',
            'started_at': None,
            'last_activity': None,
            'error_count': 0,
            'last_error': None
        }
        
        # Configure logging
        configure_logging(service_name)
        self.logger = get_logger(service_name)
        
        # Create Flask app
        self.app = self._create_flask_app()
        
        # Start worker thread
        self._start_worker_thread()
        
    def _create_flask_app(self) -> Flask:
        """Create and configure the Flask application."""
        app = Flask(__name__)
        
        # Create health checker
        health_checker = create_standard_health_checker(
            self.service_name, 
            include_rabbitmq=self.include_rabbitmq
        )
        
        # Add middleware for correlation ID and logging
        @app.before_request
        def before_request():
            # Generate or extract correlation ID
            correlation_id = request.headers.get('X-Correlation-ID') or generate_correlation_id()
            g.correlation_id = correlation_id
            
            # Set correlation ID in logger context
            self.logger.set_correlation_id(correlation_id)
            
            # Log request start
            self.logger.info(
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
            self.logger.info(
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
        
        # Add health endpoint
        @app.route('/health')
        def health():
            return self._health_check()
        
        # Add worker status endpoint
        @app.route('/worker/status')
        def worker_status():
            return jsonify(self.worker_status)
        
        # Add root endpoint for basic info
        @app.route('/')
        def root():
            return jsonify({
                'service': self.service_name,
                'type': 'worker-web-service',
                'status': self.worker_status['status'],
                'endpoints': ['/health', '/worker/status']
            })
        
        return app
    
    def _start_worker_thread(self):
        """Start the worker function in a background thread."""
        def worker_wrapper():
            """Wrapper function that handles worker lifecycle and error tracking."""
            self.worker_status['status'] = 'running'
            self.worker_status['started_at'] = datetime.utcnow().isoformat()
            
            self.logger.info(f"{self.service_name} worker thread started")
            
            while True:
                try:
                    # Update last activity timestamp
                    self.worker_status['last_activity'] = datetime.utcnow().isoformat()
                    
                    # Run the original worker function
                    self.worker_function()
                    
                except Exception as e:
                    self.worker_status['error_count'] += 1
                    self.worker_status['last_error'] = {
                        'message': str(e),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    
                    self.logger.error(
                        f"Error in {self.service_name} worker function",
                        error=e,
                        context={
                            'error_count': self.worker_status['error_count']
                        },
                        severity="operational"
                    )
                    
                    # Sleep before retrying to avoid tight error loops
                    time.sleep(30)
                
                except KeyboardInterrupt:
                    self.logger.info(f"{self.service_name} worker thread stopping due to interrupt")
                    break
        
        # Start the worker thread
        self.worker_thread = threading.Thread(target=worker_wrapper, daemon=True)
        self.worker_thread.start()
        
        self.logger.info(f"{self.service_name} worker thread initialized")
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform health check including worker status."""
        try:
            # Basic service health
            health_info = {
                'service': self.service_name,
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'worker': {
                    'status': self.worker_status['status'],
                    'thread_alive': self.worker_thread.is_alive() if self.worker_thread else False,
                    'started_at': self.worker_status['started_at'],
                    'last_activity': self.worker_status['last_activity'],
                    'error_count': self.worker_status['error_count']
                }
            }
            
            # Check if worker thread is alive
            if not self.worker_thread or not self.worker_thread.is_alive():
                health_info['status'] = 'unhealthy'
                health_info['error'] = 'Worker thread is not running'
            
            # Check for recent errors
            if self.worker_status['error_count'] > 10:
                health_info['status'] = 'degraded'
                health_info['warning'] = f"High error count: {self.worker_status['error_count']}"
            
            # Run custom health check if provided
            if self.custom_health_check:
                try:
                    custom_result = self.custom_health_check()
                    health_info['custom'] = custom_result
                except Exception as e:
                    health_info['status'] = 'unhealthy'
                    health_info['error'] = f"Custom health check failed: {str(e)}"
            
            # Determine HTTP status code
            status_code = 200
            if health_info['status'] == 'unhealthy':
                status_code = 503
            elif health_info['status'] == 'degraded':
                status_code = 200  # Still return 200 for degraded to keep UptimeRobot happy
            
            return jsonify(health_info), status_code
            
        except Exception as e:
            self.logger.error(
                "Health check failed",
                error=e,
                severity="operational"
            )
            
            return jsonify({
                'service': self.service_name,
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503
    
    def run(self, host: str = '0.0.0.0', port: Optional[int] = None, debug: bool = False):
        """Run the Flask application."""
        if port is None:
            port = int(os.environ.get('PORT', 8000))
        
        self.logger.info(
            f"Starting {self.service_name} web service",
            context={
                'host': host,
                'port': port,
                'debug': debug
            }
        )
        
        self.app.run(host=host, port=port, debug=debug)


def create_worker_web_service(service_name: str, worker_function: Callable, 
                             include_rabbitmq: bool = True, 
                             custom_health_check: Optional[Callable] = None) -> WorkerWebService:
    """
    Factory function to create a worker web service.
    
    Args:
        service_name: Name of the service
        worker_function: The original worker function
        include_rabbitmq: Whether to include RabbitMQ in health checks
        custom_health_check: Optional custom health check function
        
    Returns:
        WorkerWebService instance
    """
    return WorkerWebService(
        service_name=service_name,
        worker_function=worker_function,
        include_rabbitmq=include_rabbitmq,
        custom_health_check=custom_health_check
    )