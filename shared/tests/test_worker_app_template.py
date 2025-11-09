import unittest
import threading
import time
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from shared.worker_app_template import WorkerWebService, create_worker_web_service


class TestWorkerAppTemplate(unittest.TestCase):
    """Test cases for the worker app template."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_service_name = 'test-worker'
        self.worker_called = False
        self.worker_call_count = 0
        
    def test_worker_function(self):
        """Simple test worker function."""
        self.worker_called = True
        self.worker_call_count += 1
        time.sleep(0.1)  # Simulate some work
        
    def failing_worker_function(self):
        """Worker function that always fails."""
        self.worker_call_count += 1
        raise Exception("Test worker error")
    
    def test_worker_web_service_creation(self):
        """Test creating a WorkerWebService instance."""
        # Create service
        service = WorkerWebService(
            service_name=self.test_service_name,
            worker_function=self.test_worker_function
        )
        
        # Verify initialization
        self.assertEqual(service.service_name, self.test_service_name)
        self.assertIsNotNone(service.app)
        self.assertIsNotNone(service.worker_thread)
        self.assertTrue(service.worker_thread.is_alive())
        
        # Verify basic functionality
        self.assertIn('status', service.worker_status)
        self.assertIn('started_at', service.worker_status)
    
    @patch('shared.logging_config.configure_logging')
    @patch('shared.logging_config.get_logger')
    @patch('shared.health_check.create_standard_health_checker')
    def test_flask_app_endpoints(self, mock_health_checker, mock_get_logger, mock_configure_logging):
        """Test that Flask app has required endpoints."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_health_checker.return_value = MagicMock()
        
        # Create service
        service = WorkerWebService(
            service_name=self.test_service_name,
            worker_function=self.test_worker_function
        )
        
        # Test client
        with service.app.test_client() as client:
            # Test root endpoint
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['service'], self.test_service_name)
            self.assertEqual(data['type'], 'worker-web-service')
            
            # Test worker status endpoint
            response = client.get('/worker/status')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('status', data)
            self.assertIn('started_at', data)
    
    @patch('shared.logging_config.configure_logging')
    @patch('shared.logging_config.get_logger')
    @patch('shared.health_check.create_standard_health_checker')
    def test_health_endpoint(self, mock_health_checker, mock_get_logger, mock_configure_logging):
        """Test health check endpoint."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_health_checker.return_value = MagicMock()
        
        # Create service
        service = WorkerWebService(
            service_name=self.test_service_name,
            worker_function=self.test_worker_function
        )
        
        # Wait a moment for worker to start
        time.sleep(0.2)
        
        # Test health endpoint
        with service.app.test_client() as client:
            response = client.get('/health')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertEqual(data['service'], self.test_service_name)
            self.assertIn('status', data)
            self.assertIn('worker', data)
            self.assertTrue(data['worker']['thread_alive'])
    
    @patch('shared.logging_config.configure_logging')
    @patch('shared.logging_config.get_logger')
    @patch('shared.health_check.create_standard_health_checker')
    def test_worker_function_execution(self, mock_health_checker, mock_get_logger, mock_configure_logging):
        """Test that worker function is executed."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_health_checker.return_value = MagicMock()
        
        # Create service
        service = WorkerWebService(
            service_name=self.test_service_name,
            worker_function=self.test_worker_function
        )
        
        # Wait for worker to execute
        time.sleep(0.3)
        
        # Verify worker was called
        self.assertTrue(self.worker_called)
        self.assertGreater(self.worker_call_count, 0)
    
    @patch('shared.logging_config.configure_logging')
    @patch('shared.logging_config.get_logger')
    @patch('shared.health_check.create_standard_health_checker')
    def test_worker_error_handling(self, mock_health_checker, mock_get_logger, mock_configure_logging):
        """Test worker error handling and recovery."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_health_checker.return_value = MagicMock()
        
        # Create service with failing worker
        service = WorkerWebService(
            service_name=self.test_service_name,
            worker_function=self.failing_worker_function
        )
        
        # Wait for worker to fail and retry
        time.sleep(0.5)
        
        # Verify error count increased (since we're mocking the logger, we check the service state)
        self.assertGreater(service.worker_status['error_count'], 0)
        self.assertIsNotNone(service.worker_status['last_error'])
    
    @patch('shared.logging_config.configure_logging')
    @patch('shared.logging_config.get_logger')
    @patch('shared.health_check.create_standard_health_checker')
    def test_custom_health_check(self, mock_health_checker, mock_get_logger, mock_configure_logging):
        """Test custom health check functionality."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_health_checker.return_value = MagicMock()
        
        # Custom health check function
        def custom_health():
            return {'custom_status': 'ok', 'custom_value': 42}
        
        # Create service with custom health check
        service = WorkerWebService(
            service_name=self.test_service_name,
            worker_function=self.test_worker_function,
            custom_health_check=custom_health
        )
        
        # Test health endpoint
        with service.app.test_client() as client:
            response = client.get('/health')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            self.assertIn('custom', data)
            self.assertEqual(data['custom']['custom_status'], 'ok')
            self.assertEqual(data['custom']['custom_value'], 42)
    
    @patch('shared.logging_config.configure_logging')
    @patch('shared.logging_config.get_logger')
    @patch('shared.health_check.create_standard_health_checker')
    def test_factory_function(self, mock_health_checker, mock_get_logger, mock_configure_logging):
        """Test the factory function."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_health_checker.return_value = MagicMock()
        
        # Create service using factory function
        service = create_worker_web_service(
            service_name=self.test_service_name,
            worker_function=self.test_worker_function
        )
        
        # Verify it's a WorkerWebService instance
        self.assertIsInstance(service, WorkerWebService)
        self.assertEqual(service.service_name, self.test_service_name)
    
    @patch('shared.logging_config.configure_logging')
    @patch('shared.logging_config.get_logger')
    @patch('shared.health_check.create_standard_health_checker')
    def test_correlation_id_middleware(self, mock_health_checker, mock_get_logger, mock_configure_logging):
        """Test correlation ID middleware."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_health_checker.return_value = MagicMock()
        
        # Create service
        service = WorkerWebService(
            service_name=self.test_service_name,
            worker_function=self.test_worker_function
        )
        
        # Test with correlation ID header
        with service.app.test_client() as client:
            response = client.get('/', headers={'X-Correlation-ID': 'test-123'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get('X-Correlation-ID'), 'test-123')
            
            # Test without correlation ID header (should generate one)
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.headers.get('X-Correlation-ID'))


if __name__ == '__main__':
    unittest.main()