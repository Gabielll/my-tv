"""
Tests for error logging and context preservation
"""
import json
import logging
import traceback
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

from shared.logging_config import configure_logging, get_logger, CorrelationContext


class TestErrorLoggingContext:
    """Test error logging with context preservation"""
    
    def setup_method(self):
        """Set up test environment"""
        configure_logging("error-test-service")
    
    def test_exception_logging_with_stack_trace(self):
        """Test that exceptions are logged with full stack traces"""
        logger = get_logger("exception-test")
        
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        
        try:
            # Create a nested exception scenario
            def inner_function():
                raise ValueError("Inner function error")
            
            def outer_function():
                try:
                    inner_function()
                except ValueError:
                    raise RuntimeError("Outer function error") from None
            
            outer_function()
            
        except RuntimeError as e:
            logger.error("Error in processing pipeline", 
                        exc_info=True,
                        extra={
                            "operation": "file_processing",
                            "file_path": "/tmp/test.mp4",
                            "stage": "normalization"
                        })
        
        # Parse JSON log output
        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["level"] == "ERROR"
        assert "Error in processing pipeline" in log_data["message"]
        assert log_data["operation"] == "file_processing"
        assert log_data["file_path"] == "/tmp/test.mp4"
        assert log_data["stage"] == "normalization"
        
        # Should contain stack trace information
        assert "RuntimeError" in log_data["message"] or "traceback" in log_data
        
        logger.removeHandler(handler)
    
    def test_error_context_preservation_across_services(self):
        """Test that error context is preserved when passing between services"""
        correlation_id = "test-correlation-123"
        
        with CorrelationContext(correlation_id):
            # Simulate error in Media Manager
            media_logger = get_logger("media-manager")
            
            stream = StringIO()
            handler = logging.StreamHandler(stream)
            media_logger.addHandler(handler)
            
            try:
                # Simulate file processing error
                raise IOError("Failed to read file: /uploads/corrupted.mp4")
            except IOError as e:
                media_logger.error("File processing failed",
                                 error=e,
                                 context={
                                     "service": "media-manager",
                                     "operation": "file_validation",
                                     "file_path": "/uploads/corrupted.mp4",
                                     "file_size": 0,
                                     "error_code": "FILE_CORRUPTED"
                                 })
            
            # Parse log output
            log_output = stream.getvalue().strip()
            log_data = json.loads(log_output)
            
            # Verify all context is preserved
            assert log_data["correlation_id"] == correlation_id
            assert log_data["service"] == "media-manager"
            assert log_data["operation"] == "file_validation"
            assert log_data["file_path"] == "/uploads/corrupted.mp4"
            assert log_data["error_code"] == "FILE_CORRUPTED"
            
            media_logger.removeHandler(handler)
    
    def test_performance_error_logging(self):
        """Test logging of performance-related errors"""
        logger = get_logger("performance-test")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        
        # Simulate performance issue
        import time
        start_time = time.time()
        
        # Simulate slow operation
        time.sleep(0.1)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Log performance warning if operation is slow
        if duration_ms > 50:  # 50ms threshold
            logger.warning("Slow operation detected",
                         extra={
                             "operation": "video_normalization",
                             "duration_ms": duration_ms,
                             "threshold_ms": 50,
                             "file_path": "/tmp/large_video.mp4",
                             "file_size_mb": 500,
                             "performance_issue": True
                         })
        
        # Parse log output
        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["level"] == "WARNING"
        assert log_data["operation"] == "video_normalization"
        assert log_data["duration_ms"] > 50
        assert log_data["performance_issue"] is True
        
        logger.removeHandler(handler)
    
    def test_database_error_context(self):
        """Test database error logging with query context"""
        logger = get_logger("database-test")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        
        # Simulate database error
        query = "INSERT INTO files (filename, status) VALUES (%s, %s)"
        params = ("test.mp4", "pending")
        
        try:
            # Simulate database connection error
            raise Exception("connection to server at \"localhost\" (127.0.0.1), port 5432 failed")
        except Exception as e:
            logger.error("Database operation failed",
                        exc_info=True,
                        extra={
                            "operation": "database_insert",
                            "query": query,
                            "params": params,
                            "database": "media_processing",
                            "table": "files",
                            "retry_count": 3,
                            "error_type": "connection_error"
                        })
        
        # Parse log output
        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["level"] == "ERROR"
        assert log_data["operation"] == "database_insert"
        assert log_data["query"] == query
        assert log_data["params"] == list(params)
        assert log_data["retry_count"] == 3
        assert log_data["error_type"] == "connection_error"
        
        logger.removeHandler(handler)
    
    def test_rabbitmq_error_context(self):
        """Test RabbitMQ error logging with message context"""
        logger = get_logger("rabbitmq-test")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        
        # Simulate RabbitMQ publishing error
        message_data = {
            "task": "normalize_video",
            "file_path": "/uploads/test.mp4",
            "priority": "high"
        }
        
        try:
            # Simulate RabbitMQ connection error
            raise Exception("Connection to RabbitMQ failed: [Errno 111] Connection refused")
        except Exception as e:
            logger.error("Failed to publish message to queue",
                        exc_info=True,
                        extra={
                            "operation": "message_publish",
                            "queue": "normalization_queue",
                            "message": message_data,
                            "exchange": "media_processing",
                            "routing_key": "video.normalize",
                            "retry_attempt": 2,
                            "max_retries": 5
                        })
        
        # Parse log output
        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["level"] == "ERROR"
        assert log_data["operation"] == "message_publish"
        assert log_data["queue"] == "normalization_queue"
        assert log_data["message"] == message_data
        assert log_data["retry_attempt"] == 2
        
        logger.removeHandler(handler)


class TestAuditLogging:
    """Test audit logging for administrative actions"""
    
    def setup_method(self):
        """Set up test environment"""
        configure_logging("audit-test-service")
    
    def test_file_upload_audit_log(self):
        """Test audit logging for file uploads"""
        correlation_id = "audit-test-123"
        
        with CorrelationContext(correlation_id):
            logger = get_logger("admin-ui")
            
            stream = StringIO()
            handler = logging.StreamHandler(stream)
            logger.addHandler(handler)
            
            # Simulate file upload audit log
            logger.audit("file_upload", "presentation.mp4", context={
                "user_id": "admin_user",
                "filename": "presentation.mp4",
                "file_size": 157286400,  # ~150MB
                "file_type": "video/mp4",
                "upload_source": "web_interface",
                "client_ip": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            # Parse log output
            log_output = stream.getvalue().strip()
            log_data = json.loads(log_output)
            
            assert log_data["audit"] is True
            assert log_data["action"] == "file_upload"
            assert log_data["user_id"] == "admin_user"
            assert log_data["filename"] == "presentation.mp4"
            assert log_data["correlation_id"] == correlation_id
            
            logger.removeHandler(handler)
    
    def test_scheduling_rule_audit_log(self):
        """Test audit logging for scheduling rule changes"""
        logger = get_logger("scheduler-ai")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        
        # Simulate scheduling rule modification
        logger.info("Scheduling rule updated",
                   extra={
                       "audit": True,
                       "action": "rule_update",
                       "user_id": "admin_user",
                       "rule_id": "priority_rule_1",
                       "old_priority": "normal",
                       "new_priority": "high",
                       "rule_condition": "file_size > 100MB",
                       "affected_files_count": 15
                   })
        
        # Parse log output
        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["audit"] is True
        assert log_data["action"] == "rule_update"
        assert log_data["rule_id"] == "priority_rule_1"
        assert log_data["old_priority"] == "normal"
        assert log_data["new_priority"] == "high"
        
        logger.removeHandler(handler)
    
    def test_system_configuration_audit_log(self):
        """Test audit logging for system configuration changes"""
        logger = get_logger("admin-ui")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        
        # Simulate system configuration change
        logger.warning("System configuration modified",
                      extra={
                          "audit": True,
                          "action": "config_change",
                          "user_id": "admin_user",
                          "config_section": "processing_limits",
                          "config_key": "max_concurrent_jobs",
                          "old_value": 5,
                          "new_value": 10,
                          "change_reason": "Increased server capacity"
                      })
        
        # Parse log output
        log_output = stream.getvalue().strip()
        log_data = json.loads(log_output)
        
        assert log_data["level"] == "WARNING"
        assert log_data["audit"] is True
        assert log_data["action"] == "config_change"
        assert log_data["config_key"] == "max_concurrent_jobs"
        assert log_data["old_value"] == 5
        assert log_data["new_value"] == 10
        
        logger.removeHandler(handler)


class TestLogAggregationAndAnalysis:
    """Test log aggregation and analysis scenarios"""
    
    def test_log_correlation_across_request_lifecycle(self):
        """Test log correlation throughout a complete request lifecycle"""
        correlation_id = "lifecycle-test-456"
        
        logs_captured = []
        
        class LogCapture(logging.Handler):
            def emit(self, record):
                logs_captured.append(json.loads(self.format(record)))
        
        # Set up log capture
        capture_handler = LogCapture()
        capture_handler.setFormatter(logging.Formatter('%(message)s'))
        
        with CorrelationContext(correlation_id):
            # Stage 1: Admin UI receives upload
            admin_logger = get_logger("admin-ui")
            admin_logger.addHandler(capture_handler)
            admin_logger.info("Upload request received", context={"stage": "upload_start"})
            
            # Stage 2: Media Manager processes file
            media_logger = get_logger("media-manager")
            media_logger.addHandler(capture_handler)
            media_logger.info("File validation started", context={"stage": "validation"})
            media_logger.info("File moved to processing directory", context={"stage": "file_move"})
            
            # Stage 3: Normalization Worker processes
            worker_logger = get_logger("normalization-worker")
            worker_logger.addHandler(capture_handler)
            worker_logger.info("Video normalization started", context={"stage": "normalization_start"})
            worker_logger.info("Video normalization completed", context={"stage": "normalization_complete"})
            
            # Stage 4: Scheduler AI updates status
            scheduler_logger = get_logger("scheduler-ai")
            scheduler_logger.addHandler(capture_handler)
            scheduler_logger.info("File status updated", context={"stage": "status_update"})
        
        # Verify all logs have the same correlation ID
        assert len(logs_captured) == 6
        for log_entry in logs_captured:
            assert log_entry["correlation_id"] == correlation_id
        
        # Verify stages are in correct order
        stages = [log["stage"] for log in logs_captured]
        expected_stages = [
            "upload_start", "validation", "file_move", 
            "normalization_start", "normalization_complete", "status_update"
        ]
        assert stages == expected_stages
    
    def test_error_rate_monitoring_logs(self):
        """Test logs suitable for error rate monitoring"""
        logger = get_logger("monitoring-test")
        
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        
        # Simulate various error scenarios for monitoring
        error_scenarios = [
            {"error_type": "file_not_found", "severity": "ERROR"},
            {"error_type": "database_timeout", "severity": "ERROR"},
            {"error_type": "rabbitmq_connection_lost", "severity": "ERROR"},
            {"error_type": "ffmpeg_process_failed", "severity": "ERROR"},
            {"error_type": "disk_space_low", "severity": "WARNING"},
        ]
        
        for scenario in error_scenarios:
            if scenario["severity"] == "ERROR":
                logger.error(f"System error: {scenario['error_type']}",
                           extra={
                               "error_category": scenario["error_type"],
                               "monitoring": True,
                               "alert_level": "high" if scenario["error_type"] != "file_not_found" else "medium"
                           })
            else:
                logger.warning(f"System warning: {scenario['error_type']}",
                             extra={
                                 "error_category": scenario["error_type"],
                                 "monitoring": True,
                                 "alert_level": "low"
                             })
        
        # Parse all log outputs
        log_lines = stream.getvalue().strip().split('\n')
        
        error_count = 0
        warning_count = 0
        
        for line in log_lines:
            log_data = json.loads(line)
            assert log_data["monitoring"] is True
            
            if log_data["level"] == "ERROR":
                error_count += 1
            elif log_data["level"] == "WARNING":
                warning_count += 1
        
        assert error_count == 4
        assert warning_count == 1
        
        logger.removeHandler(handler)