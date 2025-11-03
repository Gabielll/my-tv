import time
import psycopg2
import pika
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from flask import Flask, jsonify
from shared.config import Config
from shared.logging_config import get_logger

class HealthChecker:
    """Health check manager for services"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = get_logger(service_name)
        self.start_time = time.time()
        self.dependencies = {}
        self.config = Config.get_health_check_config()
    
    def add_dependency(self, name: str, check_func: Callable[[], bool], timeout: Optional[int] = None):
        """Add a dependency check function"""
        self.dependencies[name] = {
            'check_func': check_func,
            'timeout': timeout or self.config['timeout']
        }
        self.logger.info(f"Added health check dependency: {name}")
    
    def check_dependency(self, name: str, check_func: Callable[[], bool], timeout: int) -> Dict[str, Any]:
        """Check a single dependency with timeout and timing"""
        start_time = time.time()
        
        try:
            # Simple timeout implementation
            result = check_func()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if result:
                return {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2)
                }
            else:
                return {
                    'status': 'unhealthy',
                    'response_time_ms': round(response_time, 2),
                    'error': 'Check returned False'
                }
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(
                f"Health check failed for {name}",
                error=e,
                context={'dependency': name, 'response_time_ms': response_time}
            )
            return {
                'status': 'unhealthy',
                'response_time_ms': round(response_time, 2),
                'error': str(e)
            }
    
    def check_health(self) -> Dict[str, Any]:
        """Perform all health checks and return status"""
        overall_status = 'healthy'
        checks = {}
        
        # Check all dependencies
        for name, config in self.dependencies.items():
            check_result = self.check_dependency(
                name, 
                config['check_func'], 
                config['timeout']
            )
            checks[name] = check_result
            
            if check_result['status'] != 'healthy':
                overall_status = 'unhealthy'
        
        uptime_seconds = int(time.time() - self.start_time)
        
        health_status = {
            'status': overall_status,
            'service': self.service_name,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'uptime_seconds': uptime_seconds,
            'checks': checks
        }
        
        # Log health check result
        if overall_status == 'healthy':
            self.logger.debug("Health check passed", context={'uptime_seconds': uptime_seconds})
        else:
            self.logger.warning(
                "Health check failed", 
                context={
                    'failed_checks': [name for name, result in checks.items() if result['status'] != 'healthy'],
                    'uptime_seconds': uptime_seconds
                }
            )
        
        return health_status
    
    def create_flask_endpoint(self, app: Flask, endpoint: str = '/health'):
        """Create Flask health check endpoint"""
        @app.route(endpoint, methods=['GET'])
        def health_check():
            health_status = self.check_health()
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return jsonify(health_status), status_code
        
        self.logger.info(f"Health check endpoint created at {endpoint}")

def check_database_connection() -> bool:
    """Check database connectivity"""
    try:
        db_config = Config.get_db_config()
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            connect_timeout=db_config['connect_timeout']
        )
        
        # Perform a simple query to verify connection
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            result = cur.fetchone()
        
        conn.close()
        return result is not None
    
    except Exception:
        return False

def check_rabbitmq_connection() -> bool:
    """Check RabbitMQ connectivity"""
    try:
        rabbitmq_config = Config.get_rabbitmq_config()
        
        credentials = pika.PlainCredentials(
            rabbitmq_config['username'],
            rabbitmq_config['password']
        )
        
        parameters = pika.ConnectionParameters(
            host=rabbitmq_config['host'],
            port=rabbitmq_config['port'],
            virtual_host=rabbitmq_config['virtual_host'],
            credentials=credentials,
            connection_attempts=1,
            retry_delay=1,
            socket_timeout=rabbitmq_config['connection_timeout'],
            heartbeat=rabbitmq_config['heartbeat']
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Test basic functionality
        channel.queue_declare(queue='health_check_test', durable=False, auto_delete=True)
        
        connection.close()
        return True
    
    except Exception:
        return False

def check_disk_space(path: str = '/mnt/media', min_free_gb: int = 1) -> bool:
    """Check if there's enough disk space available"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        free_gb = free // (1024**3)  # Convert to GB
        return free_gb >= min_free_gb
    except Exception:
        return False

def check_memory_usage(max_usage_percent: int = 90) -> bool:
    """Check memory usage"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return memory.percent < max_usage_percent
    except ImportError:
        # psutil not available, skip check
        return True
    except Exception:
        return False

def create_standard_health_checker(service_name: str, include_db: bool = True, 
                                 include_rabbitmq: bool = True) -> HealthChecker:
    """Create a health checker with standard dependencies"""
    health_checker = HealthChecker(service_name)
    
    if include_db:
        health_checker.add_dependency('database', check_database_connection)
    
    if include_rabbitmq:
        health_checker.add_dependency('rabbitmq', check_rabbitmq_connection)
    
    # Always check disk space for media services
    health_checker.add_dependency('disk_space', lambda: check_disk_space('/mnt/media', 1))
    
    return health_checker