"""
Tests for health check functionality
"""
import json
import time
from unittest.mock import patch, MagicMock, Mock

import pytest
from flask import Flask

from shared.health_check import HealthChecker, create_standard_health_checker, check_database_connection, check_rabbitmq_connection


class TestHealthChecker:
    """Test health check functionality"""
    
    def test_health_checker_initialization(self):
        """Test HealthChecker initialization"""
        checker = HealthChecker("test-service")
        
        assert checker.service_name == "test-service"
        assert checker.dependencies == {}
    
    def test_add_dependency(self):
        """Test adding health check dependencies"""
        checker = HealthChecker("test-service")
        
        def dummy_check():
            return True
        
        checker.add_dependency("test", dummy_check)
        
        assert "test" in checker.dependencies
        assert checker.dependencies["test"]["check_func"] == dummy_check
    
    def test_check_health_all_healthy(self):
        """Test running checks when all are healthy"""
        checker = HealthChecker("test-service")
        
        def check1():
            return True
        
        def check2():
            return True
        
        checker.add_dependency("service1", check1)
        checker.add_dependency("service2", check2)
        
        result = checker.check_health()
        
        assert result["status"] == "healthy"
        assert result["checks"]["service1"]["status"] == "healthy"
        assert result["checks"]["service2"]["status"] == "healthy"
        assert "timestamp" in result
        assert "uptime_seconds" in result
    
    def test_check_health_some_unhealthy(self):
        """Test running checks when some are unhealthy"""
        checker = HealthChecker("test-service")
        
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        checker.add_dependency("healthy", healthy_check)
        checker.add_dependency("unhealthy", unhealthy_check)
        
        result = checker.check_health()
        
        assert result["status"] == "unhealthy"
        assert result["checks"]["healthy"]["status"] == "healthy"
        assert result["checks"]["unhealthy"]["status"] == "unhealthy"
    
    def test_check_health_with_exception(self):
        """Test running checks when one raises an exception"""
        checker = HealthChecker("test-service")
        
        def healthy_check():
            return True
        
        def failing_check():
            raise Exception("Connection failed")
        
        checker.add_dependency("healthy", healthy_check)
        checker.add_dependency("failing", failing_check)
        
        result = checker.check_health()
        
        assert result["status"] == "unhealthy"
        assert result["checks"]["healthy"]["status"] == "healthy"
        assert result["checks"]["failing"]["status"] == "unhealthy"
        assert "Connection failed" in result["checks"]["failing"]["error"]


class TestHealthCheckEndpoint:
    """Test Flask health check endpoint integration"""
    
    def test_create_flask_endpoint(self):
        """Test creating Flask health check endpoint"""
        app = Flask(__name__)
        checker = HealthChecker("test-service")
        
        def dummy_check():
            return True
        
        checker.add_dependency("test", dummy_check)
        checker.create_flask_endpoint(app)
        
        with app.test_client() as client:
            response = client.get('/health')
            
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data["status"] == "healthy"
            assert "test" in data["checks"]
    
    def test_flask_endpoint_unhealthy_status_code(self):
        """Test that unhealthy checks return 503 status"""
        app = Flask(__name__)
        checker = HealthChecker("test-service")
        
        def unhealthy_check():
            return False
        
        checker.add_dependency("test", unhealthy_check)
        checker.create_flask_endpoint(app)
        
        with app.test_client() as client:
            response = client.get('/health')
            
            assert response.status_code == 503
            
            data = json.loads(response.data)
            assert data["status"] == "unhealthy"


class TestStandardHealthChecker:
    """Test standard health checker creation"""
    
    def test_create_standard_health_checker(self):
        """Test creating standard health checker"""
        checker = create_standard_health_checker("test-service")
        
        assert checker.service_name == "test-service"
        assert "database" in checker.dependencies
        assert "rabbitmq" in checker.dependencies
        assert "disk_space" in checker.dependencies
    
    def test_create_standard_health_checker_no_db(self):
        """Test creating standard health checker without database"""
        checker = create_standard_health_checker("test-service", include_db=False)
        
        assert "database" not in checker.dependencies
        assert "rabbitmq" in checker.dependencies
        assert "disk_space" in checker.dependencies
    
    def test_create_standard_health_checker_no_rabbitmq(self):
        """Test creating standard health checker without RabbitMQ"""
        checker = create_standard_health_checker("test-service", include_rabbitmq=False)
        
        assert "database" in checker.dependencies
        assert "rabbitmq" not in checker.dependencies
        assert "disk_space" in checker.dependencies


class TestHealthCheckFunctions:
    """Test individual health check functions"""
    
    @patch('shared.health_check.psycopg2.connect')
    @patch('shared.config.Config.get_db_config')
    def test_database_connection_check_success(self, mock_config, mock_connect):
        """Test database connection check when successful"""
        # Mock config
        mock_config.return_value = {
            'host': 'localhost',
            'port': 5432,
            'dbname': 'test',
            'user': 'test',
            'password': 'test',
            'connect_timeout': 5
        }
        
        # Mock successful connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)
        mock_connect.return_value = mock_conn
        
        result = check_database_connection()
        
        assert result is True
        mock_connect.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('shared.health_check.psycopg2.connect')
    @patch('shared.config.Config.get_db_config')
    def test_database_connection_check_failure(self, mock_config, mock_connect):
        """Test database connection check when it fails"""
        # Mock config
        mock_config.return_value = {
            'host': 'localhost',
            'port': 5432,
            'dbname': 'test',
            'user': 'test',
            'password': 'test',
            'connect_timeout': 5
        }
        
        # Mock connection failure
        mock_connect.side_effect = Exception("Connection refused")
        
        result = check_database_connection()
        
        assert result is False
    
    @patch('shared.health_check.pika.BlockingConnection')
    @patch('shared.config.Config.get_rabbitmq_config')
    def test_rabbitmq_connection_check_success(self, mock_config, mock_connection):
        """Test RabbitMQ connection check when successful"""
        # Mock config
        mock_config.return_value = {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'virtual_host': '/',
            'connection_timeout': 5,
            'heartbeat': 600
        }
        
        # Mock successful connection
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_connection.return_value = mock_conn
        
        result = check_rabbitmq_connection()
        
        assert result is True
        mock_connection.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('shared.health_check.pika.BlockingConnection')
    @patch('shared.config.Config.get_rabbitmq_config')
    def test_rabbitmq_connection_check_failure(self, mock_config, mock_connection):
        """Test RabbitMQ connection check when it fails"""
        # Mock config
        mock_config.return_value = {
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'virtual_host': '/',
            'connection_timeout': 5,
            'heartbeat': 600
        }
        
        # Mock connection failure
        mock_connection.side_effect = Exception("Connection refused")
        
        result = check_rabbitmq_connection()
        
        assert result is False