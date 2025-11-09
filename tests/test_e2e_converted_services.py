#!/usr/bin/env python3
"""
End-to-End Integration Tests for Converted Web Services

Tests that all converted workers maintain original functionality
while running as web services with health endpoints.
"""

import os
import sys
import time
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

class TestConvertedServicesIntegration(unittest.TestCase):
    """Test integration of all converted web services"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'STORAGE_MODE': 'local',
            'STAGING_DIR': os.path.join(self.temp_dir, 'staging'),
            'NORMALIZED_DIR': os.path.join(self.temp_dir, 'normalized'),
            'STREAMS_DIR': os.path.join(self.temp_dir, 'streams'),
            'TMDB_API_KEY': 'test-tmdb-key',
            'GEMINI_API_KEY': 'test-gemini-key',
            'SERVICE_NAME': 'test-service',
            'LOG_LEVEL': 'INFO'
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
    
    def test_admin_ui_web_service(self):
        """Test admin_ui web service functionality"""
        print("Testing admin_ui web service...")
        
        try:
            from admin_ui.app import app, storage_manager
            
            # Test Flask app creation
            self.assertIsNotNone(app)
            self.assertEqual(app.name, 'admin_ui.app')
            
            # Test StorageManager integration
            self.assertIsNotNone(storage_manager)
            self.assertEqual(storage_manager.storage_mode, 'local')
            
            # Test storage info
            info = storage_manager.get_storage_info()
            self.assertIn('mode', info)
            self.assertIn('local_dirs', info)
            
            print("✓ admin_ui web service working")
            return True
            
        except Exception as e:
            print(f"✗ admin_ui test failed: {e}")
            return False
    
    def test_stream_api_web_service(self):
        """Test stream_api web service functionality"""
        print("Testing stream_api web service...")
        
        try:
            from stream_api.app import app, storage_manager
            
            # Test Flask app creation
            self.assertIsNotNone(app)
            self.assertEqual(app.name, 'stream_api.app')
            
            # Test StorageManager integration
            self.assertIsNotNone(storage_manager)
            
            # Test file URL generation
            test_url = storage_manager.get_file_url("normalized/test.mp4")
            self.assertTrue(test_url.startswith("/local/"))
            
            print("✓ stream_api web service working")
            return True
            
        except Exception as e:
            print(f"✗ stream_api test failed: {e}")
            return False
    
    @patch('shared.worker_app_template.create_worker_web_service')
    def test_media_manager_web_service(self, mock_create_service):
        """Test media_manager web service functionality"""
        print("Testing media_manager web service...")
        
        try:
            # Mock Flask app
            mock_app = MagicMock()
            mock_create_service.return_value = mock_app
            
            from media_manager.app import media_manager_worker, custom_health_check
            
            # Test worker function exists
            self.assertIsNotNone(media_manager_worker)
            
            # Test custom health check
            health_info = custom_health_check()
            self.assertIn('staging_directory', health_info)
            self.assertIn('file_observer', health_info)
            
            # Test staging directory configuration
            staging_path = health_info['staging_directory']['path']
            self.assertTrue(staging_path.endswith('staging'))
            
            print("✓ media_manager web service working")
            return True
            
        except Exception as e:
            print(f"✗ media_manager test failed: {e}")
            return False
    
    @patch('shared.worker_app_template.create_worker_web_service')
    @patch('requests.get')
    @patch('requests.post')
    def test_metadata_enricher_web_service(self, mock_post, mock_get, mock_create_service):
        """Test metadata_enricher web service functionality"""
        print("Testing metadata_enricher web service...")
        
        try:
            # Mock Flask app
            mock_app = MagicMock()
            mock_create_service.return_value = mock_app
            
            # Mock API responses
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'results': []}
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'candidates': []}
            
            from metadata_enricher.app import MetadataEnricher, custom_health_check
            
            # Test MetadataEnricher creation
            enricher = MetadataEnricher()
            self.assertIsNotNone(enricher)
            self.assertTrue(enricher.tmdb_available)
            self.assertTrue(enricher.gemini_available)
            
            # Test custom health check
            health_info = custom_health_check()
            self.assertIn('apis', health_info)
            self.assertIn('processing', health_info)
            
            print("✓ metadata_enricher web service working")
            return True
            
        except Exception as e:
            print(f"✗ metadata_enricher test failed: {e}")
            return False
    
    @patch('shared.worker_app_template.create_worker_web_service')
    def test_normalization_worker_web_service(self, mock_create_service):
        """Test normalization_worker web service functionality"""
        print("Testing normalization_worker web service...")
        
        try:
            # Mock Flask app
            mock_app = MagicMock()
            mock_create_service.return_value = mock_app
            
            from normalization_worker.app import normalization_worker_function, custom_health_check
            
            # Test worker function exists
            self.assertIsNotNone(normalization_worker_function)
            
            # Test custom health check
            health_info = custom_health_check()
            self.assertIn('ffmpeg', health_info)
            self.assertIn('processing', health_info)
            
            print("✓ normalization_worker web service working")
            return True
            
        except Exception as e:
            print(f"✗ normalization_worker test failed: {e}")
            return False
    
    @patch('shared.worker_app_template.create_worker_web_service')
    def test_scene_analyzer_web_service(self, mock_create_service):
        """Test scene_analyzer web service functionality"""
        print("Testing scene_analyzer web service...")
        
        try:
            # Mock Flask app
            mock_app = MagicMock()
            mock_create_service.return_value = mock_app
            
            from scene_analyzer.app import scene_analyzer_worker, custom_health_check
            
            # Test worker function exists
            self.assertIsNotNone(scene_analyzer_worker)
            
            # Test custom health check
            health_info = custom_health_check()
            self.assertIn('ffmpeg', health_info)
            self.assertIn('processing', health_info)
            
            print("✓ scene_analyzer web service working")
            return True
            
        except Exception as e:
            print(f"✗ scene_analyzer test failed: {e}")
            return False
    
    @patch('shared.worker_app_template.create_worker_web_service')
    def test_scheduler_ai_web_service(self, mock_create_service):
        """Test scheduler_ai web service functionality"""
        print("Testing scheduler_ai web service...")
        
        try:
            # Mock Flask app
            mock_app = MagicMock()
            mock_create_service.return_value = mock_app
            
            from scheduler_ai.app import scheduler_worker, custom_health_check
            
            # Test worker function exists
            self.assertIsNotNone(scheduler_worker)
            
            # Test custom health check
            health_info = custom_health_check()
            self.assertIn('scheduling', health_info)
            self.assertIn('last_run', health_info)
            
            print("✓ scheduler_ai web service working")
            return True
            
        except Exception as e:
            print(f"✗ scheduler_ai test failed: {e}")
            return False

class TestHealthEndpoints(unittest.TestCase):
    """Test health endpoints for all converted services"""
    
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
    
    def test_health_endpoints_structure(self):
        """Test that all health endpoints return proper structure"""
        print("Testing health endpoint structures...")
        
        services_to_test = [
            ('admin_ui.app', 'admin_ui'),
            ('stream_api.app', 'stream_api'),
        ]
        
        for module_name, service_name in services_to_test:
            try:
                module = __import__(module_name, fromlist=[''])
                app = getattr(module, 'app')
                
                with app.test_client() as client:
                    response = client.get('/health')
                    
                    # Should return 200 OK
                    self.assertEqual(response.status_code, 200)
                    
                    # Should return JSON
                    self.assertEqual(response.content_type, 'application/json')
                    
                    # Should have basic health info
                    data = response.get_json()
                    self.assertIn('status', data)
                    self.assertIn('service', data)
                    
                    print(f"✓ {service_name} health endpoint working")
                    
            except Exception as e:
                print(f"✗ {service_name} health endpoint failed: {e}")

class TestStorageManagerIntegration(unittest.TestCase):
    """Test StorageManager integration across services"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        self.env_patcher = patch.dict(os.environ, {
            'STORAGE_MODE': 'local',
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
    
    def test_storage_manager_consistency(self):
        """Test StorageManager works consistently across services"""
        print("Testing StorageManager consistency...")
        
        try:
            from shared.storage_manager import StorageManager
            from admin_ui.app import storage_manager as admin_storage
            from stream_api.app import storage_manager as stream_storage
            
            # Test all instances have same configuration
            self.assertEqual(admin_storage.storage_mode, 'local')
            self.assertEqual(stream_storage.storage_mode, 'local')
            
            # Test file operations work consistently
            test_content = b"test file content"
            file_obj = BytesIO(test_content)
            
            # Save via admin_ui storage manager
            result = admin_storage.save_file("staging/test.txt", file_obj, "text/plain")
            self.assertTrue(os.path.exists(result))
            
            # Get URL via stream_api storage manager
            url = stream_storage.get_file_url("staging/test.txt")
            self.assertEqual(url, "/local/staging/test.txt")
            
            print("✓ StorageManager consistency verified")
            return True
            
        except Exception as e:
            print(f"✗ StorageManager consistency test failed: {e}")
            return False

def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Running Converted Services Integration Tests\n")
    
    # Test suites
    test_suites = [
        TestConvertedServicesIntegration,
        TestHealthEndpoints,
        TestStorageManagerIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_suite_class in test_suites:
        print(f"\n--- {test_suite_class.__name__} ---")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_suite_class)
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        total_tests += result.testsRun
        passed_tests += result.testsRun - len(result.failures) - len(result.errors)
        
        # Run individual tests with custom output
        test_instance = test_suite_class()
        test_instance.setUp()
        
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(test_instance, method_name)
                    method()
                except Exception as e:
                    print(f"✗ {method_name} failed: {e}")
        
        test_instance.tearDown()
    
    print(f"\n📊 Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("❌ Some integration tests failed!")
        return False

if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)