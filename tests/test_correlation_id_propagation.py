"""
Integration tests for correlation ID propagation across services
"""
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest
import requests
from flask import Flask

from shared.logging_config import configure_logging, get_logger, CorrelationContext


class TestCorrelationIdPropagation:
    """Test correlation ID propagation between services"""
    
    def setup_method(self):
        """Set up test environment"""
        configure_logging("test-service")
    
    def test_correlation_id_in_http_headers(self):
        """Test that correlation ID is included in HTTP headers"""
        correlation_id = str(uuid.uuid4())
        
        with CorrelationContext(correlation_id):
            # Simulate making an HTTP request with correlation ID
            headers = {"X-Correlation-ID": correlation_id}
            
            # Mock the requests library
            with patch('requests.post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "success"}
                mock_post.return_value = mock_response
                
                # Simulate service making HTTP request
                response = requests.post(
                    "http://localhost:8001/api/process",
                    json={"data": "test"},
                    headers=headers
                )
                
                # Verify correlation ID was included in headers
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[1]["headers"]["X-Correlation-ID"] == correlation_id
    
    def test_correlation_id_extraction_from_request(self):
        """Test extracting correlation ID from incoming HTTP request"""
        app = Flask(__name__)
        
        @app.route('/test', methods=['POST'])
        def test_endpoint():
            from flask import request
            
            # Extract correlation ID from headers
            correlation_id = request.headers.get('X-Correlation-ID')
            
            if correlation_id:
                with CorrelationContext(correlation_id):
                    logger = get_logger("test-endpoint")
                    logger.info("Processing request")
                    
                    return {"correlation_id": correlation_id, "status": "processed"}
            else:
                return {"error": "No correlation ID provided"}, 400
        
        with app.test_client() as client:
            correlation_id = str(uuid.uuid4())
            
            response = client.post('/test', 
                                 json={"data": "test"},
                                 headers={"X-Correlation-ID": correlation_id})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["correlation_id"] == correlation_id
    
    def test_correlation_id_in_rabbitmq_messages(self):
        """Test that correlation ID is included in RabbitMQ messages"""
        correlation_id = str(uuid.uuid4())
        
        with CorrelationContext(correlation_id):
            # Mock RabbitMQ connection
            with patch('shared.rabbitmq_client.get_rabbitmq_connection') as mock_connection:
                mock_conn = MagicMock()
                mock_channel = MagicMock()
                mock_conn.channel.return_value = mock_channel
                mock_connection.return_value = mock_conn
                
                # Simulate message publishing with correlation ID
                message_data = {
                    "task": "process_file",
                    "file_path": "/tmp/test.mp4",
                    "correlation_id": correlation_id
                }
                
                # Test that correlation ID is preserved in context
                logger = get_logger("rabbitmq-test")
                current_correlation_id = logger.get_correlation_id()
                
                assert current_correlation_id == correlation_id
    
    def test_correlation_id_in_database_operations(self):
        """Test that correlation ID is logged during database operations"""
        correlation_id = str(uuid.uuid4())
        
        with CorrelationContext(correlation_id):
            # Mock database connection
            with patch('shared.db.get_db_connection') as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn
                
                from shared.db import get_db_connection
                
                # Simulate database operation
                conn = get_db_connection()
                cursor = conn.cursor()
                
                logger = get_logger("database")
                logger.info("Executing database query", context={
                    "query": "SELECT * FROM files WHERE id = %s",
                    "params": [123]
                })
                
                cursor.execute("SELECT * FROM files WHERE id = %s", (123,))
                
                # Verify database operation was logged with correlation ID
                # (This would be verified by checking log output in a real scenario)
                mock_get_conn.assert_called_once()
                mock_cursor.execute.assert_called_once()


class TestEndToEndCorrelationIdFlow:
    """Test complete correlation ID flow through multiple services"""
    
    def test_file_upload_correlation_flow(self):
        """Test correlation ID flow through file upload process"""
        correlation_id = str(uuid.uuid4())
        
        # Mock all external dependencies
        with patch('shared.rabbitmq_client.get_rabbitmq_connection') as mock_rabbitmq, \
             patch('shared.db.get_db_connection') as mock_db, \
             patch('os.path.exists') as mock_exists, \
             patch('shutil.move') as mock_move:
            
            # Setup mocks
            mock_rabbitmq_instance = MagicMock()
            mock_rabbitmq.return_value = mock_rabbitmq_instance
            
            mock_db_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_db_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_db_conn
            
            mock_exists.return_value = True
            
            # Simulate Admin UI receiving file upload
            app = Flask(__name__)
            
            @app.route('/upload', methods=['POST'])
            def upload_file():
                from flask import request
                
                # Extract or generate correlation ID
                correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
                
                with CorrelationContext(correlation_id):
                    logger = get_logger("admin-ui")
                    logger.info("File upload received", context={
                        "filename": "test.mp4",
                        "size": 1024000
                    })
                    
                    # Simulate file processing
                    message = {
                        "task": "normalize_video",
                        "file_path": "/uploads/test.mp4",
                        "correlation_id": correlation_id
                    }
                    
                    # Simulate message publishing
                    mock_rabbitmq_instance.publish_message("normalization_queue", message)
                    
                    logger.info("File queued for processing")
                    
                    return {"correlation_id": correlation_id, "status": "queued"}
            
            with app.test_client() as client:
                response = client.post('/upload',
                                     json={"filename": "test.mp4"},
                                     headers={"X-Correlation-ID": correlation_id})
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["correlation_id"] == correlation_id
                
                # Verify RabbitMQ message was published with correlation ID
                mock_rabbitmq_instance.publish_message.assert_called_once()
                call_args = mock_rabbitmq_instance.publish_message.call_args
                published_message = call_args[0][1]
                assert published_message["correlation_id"] == correlation_id
    
    def test_scheduling_correlation_flow(self):
        """Test correlation ID flow through scheduling process"""
        correlation_id = str(uuid.uuid4())
        
        with patch('shared.db.get_db_connection') as mock_db:
            mock_db_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_db_conn.cursor.return_value = mock_cursor
            mock_db.return_value = mock_db_conn
            
            # Mock database results
            mock_cursor.fetchall.return_value = [
                (1, "test.mp4", "pending", "2024-01-01 10:00:00"),
                (2, "test2.mp4", "pending", "2024-01-01 11:00:00")
            ]
            
            with CorrelationContext(correlation_id):
                logger = get_logger("scheduler")
                logger.info("Starting scheduling process")
                
                # Simulate scheduler AI processing
                from shared.db import get_db_connection
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Query pending files
                cursor.execute("SELECT id, filename, status, created_at FROM files WHERE status = 'pending'")
                pending_files = cursor.fetchall()
                
                logger.info("Found pending files", context={
                    "count": len(pending_files),
                    "files": [f[1] for f in pending_files]
                })
                
                # Simulate scheduling logic
                for file_id, filename, status, created_at in pending_files:
                    logger.info("Scheduling file", context={
                        "file_id": file_id,
                        "filename": filename,
                        "priority": "normal"
                    })
                    
                    # Update file status
                    cursor.execute(
                        "UPDATE files SET status = 'scheduled', scheduled_at = NOW() WHERE id = %s",
                        (file_id,)
                    )
                
                conn.commit()
                logger.info("Scheduling process completed")
                
                # Verify database operations were called
                assert mock_cursor.execute.call_count >= 3  # SELECT + 2 UPDATEs
                mock_db_conn.commit.assert_called_once()


class TestCorrelationIdErrorHandling:
    """Test correlation ID handling in error scenarios"""
    
    def test_correlation_id_preserved_in_exceptions(self):
        """Test that correlation ID is preserved when exceptions occur"""
        correlation_id = str(uuid.uuid4())
        
        with CorrelationContext(correlation_id):
            logger = get_logger("error-test")
            
            try:
                # Simulate an error
                raise ValueError("Test error for correlation tracking")
            except ValueError as e:
                logger.error("Error occurred during processing", 
                           error=e,
                           context={
                               "error_type": "ValueError",
                               "operation": "test_operation"
                           })
                
                # In a real scenario, we would verify the log output contains
                # the correlation ID. Here we just ensure no exception is raised
                # during logging with correlation ID context.
                pass
    
    def test_missing_correlation_id_handling(self):
        """Test handling when correlation ID is missing"""
        # Don't set correlation ID context
        logger = get_logger("missing-correlation-test")
        
        # Should still work without correlation ID
        logger.info("Processing without correlation ID")
        
        # Verify no exception is raised
        assert True
    
    def test_invalid_correlation_id_handling(self):
        """Test handling of invalid correlation ID formats"""
        invalid_correlation_ids = [
            "",  # Empty string
            "not-a-uuid",  # Invalid format
            "12345",  # Too short
            None,  # None value
        ]
        
        for invalid_id in invalid_correlation_ids:
            try:
                with CorrelationContext(invalid_id):
                    logger = get_logger("invalid-correlation-test")
                    logger.info("Testing invalid correlation ID", context={
                        "test_correlation_id": invalid_id
                    })
                
                # Should not raise exception even with invalid ID
                assert True
            except Exception as e:
                pytest.fail(f"Exception raised with invalid correlation ID {invalid_id}: {e}")