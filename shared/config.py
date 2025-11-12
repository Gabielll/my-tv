import os
from typing import Dict, Any, Optional

# 🧪 MODO DE TESTE - REMOVER EM PRODUÇÃO
ENABLE_RABBITMQ_TEST_MODE = True

class Config:
    """Centralized configuration management for all services"""
    
    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        """Get database configuration from environment variables"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '26257')),
            'dbname': os.getenv('DB_NAME', 'media_server'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '10')),
            'command_timeout': int(os.getenv('DB_COMMAND_TIMEOUT', '30'))
        }
    
    @classmethod
    def is_rabbitmq_test_mode(cls) -> bool:
        """Check if RabbitMQ test mode is enabled"""
        return os.getenv('RABBITMQ_TEST_MODE', 'false').lower() == 'true' or ENABLE_RABBITMQ_TEST_MODE
    
    @classmethod
    def get_rabbitmq_config(cls) -> Dict[str, Any]:
        """Get RabbitMQ configuration with test mode support"""
        
        # 🧪 Credenciais hardcoded para teste
        if cls.is_rabbitmq_test_mode():
            return {
                'host': 'jaragua.lmq.cloudamqp.com',
                'port': 5672,
                'username': 'bgepvloi',
                'password': 'alfnh4BZ5O6TJCrrbfDXtrLLgifzIh01',
                'virtual_host': 'bgepvloi',
                'connection_timeout': 10,
                'heartbeat': 600
            }
        
        # Configuração normal via environment variables
        return {
            'host': os.getenv('RABBITMQ_HOST', 'localhost'),
            'port': int(os.getenv('RABBITMQ_PORT', '5672')),
            'username': os.getenv('RABBITMQ_USER', 'guest'),
            'password': os.getenv('RABBITMQ_PASS', 'guest'),
            'virtual_host': os.getenv('RABBITMQ_VHOST', '/'),
            'connection_timeout': int(os.getenv('RABBITMQ_CONNECT_TIMEOUT', '10')),
            'heartbeat': int(os.getenv('RABBITMQ_HEARTBEAT', '600'))
        }
    
    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """Get logging configuration from environment variables"""
        return {
            'level': os.getenv('LOG_LEVEL', 'INFO').upper(),
            'format': os.getenv('LOG_FORMAT', 'json').lower(),
            'output': os.getenv('LOG_OUTPUT', 'console').lower(),
            'file': os.getenv('LOG_FILE'),
            'correlation_header': os.getenv('CORRELATION_ID_HEADER', 'X-Correlation-ID')
        }
    
    @classmethod
    def get_health_check_config(cls) -> Dict[str, Any]:
        """Get health check configuration from environment variables"""
        return {
            'timeout': int(os.getenv('HEALTH_CHECK_TIMEOUT', '5')),
            'interval': int(os.getenv('HEALTH_CHECK_INTERVAL', '30')),
            'retries': int(os.getenv('HEALTH_CHECK_RETRIES', '3')),
            'start_period': int(os.getenv('HEALTH_CHECK_START_PERIOD', '60'))
        }
    
    @classmethod
    def get_service_config(cls) -> Dict[str, Any]:
        """Get service-specific configuration"""
        return {
            'name': os.getenv('SERVICE_NAME', 'unknown'),
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'hostname': os.getenv('HOSTNAME', 'unknown'),
            'port': int(os.getenv('SERVICE_PORT', '8000'))
        }
    
    @classmethod
    def get_media_config(cls) -> Dict[str, Any]:
        """Get media processing configuration"""
        return {
            'staging_dir': os.getenv('STAGING_DIR', '/mnt/media/staging_ingest'),
            'normalized_dir': os.getenv('NORMALIZED_DIR', '/mnt/media/normalized'),
            'streams_dir': os.getenv('STREAMS_DIR', '/mnt/media/streams'),
            'allowed_extensions': os.getenv('ALLOWED_EXTENSIONS', '.mkv,.mp4,.avi,.mov').split(','),
            'max_file_size': int(os.getenv('MAX_FILE_SIZE', str(16 * 1024 * 1024 * 1024)))  # 16GB
        }
    
    @classmethod
    def get_storage_config(cls) -> Dict[str, Any]:
        """Get storage configuration for Cloudflare R2"""
        return {
            'mode': os.getenv('STORAGE_MODE', 'local'),  # 'local', 'r2', 'hybrid'
            'r2_account_id': os.getenv('R2_ACCOUNT_ID'),
            'r2_access_key_id': os.getenv('R2_ACCESS_KEY_ID'),
            'r2_secret_access_key': os.getenv('R2_SECRET_ACCESS_KEY'),
            'r2_bucket_name': os.getenv('R2_BUCKET_NAME'),
            'r2_endpoint': os.getenv('R2_ENDPOINT')
        }
    
    @classmethod
    def is_render_mode(cls) -> bool:
        """Check if running in Render mode (external services)"""
        return os.getenv('DEPLOYMENT_MODE', 'local').lower() == 'render'
    
    @classmethod
    def is_local_mode(cls) -> bool:
        """Check if running in local mode (Docker services)"""
        return os.getenv('DEPLOYMENT_MODE', 'local').lower() == 'local'
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development environment"""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'development'
    
    @classmethod
    def get_all_config(cls) -> Dict[str, Any]:
        """Get all configuration as a single dictionary"""
        return {
            'database': cls.get_db_config(),
            'rabbitmq': cls.get_rabbitmq_config(),
            'logging': cls.get_logging_config(),
            'health_check': cls.get_health_check_config(),
            'service': cls.get_service_config(),
            'media': cls.get_media_config()
        }