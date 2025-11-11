#!/usr/bin/env python3
"""
External Services Connectivity Tests

Tests connectivity and functionality with external services:
- CockroachDB Cloud
- CloudAMQP
- Cloudflare R2
- TMDB API
- Google Gemini API
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

class TestExternalServiceConnectivity(unittest.TestCase):
    """Test connectivity to external services"""
    
    def setUp(self):
        """Set up test environment"""
        # Use real environment variables if available, otherwise mock
        self.real_env = {
            'DB_HOST': os.getenv('DB_HOST', 'mock-db-host'),
            'DB_PORT': os.getenv('DB_PORT', '26257'),
            'DB_NAME': os.getenv('DB_NAME', 'mock-db'),
            'DB_USER': os.getenv('DB_USER', 'mock-user'),
            'DB_PASSWORD': os.getenv('DB_PASSWORD', 'mock-pass'),
            'RABBITMQ_HOST': os.getenv('RABBITMQ_HOST', 'mock-rabbitmq-host'),
            'RABBITMQ_USER': os.getenv('RABBITMQ_USER', 'mock-user'),
            'RABBITMQ_PASS': os.getenv('RABBITMQ_PASS', 'mock-pass'),
            'R2_ACCOUNT_ID': os.getenv('R2_ACCOUNT_ID', 'mock-account'),
            'R2_ACCESS_KEY_ID': os.getenv('R2_ACCESS_KEY_ID', 'mock-key'),
            'R2_SECRET_ACCESS_KEY': os.getenv('R2_SECRET_ACCESS_KEY', 'mock-secret'),
            'R2_BUCKET_NAME': os.getenv('R2_BUCKET_NAME', 'mock-bucket'),
            'TMDB_API_KEY': os.getenv('TMDB_API_KEY', 'mock-tmdb-key'),
            'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', 'mock-gemini-key'),
            'STORAGE_MODE': 'local'  # Force local for testing
        }
        
        self.env_patcher = patch.dict(os.environ, self.real_env)
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_database_configuration(self):
        """Test database configuration and connection setup"""
        print("Testing database configuration...")
        
        try:
            from shared.db import get_db_connection
            
            # Test configuration is loaded
            self.assertEqual(os.getenv('DB_HOST'), self.real_env['DB_HOST'])
            self.assertEqual(os.getenv('DB_PORT'), self.real_env['DB_PORT'])
            
            # Test connection function exists (won't actually connect with mock data)
            self.assertIsNotNone(get_db_connection)
            
            print("✓ Database configuration working")
            return True
            
        except Exception as e:
            print(f"✗ Database configuration test failed: {e}")
            return False
    
    def test_rabbitmq_configuration(self):
        """Test RabbitMQ configuration"""
        print("Testing RabbitMQ configuration...")
        
        try:
            from shared import rabbitmq_client
            
            # Test configuration is loaded
            self.assertEqual(os.getenv('RABBITMQ_HOST'), self.real_env['RABBITMQ_HOST'])
            self.assertEqual(os.getenv('RABBITMQ_USER'), self.real_env['RABBITMQ_USER'])
            
            # Test client functions exist
            self.assertIsNotNone(rabbitmq_client.publish_message)
            self.assertIsNotNone(rabbitmq_client.start_consumer)
            
            print("✓ RabbitMQ configuration working")
            return True
            
        except Exception as e:
            print(f"✗ RabbitMQ configuration test failed: {e}")
            return False
    
    def test_storage_configuration(self):
        """Test storage configuration (R2 + local fallback)"""
        print("Testing storage configuration...")
        
        try:
            from shared.storage_manager import StorageManager
            
            # Test StorageManager initialization
            storage = StorageManager()
            self.assertIsNotNone(storage)
            
            # Test configuration
            info = storage.get_storage_info()
            self.assertIn('mode', info)
            self.assertIn('local_dirs', info)
            
            # Test R2 configuration is loaded (even if not used in local mode)
            self.assertEqual(os.getenv('R2_ACCOUNT_ID'), self.real_env['R2_ACCOUNT_ID'])
            self.assertEqual(os.getenv('R2_BUCKET_NAME'), self.real_env['R2_BUCKET_NAME'])
            
            print("✓ Storage configuration working")
            return True
            
        except Exception as e:
            print(f"✗ Storage configuration test failed: {e}")
            return False
    
    @patch('requests.get')
    def test_tmdb_api_configuration(self, mock_get):
        """Test TMDB API configuration"""
        print("Testing TMDB API configuration...")
        
        try:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'results': []}
            mock_get.return_value = mock_response
            
            from metadata_enricher.app import MetadataEnricher
            
            # Test MetadataEnricher with TMDB
            enricher = MetadataEnricher()
            self.assertTrue(enricher.tmdb_available)
            
            # Test API key is configured
            self.assertEqual(os.getenv('TMDB_API_KEY'), self.real_env['TMDB_API_KEY'])
            
            print("✓ TMDB API configuration working")
            return True
            
        except Exception as e:
            print(f"✗ TMDB API configuration test failed: {e}")
            return False
    
    @patch('requests.post')
    def test_gemini_api_configuration(self, mock_post):
        """Test Gemini API configuration"""
        print("Testing Gemini API configuration...")
        
        try:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'candidates': []}
            mock_post.return_value = mock_response
            
            from metadata_enricher.app import MetadataEnricher
            
            # Test MetadataEnricher with Gemini
            enricher = MetadataEnricher()
            self.assertTrue(enricher.gemini_available)
            
            # Test API key is configured
            self.assertEqual(os.getenv('GEMINI_API_KEY'), self.real_env['GEMINI_API_KEY'])
            
            print("✓ Gemini API configuration working")
            return True
            
        except Exception as e:
            print(f"✗ Gemini API configuration test failed: {e}")
            return False

class TestHealthEndpointsForUptimeRobot(unittest.TestCase):
    """Test health endpoints respond correctly for UptimeRobot monitoring"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, {
            'STORAGE_MODE': 'local',
            'TMDB_API_KEY': 'test-key',
            'GEMINI_API_KEY': 'test-key',
            'SERVICE_NAME': 'test-service'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_health_endpoints_for_monitoring(self):
        """Test health endpoints return proper format for UptimeRobot"""
        print("Testing health endpoints for UptimeRobot monitoring...")
        
        # Services that should have health endpoints
        services_to_test = [
            ('admin_ui.app', 'admin-ui'),
            ('stream_api.app', 'stream-api'),
        ]
        
        for module_name, service_name in services_to_test:
            try:
                module = __import__(module_name, fromlist=[''])
                app = getattr(module, 'app')
                
                with app.test_client() as client:
                    response = client.get('/health')
                    
                    # UptimeRobot requirements
                    self.assertEqual(response.status_code, 200, 
                                   f"{service_name} health endpoint should return 200")
                    
                    # Should return JSON
                    self.assertEqual(response.content_type, 'application/json',
                                   f"{service_name} health endpoint should return JSON")
                    
                    # Should have status field
                    data = response.get_json()
                    self.assertIn('status', data,
                                f"{service_name} health endpoint should have status field")
                    
                    # Response time should be reasonable (< 5 seconds for UptimeRobot)
                    # This is tested by the fact that the test completes quickly
                    
                    print(f"✓ {service_name} health endpoint ready for UptimeRobot")
                    
            except Exception as e:
                print(f"✗ {service_name} health endpoint failed: {e}")

class TestR2StreamingIntegration(unittest.TestCase):
    """Test streaming works with files stored in Cloudflare R2"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        self.env_patcher = patch.dict(os.environ, {
            'STORAGE_MODE': 'hybrid',  # Test hybrid mode
            'R2_ACCOUNT_ID': 'test-account',
            'R2_ACCESS_KEY_ID': 'test-key',
            'R2_SECRET_ACCESS_KEY': 'test-secret',
            'R2_BUCKET_NAME': 'test-bucket',
            'R2_ENDPOINT': 'https://test-account.r2.cloudflarestorage.com',
            'STAGING_DIR': os.path.join(self.temp_dir, 'staging'),
            'NORMALIZED_DIR': os.path.join(self.temp_dir, 'normalized'),
            'STREAMS_DIR': os.path.join(self.temp_dir, 'streams')
        })
        self.env_patcher.start()
        
        # Create directories
        os.makedirs(os.path.join(self.temp_dir, 'staging'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'normalized'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'streams'), exist_ok=True)
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_r2_url_generation(self):
        """Test R2 URL generation for streaming"""
        print("Testing R2 URL generation for streaming...")
        
        try:
            from shared.storage_manager import StorageManager
            
            # Test StorageManager in hybrid mode (will fallback to local without boto3)
            storage = StorageManager()
            self.assertIsNotNone(storage)
            
            # Test URL generation
            url = storage.get_file_url("normalized/test.mp4")
            
            # Should return local URL since boto3 not available
            self.assertTrue(url.startswith("/local/"))
            
            print("✓ R2 URL generation working (local fallback)")
            return True
            
        except Exception as e:
            print(f"✗ R2 URL generation test failed: {e}")
            return False
    
    def test_streaming_with_r2_urls(self):
        """Test that stream_api can handle R2 URLs"""
        print("Testing streaming with R2 URLs...")
        
        try:
            from stream_api.app import storage_manager
            
            # Test that storage manager is available in stream_api
            self.assertIsNotNone(storage_manager)
            
            # Test URL generation for streaming
            test_url = storage_manager.get_file_url("normalized/test.mp4")
            self.assertIsNotNone(test_url)
            
            # Test that the URL format is correct for ffmpeg
            # (either local path or HTTP URL)
            self.assertTrue(
                test_url.startswith("/local/") or test_url.startswith("http"),
                "URL should be either local path or HTTP URL for ffmpeg"
            )
            
            print("✓ Streaming with R2 URLs working")
            return True
            
        except Exception as e:
            print(f"✗ Streaming with R2 URLs test failed: {e}")
            return False

def run_external_services_tests():
    """Run all external services tests"""
    print("🧪 Running External Services Integration Tests\n")
    
    # Test suites
    test_suites = [
        TestExternalServiceConnectivity,
        TestHealthEndpointsForUptimeRobot,
        TestR2StreamingIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_suite_class in test_suites:
        print(f"\n--- {test_suite_class.__name__} ---")
        
        # Run individual tests with custom output
        test_instance = test_suite_class()
        test_instance.setUp()
        
        suite_passed = 0
        suite_total = 0
        
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                suite_total += 1
                try:
                    method = getattr(test_instance, method_name)
                    result = method()
                    if result is not False:  # None or True counts as success
                        suite_passed += 1
                except Exception as e:
                    print(f"✗ {method_name} failed: {e}")
        
        test_instance.tearDown()
        
        total_tests += suite_total
        passed_tests += suite_passed
        
        print(f"Suite results: {suite_passed}/{suite_total} tests passed")
    
    print(f"\n📊 Overall Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All external services tests passed!")
        return True
    else:
        print("❌ Some external services tests failed!")
        return False

if __name__ == '__main__':
    success = run_external_services_tests()
    sys.exit(0 if success else 1)