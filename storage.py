import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Tuple
import logging
from pathlib import Path
import mimetypes
from datetime import datetime

logger = logging.getLogger(__name__)

class BackblazeB2Storage:
    """Backblaze B2 storage client using S3-compatible API"""
    
    def __init__(self):
        self.key_id = os.getenv("B2_APPLICATION_KEY_ID")
        self.application_key = os.getenv("B2_APPLICATION_KEY")
        self.bucket_name = os.getenv("B2_BUCKET_NAME")
        self.endpoint_url = os.getenv("B2_ENDPOINT_URL")
        
        if not all([self.key_id, self.application_key, self.bucket_name, self.endpoint_url]):
            raise ValueError("Missing Backblaze B2 configuration. Please set B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME, and B2_ENDPOINT_URL")
        
        # Create S3 client configured for Backblaze B2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.key_id,
            aws_secret_access_key=self.application_key,
            config=Config(
                region_name='us-west-004',  # Backblaze B2 region
                signature_version='s3v4',
                s3={
                    'addressing_style': 'path'
                }
            )
        )
    
    def upload_file(self, local_file_path: str, remote_key: str, content_type: str = None) -> Tuple[bool, str]:
        """
        Upload a file to Backblaze B2
        
        Args:
            local_file_path: Path to local file
            remote_key: Key/path in B2 bucket
            content_type: MIME type of the file
            
        Returns:
            Tuple of (success: bool, url_or_error: str)
        """
        try:
            # Auto-detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(local_file_path)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Get file size for progress tracking
            file_size = os.path.getsize(local_file_path)
            logger.info(f"Uploading {local_file_path} ({file_size} bytes) to B2 as {remote_key}")
            
            # Upload file with metadata
            extra_args = {
                'ContentType': content_type,
                                 'Metadata': {
                     'original-filename': os.path.basename(local_file_path),
                     'upload-timestamp': str(int(datetime.now().timestamp()))
                 }
            }
            
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                remote_key,
                ExtraArgs=extra_args
            )
            
            # Generate public URL
            public_url = f"{self.endpoint_url.replace('s3.', 'f004.')}/{self.bucket_name}/{remote_key}"
            
            logger.info(f"Successfully uploaded {remote_key} to B2")
            return True, public_url
            
        except FileNotFoundError:
            error_msg = f"Local file not found: {local_file_path}"
            logger.error(error_msg)
            return False, error_msg
            
        except NoCredentialsError:
            error_msg = "Backblaze B2 credentials not found or invalid"
            logger.error(error_msg)
            return False, error_msg
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = f"B2 upload failed ({error_code}): {e.response['Error']['Message']}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during B2 upload: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def delete_file(self, remote_key: str) -> Tuple[bool, str]:
        """
        Delete a file from Backblaze B2
        
        Args:
            remote_key: Key/path in B2 bucket
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=remote_key)
            logger.info(f"Successfully deleted {remote_key} from B2")
            return True, f"Successfully deleted {remote_key}"
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = f"B2 delete failed ({error_code}): {e.response['Error']['Message']}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error during B2 delete: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def file_exists(self, remote_key: str) -> bool:
        """
        Check if a file exists in Backblaze B2
        
        Args:
            remote_key: Key/path in B2 bucket
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=remote_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            # Re-raise other errors
            raise
        except Exception:
            return False
    
    def get_file_info(self, remote_key: str) -> Optional[dict]:
        """
        Get information about a file in B2
        
        Args:
            remote_key: Key/path in B2 bucket
            
        Returns:
            Dictionary with file info or None if not found
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=remote_key)
            return {
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise
        except Exception:
            return None
    
    def generate_presigned_url(self, remote_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for downloading a file
        
        Args:
            remote_key: Key/path in B2 bucket
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': remote_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {remote_key}: {str(e)}")
            return None
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        List files in the B2 bucket
        
        Args:
            prefix: Filter files by prefix
            max_keys: Maximum number of keys to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            return []

def generate_video_key(video_id: str, title: str, extension: str = "mp4") -> str:
    """
    Generate a unique key for storing a video in B2
    
    Args:
        video_id: YouTube video ID
        title: Video title
        extension: File extension
        
    Returns:
        B2 object key
    """
    # Sanitize title for use in filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
    
    # Create hierarchical structure: videos/YYYY/MM/video_id_title.ext
    from datetime import datetime
    now = datetime.now()
    
    return f"videos/{now.year:04d}/{now.month:02d}/{video_id}_{safe_title}.{extension}"

# Global storage instance
storage = BackblazeB2Storage()