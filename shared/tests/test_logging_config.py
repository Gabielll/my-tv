"""
Tests for structured logging functionality
"""
import json
import logging
import uuid
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

from shared.logging_config import configure_logging, get_logger, generate_correlation_id, CorrelationContext, StructuredLogger


class TestLoggingConfig:
    """Test structured logging configuration"""
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation"""
        correlation_id = generate_correlation_id()
        
        # Should be a valid string with req_ prefix
        assert isinstance(correlation_id, str)
        assert correlation_id.startswith("req_")
        assert len(correlation_id) == 16  # req_ + 12 hex chars
        
        # Should be unique
        correlation_id2 = generate_correlation_id()
        assert correlation_id != correlation_id2
    
    def test_structured_logger_creation(self):
        """Test structured logger creation"""
        logger = get_logger("test-service")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.service_name == "test-service"
    
    def test_correlation_context_manager(self):
        """Test correlation ID context manager"""
        test_id = "test-correlation-id"
        
        with CorrelationContext(test_id) as correlation_id:
            assert correlation_id == test_id
            
            # Test that logger can access correlation ID
            logger = get_logger("test")
            assert logger.get_correlation_id() == test_id
    
    def test_correlation_context_nesting(self):
        """Test nested correlation contexts"""
        outer_id = "outer-correlation"
        inner_id = "inner-correlation"
        
        with CorrelationContext(outer_id):
            logger = get_logger("test")
            assert logger.get_correlation_id() == outer_id
            
            with CorrelationContext(inner_id):
                assert logger.get_correlation_id() == inner_id
            
            # Should restore outer context
            assert logger.get_correlation_id() == outer_id
    
    def test_logger_methods(self):
        """Test that logger methods work correctly"""
        logger = get_logger("test-service")
        
        # Test that methods exist and can be called
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # Test audit logging
        logger.audit("user_login", "user_123", context={"ip": "192.168.1.1"})
        
        # Should not raise any exceptions
        assert True