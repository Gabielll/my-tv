import os
import shutil
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
from shared.logging_config import get_logger
from shared.config import Config

# Import boto3 only when needed for R2 functionality
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None

logger = get_logger("storage_manager")

class StorageManager:
    """
    Hybrid storage manager supporting local filesystem and Cloudflare R2.
    Automatically falls back to local storage if R2 is not available.
    """
    
    def __init__(self):
        self.config = Config.get_media_config()
        self.storage_mode = os.getenv('STORAGE_MODE', 'local')  # 'local', 'r2', 'hybrid'
        self.r2_client = None
        self.bucket_name = os.getenv('R2_BUCKET_NAME')
        
        if self.storage_mode in ['r2', 'hybrid']:
            self._init_r2_client()
    
    def _init_r2_client(self):
        """Initialize Cloudflare R2 client if credentials are available"""
        try:
            # Check if boto3 is available
            if not BOTO3_AVAILABLE:
                logger.warning("boto3 not available, falling back to local storage")
                self.storage_mode = 'local'
                return
            
            account_id = os.getenv('R2_ACCOUNT_ID')
            access_key = os.getenv('R2_ACCESS_KEY_ID')
            secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
            
            if not all([account_id, access_key, secret_key, self.bucket_name]):
                logger.warning("R2 credentials incomplete, falling back to local storage")
                self.storage_mode = 'local'
                return
            
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
            
            self.r2_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='auto'
            )
            
            # Test connection
            self.r2_client.head_bucket(Bucket=self.bucket_name)
            logger.info("R2 client initialized successfully", context={
                'bucket': self.bucket_name,
                'mode': self.storage_mode
            })
            
        except Exception as e:
            logger.error("Failed to initialize R2 client", error=e)
            if self.storage_mode == 'r2':
                raise
            else:
                logger.info("Falling back to local storage")
                self.storage_mode = 'local'
                self.r2_client = None
    
    def save_file(self, relative_path: str, file_obj: BinaryIO, content_type: str = None) -> str:
        """
        Save file to storage (R2 or local based on configuration)
        
        Args:
            relative_path: Path relative to media root (e.g., 'staging/video.mp4')
            file_obj: File object to save
            content_type: MIME type of the file
            
        Returns:
            URL or path to access the saved file
        """
        if self.storage_mode == 'r2' and self.r2_client:
            return self._save_to_r2(relative_path, file_obj, content_type)
        elif self.storage_mode == 'hybrid' and self.r2_client:
            try:
                return self._save_to_r2(relative_path, file_obj, content_type)
            except Exception as e:
                logger.warning("R2 save failed, falling back to local", error=e)
                return self._save_locally(relative_path, file_obj)
        else:
            return self._save_locally(relative_path, file_obj)
    
    def _save_to_r2(self, relative_path: str, file_obj: BinaryIO, content_type: str = None) -> str:
        """Save file to Cloudflare R2"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.r2_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                relative_path,
                ExtraArgs=extra_args
            )
            
            # Return R2 URL
            account_id = os.getenv('R2_ACCOUNT_ID')
            url = f"https://{self.bucket_name}.{account_id}.r2.cloudflarestorage.com/{relative_path}"
            
            logger.info("File saved to R2", context={
                'path': relative_path,
                'url': url
            })
            
            return url
            
        except Exception as e:
            logger.error("Failed to save file to R2", error=e, context={'path': relative_path})
            raise
    
    def _save_locally(self, relative_path: str, file_obj: BinaryIO) -> str:
        """Save file to local filesystem"""
        # Determine base directory based on path
        if relative_path.startswith('staging'):
            base_dir = self.config['staging_dir']
            local_path = os.path.join(base_dir, os.path.basename(relative_path))
        elif relative_path.startswith('normalized'):
            base_dir = self.config['normalized_dir']
            local_path = os.path.join(base_dir, os.path.basename(relative_path))
        elif relative_path.startswith('streams'):
            base_dir = self.config['streams_dir']
            local_path = os.path.join(base_dir, relative_path.replace('streams/', ''))
        else:
            # Default to staging
            base_dir = self.config['staging_dir']
            local_path = os.path.join(base_dir, relative_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Save file
        with open(local_path, 'wb') as f:
            shutil.copyfileobj(file_obj, f)
        
        logger.info("File saved locally", context={
            'path': relative_path,
            'local_path': local_path
        })
        
        return local_path
    
    def get_file_url(self, relative_path: str) -> str:
        """
        Get URL to access a file
        
        Args:
            relative_path: Path relative to media root
            
        Returns:
            URL to access the file
        """
        if self.storage_mode in ['r2', 'hybrid'] and self._exists_in_r2(relative_path):
            account_id = os.getenv('R2_ACCOUNT_ID')
            return f"https://{self.bucket_name}.{account_id}.r2.cloudflarestorage.com/{relative_path}"
        else:
            return f"/local/{relative_path}"
    
    def _exists_in_r2(self, relative_path: str) -> bool:
        """Check if file exists in R2"""
        if not self.r2_client:
            return False
        
        try:
            self.r2_client.head_object(Bucket=self.bucket_name, Key=relative_path)
            return True
        except:
            return False
    
    def delete_file(self, relative_path: str) -> bool:
        """
        Delete file from storage
        
        Args:
            relative_path: Path relative to media root
            
        Returns:
            True if deleted successfully
        """
        success = False
        
        # Try to delete from R2 if available
        if self.r2_client and self._exists_in_r2(relative_path):
            try:
                self.r2_client.delete_object(Bucket=self.bucket_name, Key=relative_path)
                logger.info("File deleted from R2", context={'path': relative_path})
                success = True
            except Exception as e:
                logger.error("Failed to delete file from R2", error=e, context={'path': relative_path})
        
        # Also try to delete locally
        local_path = self._get_local_path(relative_path)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info("File deleted locally", context={'path': local_path})
                success = True
            except Exception as e:
                logger.error("Failed to delete local file", error=e, context={'path': local_path})
        
        return success
    
    def _get_local_path(self, relative_path: str) -> str:
        """Convert relative path to local filesystem path"""
        if relative_path.startswith('staging'):
            return os.path.join(self.config['staging_dir'], os.path.basename(relative_path))
        elif relative_path.startswith('normalized'):
            return os.path.join(self.config['normalized_dir'], os.path.basename(relative_path))
        elif relative_path.startswith('streams'):
            return os.path.join(self.config['streams_dir'], relative_path.replace('streams/', ''))
        else:
            return os.path.join(self.config['staging_dir'], relative_path)
    
    def list_files(self, prefix: str = '') -> list:
        """
        List files in storage
        
        Args:
            prefix: Path prefix to filter files
            
        Returns:
            List of file paths
        """
        files = []
        
        # List from R2 if available
        if self.r2_client:
            try:
                response = self.r2_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                )
                if 'Contents' in response:
                    files.extend([obj['Key'] for obj in response['Contents']])
            except Exception as e:
                logger.error("Failed to list R2 files", error=e)
        
        # Also list local files
        local_dirs = [
            self.config['staging_dir'],
            self.config['normalized_dir'],
            self.config['streams_dir']
        ]
        
        for local_dir in local_dirs:
            if os.path.exists(local_dir):
                for root, dirs, filenames in os.walk(local_dir):
                    for filename in filenames:
                        rel_path = os.path.relpath(os.path.join(root, filename), local_dir)
                        if not prefix or rel_path.startswith(prefix):
                            files.append(rel_path)
        
        return list(set(files))  # Remove duplicates
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about current storage configuration"""
        return {
            'mode': self.storage_mode,
            'r2_available': self.r2_client is not None,
            'bucket_name': self.bucket_name,
            'local_dirs': {
                'staging': self.config['staging_dir'],
                'normalized': self.config['normalized_dir'],
                'streams': self.config['streams_dir']
            }
        }