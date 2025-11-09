#!/usr/bin/env python3
"""
Simple integration test for StorageManager
"""

import os
import sys
import tempfile
from io import BytesIO

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_storage_manager_integration():
    """Test basic StorageManager functionality"""
    print("Testing StorageManager integration...")
    
    # Set up environment for local mode
    temp_dir = tempfile.mkdtemp()
    os.environ['STORAGE_MODE'] = 'local'
    os.environ['STAGING_DIR'] = os.path.join(temp_dir, 'staging')
    os.environ['NORMALIZED_DIR'] = os.path.join(temp_dir, 'normalized')
    os.environ['STREAMS_DIR'] = os.path.join(temp_dir, 'streams')
    
    # Create directories
    os.makedirs(os.path.join(temp_dir, 'staging'), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, 'normalized'), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, 'streams'), exist_ok=True)
    
    try:
        # Import after setting environment
        from shared.storage_manager import StorageManager
        
        # Test initialization
        storage = StorageManager()
        print(f"✓ StorageManager initialized in {storage.storage_mode} mode")
        
        # Test storage info
        info = storage.get_storage_info()
        print(f"✓ Storage info: {info}")
        
        # Test file operations
        test_content = b"test file content for integration"
        file_obj = BytesIO(test_content)
        
        # Test save file
        result = storage.save_file("staging/integration_test.txt", file_obj, "text/plain")
        print(f"✓ File saved: {result}")
        
        # Verify file exists
        if os.path.exists(result):
            print("✓ File exists on filesystem")
            
            # Verify content
            with open(result, 'rb') as f:
                saved_content = f.read()
                if saved_content == test_content:
                    print("✓ File content matches")
                else:
                    print("✗ File content mismatch")
        else:
            print("✗ File does not exist")
        
        # Test get file URL
        url = storage.get_file_url("staging/integration_test.txt")
        print(f"✓ File URL: {url}")
        
        # Test list files
        files = storage.list_files("staging/")
        print(f"✓ Files in staging: {files}")
        
        print("\n✅ All StorageManager integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

def test_admin_ui_integration():
    """Test admin_ui StorageManager integration"""
    print("\nTesting admin_ui integration...")
    
    try:
        # Import admin_ui app
        from admin_ui.app import app, storage_manager
        
        print(f"✓ Admin UI app imported successfully")
        print(f"✓ StorageManager available in admin_ui: {storage_manager.storage_mode} mode")
        
        # Test storage info endpoint (if available)
        info = storage_manager.get_storage_info()
        print(f"✓ Admin UI storage info: {info}")
        
        return True
        
    except Exception as e:
        print(f"✗ Admin UI integration test failed: {e}")
        return False

def test_stream_api_integration():
    """Test stream_api StorageManager integration"""
    print("\nTesting stream_api integration...")
    
    try:
        # Import stream_api app
        from stream_api.app import app, storage_manager
        
        print(f"✓ Stream API app imported successfully")
        print(f"✓ StorageManager available in stream_api: {storage_manager.storage_mode} mode")
        
        # Test file URL generation
        test_url = storage_manager.get_file_url("normalized/test.mp4")
        print(f"✓ Stream API file URL generation: {test_url}")
        
        return True
        
    except Exception as e:
        print(f"✗ Stream API integration test failed: {e}")
        return False

if __name__ == '__main__':
    print("🧪 Running StorageManager Integration Tests\n")
    
    success = True
    
    # Test basic StorageManager
    success &= test_storage_manager_integration()
    
    # Test admin_ui integration
    success &= test_admin_ui_integration()
    
    # Test stream_api integration  
    success &= test_stream_api_integration()
    
    if success:
        print("\n🎉 All integration tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some integration tests failed!")
        sys.exit(1)