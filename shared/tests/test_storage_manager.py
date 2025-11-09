#!/usr/bin/env python3
"""
Tests for StorageManager integration
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from shared.storage_manager import StorageManager

class TestStorageManager(unittest.TestCase):
    """Test StorageManager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables for local mode
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
    
    def test_local_storage_mode(self):
        """Test StorageManager in local mode"""
        storage = StorageManager()
        
        # Test file save
        test_content = b"test file content"
        file_obj = BytesIO(test_content)
        
        result = storage.save_file("staging/test.txt", file_obj)
        
        # Should return local path
        self.assertTrue(result.endswith("test.txt"))
        self.assertTrue(os.path.exists(result))
        
        # Verify content
        with open(result, 'rb') as f:
            self.assertEqual(f.read(), test_content)
    
    def test_get_file_url_local(self):
        """Test get_file_url in local mode"""
        storage = StorageManager()
        
        url = storage.get_file_url("staging/test.txt")
        self.assertEqual(url, "/local/staging/test.txt")
    
    def test_storage_info(self):
        """Test get_storage_info"""
        storage = StorageManager()
        
        info = storage.get_storage_info()
        
        self.assertEqual(info['mode'], 'local')
        self.assertFalse(info['r2_available'])
        self.assertIn('local_dirs', info)
    
    @patch('shared.storage_manager.boto3')
    def test_r2_mode_initialization(self, mock_boto3):
        """Test R2 mode initialization"""
        # Mock R2 environment variables
        with patch.dict(os.environ, {
            'STORAGE_MODE': 'r2',
            'R2_ACCOUNT_ID': 'test-account',
            'R2_ACCESS_KEY_ID': 'test-key',
            'R2_SECRET_ACCESS_KEY': 'test-secret',
            'R2_BUCKET_NAME': 'test-bucket'
        }):
            # Mock successful R2 client
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            
            storage = StorageManager()
            
            # Should initialize R2 client
            mock_boto3.client.assert_called_once()
            self.assertEqual(storage.storage_mode, 'r2')
            self.assertIsNotNone(storage.r2_client)
    
    @patch('shared.storage_manager.boto3')
    def test_hybrid_mode_fallback(self, mock_boto3):
        """Test hybrid mode with R2 failure fallback"""
        # Mock R2 environment variables
        with patch.dict(os.environ, {
            'STORAGE_MODE': 'hybrid',
            'R2_ACCOUNT_ID': 'test-account',
            'R2_ACCESS_KEY_ID': 'test-key',
            'R2_SECRET_ACCESS_KEY': 'test-secret',
            'R2_BUCKET_NAME': 'test-bucket'
        }):
            # Mock R2 client that fails on save
            mock_client = MagicMock()
            mock_client.upload_fileobj.side_effect = Exception("R2 error")
            mock_boto3.client.return_value = mock_client
            
            storage = StorageManager()
            
            # Test file save with fallback
            test_content = b"test file content"
            file_obj = BytesIO(test_content)
            
            result = storage.save_file("staging/test.txt", file_obj)
            
            # Should fallback to local storage
            self.assertTrue(result.endswith("test.txt"))
            self.assertTrue(os.path.exists(result))

if __name__ == '__main__':
    unittest.main()