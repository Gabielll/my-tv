import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import threading

# Thread-local storage for correlation IDs
_local = threading.local()

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
        self.hostname = os.getenv('HOSTNAME', 'unknown')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.version = os.getenv('SERVICE_VERSION', '1.0.0')
    
    def format(self, record):
        # Get correlation ID from thread-local storage
        correlation_id = getattr(_local, 'correlation_id', None)
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'service': self.service_name,
            'hostname': self.hostname,
            'environment': self.environment,
            'version': self.version,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add correlation ID if available
        if correlation_id:
            log_entry['correlation_id'] = correlation_id
        
        # Add extra context if provided
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
        
        # Add duration if provided
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        
        # Add error details if it's an error log
        if record.exc_info:
            log_entry['error'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add severity for operational classification
        if hasattr(record, 'severity'):
            log_entry['severity'] = record.severity
        
        return json.dumps(log_entry, ensure_ascii=False)

class StructuredLogger:
    """Structured logger with correlation ID support and context management"""
    
    def __init__(self, service_name: str, correlation_id: Optional[str] = None):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        
        if correlation_id:
            self.set_correlation_id(correlation_id)
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current thread"""
        _local.correlation_id = correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for current thread"""
        return getattr(_local, 'correlation_id', None)
    
    def _log(self, level: int, message: str, context: Optional[Dict[str, Any]] = None, 
             duration_ms: Optional[float] = None, severity: Optional[str] = None, 
             error: Optional[Exception] = None):
        """Internal logging method with context support"""
        extra = {}
        
        if context:
            extra['context'] = context
        
        if duration_ms is not None:
            extra['duration_ms'] = duration_ms
        
        if severity:
            extra['severity'] = severity
        
        if error:
            self.logger.log(level, message, exc_info=(type(error), error, error.__traceback__), extra=extra)
        else:
            self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, context, **kwargs)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, context, **kwargs)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, context, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, 
              context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log error message with optional exception"""
        self._log(logging.ERROR, message, context, error=error, **kwargs)
    
    def critical(self, message: str, error: Optional[Exception] = None, 
                 context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log critical message with optional exception"""
        self._log(logging.CRITICAL, message, context, error=error, **kwargs)
    
    def audit(self, action: str, resource: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """Log audit message for tracking important actions"""
        audit_context = {
            'action': action,
            'resource': resource,
            'audit': True
        }
        
        if context:
            audit_context.update(context)
        
        self._log(logging.INFO, f"Audit: {action} on {resource}", audit_context, **kwargs)

def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return f"req_{uuid.uuid4().hex[:12]}"

def configure_logging(service_name: str, level: str = None, format_type: str = None) -> None:
    """Configure logging for the service"""
    # Get configuration from environment variables
    log_level = level or os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = format_type or os.getenv('LOG_FORMAT', 'json').lower()
    log_output = os.getenv('LOG_OUTPUT', 'console').lower()
    
    # Set logging level
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create handler based on output configuration
    if log_output == 'file':
        log_file = os.getenv('LOG_FILE', f'/var/log/{service_name}.log')
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on format configuration
    if log_format == 'json':
        formatter = StructuredFormatter(service_name)
    else:
        # Fallback to standard format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    handler.setLevel(numeric_level)
    
    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)
    
    # Disable propagation for third-party loggers to avoid noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('pika').setLevel(logging.WARNING)

def get_logger(service_name: str, correlation_id: Optional[str] = None) -> StructuredLogger:
    """Get a structured logger instance for the service"""
    return StructuredLogger(service_name, correlation_id)

# Context manager for correlation ID
class CorrelationContext:
    """Context manager for setting correlation ID for a block of code"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_correlation_id()
        self.previous_id = None
    
    def __enter__(self):
        self.previous_id = getattr(_local, 'correlation_id', None)
        _local.correlation_id = self.correlation_id
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_id:
            _local.correlation_id = self.previous_id
        else:
            if hasattr(_local, 'correlation_id'):
                delattr(_local, 'correlation_id')