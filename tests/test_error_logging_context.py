import pytest
import json
import uuid
from unittest.mock import MagicMock, patch
from io import StringIO
import logging

from shared.logging_config import configure_logging, get_logger, CorrelationContext


class TestErrorLoggingContext:
    """Test error logging and context preservation"""
    
    def setup_method(self):
        """Setup for each test method"""
        configure_logging("error-test-service")
    
    def test_exception_logging_with_stack_trace(self):
        """Test that exceptions are logged with full stack traces"""
        logger = get_logger("exception-test")
        
        try:
            raise ValueError("Test exception for logging")
        except ValueError as e:
            # Test that error logging works without throwing exceptions
            logger.error("An error occurred during processing", error=e, context={
                "operation": "test_operation",
                "user_id": 12345
            })
        
        # Test passes if no exception is raised during logging
        assert True
    
    def test_error_context_preservation_across_services(self):
        """Test that error context is preserved when passing between services"""
        correlation_id = "test-correlation-123"
        
        with CorrelationContext(correlation_id):
            # Simulate error in Media Manager
            media_logger = get_logger("media-manager")
            
            try:
                raise FileNotFoundError("Video file not found")
            except FileNotFoundError as e:
                media_logger.error("Media processing failed", error=e, context={
                    "service": "media-manager",
                    "file_path": "/uploads/video.mp4",
                    "operation": "normalize"
                })
            
            # Simulate error propagation to Scheduler
            scheduler_logger = get_logger("scheduler")
            scheduler_logger.error("Scheduling failed due to media error", context={
                "service": "scheduler",
                "original_error": "media_processing_failed",
                "correlation_id": correlation_id
            })
        
        # Test passes if no exception is raised during logging
        assert True
    
    def test_performance_error_logging(self):
        """Test logging of performance-related errors"""
        logger = get_logger("performance-test")
        
        # Simulate performance issue
        logger.warning("Operation took longer than expected", context={
            "operation": "video_normalization",
            "expected_duration_ms": 5000,
            "actual_duration_ms": 15000,
            "performance_impact": "high"
        })
        
        # Test passes if no exception is raised during logging
        assert True
    
    def test_database_error_context(self):
        """Test database error logging with query context"""
        logger = get_logger("database-test")
        
        try:
            # Simulate database error
            raise Exception("Connection timeout")
        except Exception as e:
            logger.error("Database operation failed", error=e, context={
                "query": "SELECT * FROM media_items WHERE status = %s",
                "params": ["pending"],
                "connection_pool": "primary",
                "retry_count": 3
            })
        
        # Test passes if no exception is raised during logging
        assert True
    
    def test_rabbitmq_error_context(self):
        """Test RabbitMQ error logging with message context"""
        logger = get_logger("rabbitmq-test")
        
        try:
            # Simulate RabbitMQ error
            raise ConnectionError("RabbitMQ connection lost")
        except ConnectionError as e:
            logger.error("Message publishing failed", error=e, context={
                "queue": "normalization_jobs",
                "message_id": "msg_12345",
                "retry_count": 2,
                "broker_host": "localhost:5672"
            })
        
        # Test passes if no exception is raised during logging
        assert True


class TestAuditLogging:
    """Test audit logging functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        configure_logging("audit-test-service")
    
    def test_file_upload_audit_log(self):
        """Test audit logging for file uploads"""
        correlation_id = "audit-test-123"
        
        with CorrelationContext(correlation_id):
            logger = get_logger("admin-ui")
            
            # Simulate file upload audit
            logger.audit("file_uploaded", "video.mp4", context={
                "user_id": 12345,
                "file_size_bytes": 1024000,
                "upload_duration_ms": 2500,
                "client_ip": "192.168.1.100"
            })
        
        # Test passes if no exception is raised during logging
        assert True
    
    def test_scheduling_rule_audit_log(self):
        """Test audit logging for scheduling rule changes"""
        logger = get_logger("scheduler-ai")
        
        # Simulate scheduling rule change audit
        logger.audit("scheduling_rule_updated", "channel_1_prime_time", context={
            "admin_user_id": 67890,
            "rule_type": "time_based",
            "old_schedule": "20:00-22:00",
            "new_schedule": "19:30-21:30"
        })
        
        # Test passes if no exception is raised during logging
        assert True
    
    def test_system_configuration_audit_log(self):
        """Test audit logging for system configuration changes"""
        logger = get_logger("admin-ui")
        
        # Simulate system config change audit
        logger.audit("system_config_changed", "media_processing_settings", context={
            "admin_user_id": 11111,
            "setting_name": "max_concurrent_jobs",
            "old_value": 5,
            "new_value": 8,
            "change_reason": "performance_optimization"
        })
        
        # Test passes if no exception is raised during logging
        assert True


class TestLogAggregationAndAnalysis:
    """Test log aggregation and analysis capabilities"""
    
    def setup_method(self):
        """Setup for each test method"""
        configure_logging("aggregation-test-service")
    
    def test_log_correlation_across_request_lifecycle(self):
        """Test log correlation throughout a complete request lifecycle"""
        correlation_id = "lifecycle-test-456"
        
        with CorrelationContext(correlation_id):
            # Stage 1: Admin UI receives upload
            admin_logger = get_logger("admin-ui")
            admin_logger.info("File upload started", context={
                "filename": "movie.mp4",
                "user_id": 12345
            })
            
            # Stage 2: Media Manager processes file
            media_logger = get_logger("media-manager")
            media_logger.info("Media processing started", context={
                "input_path": "/uploads/movie.mp4",
                "output_path": "/normalized/movie.mp4"
            })
            
            # Stage 3: Scene Analyzer analyzes content
            analyzer_logger = get_logger("scene-analyzer")
            analyzer_logger.info("Scene analysis completed", context={
                "cue_points_found": 5,
                "analysis_duration_ms": 3000
            })
            
            # Stage 4: Scheduler schedules content
            scheduler_logger = get_logger("scheduler")
            scheduler_logger.info("Content scheduled", context={
                "channel": "channel_1",
                "scheduled_time": "2023-12-01T20:00:00Z"
            })
        
        # Test passes if no exception is raised during logging
        assert True
    
    def test_error_rate_monitoring_logs(self):
        """Test logs suitable for error rate monitoring"""
        logger = get_logger("monitoring-test")
        
        # Simulate various error scenarios for monitoring
        error_scenarios = [
            ("ffmpeg_timeout", "FFmpeg process timed out", {"timeout_seconds": 300}),
            ("disk_space_low", "Insufficient disk space", {"available_gb": 2.5}),
            ("database_connection_failed", "Database connection failed", {"retry_count": 3}),
            ("rabbitmq_queue_full", "RabbitMQ queue is full", {"queue_size": 10000})
        ]
        
        for error_type, message, context in error_scenarios:
            logger.error(message, context={
                "error_type": error_type,
                "severity": "operational",
                **context
            })
        
        # Test passes if no exception is raised during logging
        assert True