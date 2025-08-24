#!/usr/bin/env python3
"""
Video handler module for YouTube downloads, Backblaze uploads, and Supabase database operations
"""

import os
import json
import logging
import hashlib
import tempfile
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
import yt_dlp
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoHandler:
    def __init__(self):
        """Initialize the video handler with necessary credentials"""
        # Backblaze B2 credentials
        self.b2_key_id = os.getenv('B2_KEY_ID')
        self.b2_app_key = os.getenv('B2_APP_KEY')
        self.b2_bucket_name = os.getenv('B2_BUCKET_NAME')
        
        # Supabase credentials
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        # Initialize Supabase client if credentials are available
        self.supabase_client = None
        if self.supabase_url and self.supabase_key:
            self.supabase_client = create_client(self.supabase_url, self.supabase_key)
        
        # YouTube download options
        self.ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    def download_youtube_video(self, youtube_url: str, output_dir: Optional[str] = None) -> Dict:
        """
        Download a video from YouTube
        
        Args:
            youtube_url: The YouTube video URL
            output_dir: Directory to save the video (uses temp dir if not specified)
        
        Returns:
            Dict with download status and file path
        """
        try:
            if not output_dir:
                output_dir = tempfile.mkdtemp()
            
            # Update output template with directory
            ydl_opts = self.ydl_opts.copy()
            ydl_opts['outtmpl'] = os.path.join(output_dir, '%(title)s.%(ext)s')
            
            logger.info(f"Downloading video from: {youtube_url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                video_title = info.get('title', 'video')
                video_ext = info.get('ext', 'mp4')
                
                # Get the actual downloaded file path
                file_path = os.path.join(output_dir, f"{video_title}.{video_ext}")
                
                # Handle special characters in filename
                if not os.path.exists(file_path):
                    # Try to find the file with sanitized name
                    for file in os.listdir(output_dir):
                        if file.endswith(f".{video_ext}"):
                            file_path = os.path.join(output_dir, file)
                            break
                
                logger.info(f"Video downloaded successfully: {file_path}")
                
                return {
                    'success': True,
                    'file_path': file_path,
                    'video_title': video_title,
                    'video_id': info.get('id'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
        
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def compute_sha1(self, file_path: str) -> str:
        """Compute SHA1 hash of a file"""
        hasher = hashlib.sha1()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def b2_authorize(self) -> Dict:
        """Authorize with Backblaze B2"""
        logger.info("Authorizing with Backblaze B2...")
        resp = requests.get(
            "https://api.backblazeb2.com/b2api/v3/b2_authorize_account",
            auth=(self.b2_key_id, self.b2_app_key),
            timeout=30
        )
        if resp.status_code != 200:
            raise Exception(f"Authorization failed: {resp.status_code} {resp.text}")
        return resp.json()
    
    def b2_get_bucket(self, api_url: str, auth_token: str, account_id: str) -> Dict:
        """Get bucket information from Backblaze B2"""
        logger.info(f"Getting bucket info for: {self.b2_bucket_name}")
        resp = requests.post(
            f"{api_url}/b2api/v3/b2_get_bucket",
            headers={"Authorization": auth_token},
            json={"accountId": account_id, "bucketName": self.b2_bucket_name},
            timeout=30
        )
        if resp.status_code != 200:
            raise Exception(f"Get bucket failed: {resp.status_code} {resp.text}")
        return resp.json()
    
    def b2_get_upload_url(self, api_url: str, auth_token: str, bucket_id: str) -> Dict:
        """Get upload URL from Backblaze B2"""
        logger.info("Requesting upload URL...")
        resp = requests.post(
            f"{api_url}/b2api/v3/b2_get_upload_url",
            headers={"Authorization": auth_token},
            json={"bucketId": bucket_id},
            timeout=30
        )
        if resp.status_code != 200:
            raise Exception(f"Get upload URL failed: {resp.status_code} {resp.text}")
        return resp.json()
    
    def upload_to_backblaze(self, file_path: str, remote_name: Optional[str] = None) -> Dict:
        """
        Upload a file to Backblaze B2
        
        Args:
            file_path: Path to the local file
            remote_name: Name for the file in B2 (uses basename if not specified)
        
        Returns:
            Dict with upload status and file URL
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not remote_name:
                remote_name = os.path.basename(file_path)
            
            # Authorize
            auth = self.b2_authorize()
            api_url = auth.get("apiUrl")
            auth_token = auth.get("authorizationToken")
            account_id = auth.get("accountId")
            
            # Get bucket
            bucket_resp = self.b2_get_bucket(api_url, auth_token, account_id)
            bucket_id = bucket_resp.get("buckets", [{}])[0].get("bucketId")
            
            if not bucket_id:
                raise Exception("Failed to get bucket ID")
            
            # Get upload URL
            upload_resp = self.b2_get_upload_url(api_url, auth_token, bucket_id)
            upload_url = upload_resp.get("uploadUrl")
            upload_auth_token = upload_resp.get("authorizationToken")
            
            if not upload_url or not upload_auth_token:
                raise Exception("Failed to get upload URL")
            
            # Compute SHA1
            sha1 = self.compute_sha1(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.info(f"Uploading {file_path} ({file_size} bytes) as {remote_name}")
            
            # Upload file
            with open(file_path, 'rb') as f:
                resp = requests.post(
                    upload_url,
                    headers={
                        "Authorization": upload_auth_token,
                        "X-Bz-File-Name": remote_name,
                        "Content-Type": "b2/x-auto",
                        "X-Bz-Content-Sha1": sha1,
                        "Content-Length": str(file_size)
                    },
                    data=f,
                    timeout=300
                )
            
            if resp.status_code != 200:
                raise Exception(f"Upload failed: {resp.status_code} {resp.text}")
            
            result = resp.json()
            file_id = result.get("fileId")
            
            # Construct the public URL
            # Format: https://f{bucket_id_prefix}.backblazeb2.com/file/{bucket_name}/{file_name}
            bucket_name = self.b2_bucket_name
            file_url = f"https://f{bucket_id[:3]}.backblazeb2.com/file/{bucket_name}/{remote_name}"
            
            logger.info(f"File uploaded successfully. File ID: {file_id}")
            
            return {
                'success': True,
                'file_id': file_id,
                'file_name': remote_name,
                'file_url': file_url,
                'file_size': file_size,
                'sha1': sha1
            }
        
        except Exception as e:
            logger.error(f"Error uploading to Backblaze: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_supabase_video_url(self, video_id: str, backblaze_url: str, table_name: str = 'videos') -> Dict:
        """
        Update the video URL in Supabase database
        
        Args:
            video_id: The video ID in the database
            backblaze_url: The new Backblaze URL
            table_name: The Supabase table name (default: 'videos')
        
        Returns:
            Dict with update status
        """
        try:
            if not self.supabase_client:
                raise Exception("Supabase client not initialized. Check your environment variables.")
            
            logger.info(f"Updating video {video_id} with URL: {backblaze_url}")
            
            # Update the video record
            response = self.supabase_client.table(table_name).update({
                'url': backblaze_url,
                'updated_at': 'now()'
            }).eq('id', video_id).execute()
            
            if response.data:
                logger.info(f"Successfully updated video {video_id} in Supabase")
                return {
                    'success': True,
                    'data': response.data
                }
            else:
                raise Exception("No data returned from update operation")
        
        except Exception as e:
            logger.error(f"Error updating Supabase: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_video_reupload(self, youtube_url: str, video_id: str, table_name: str = 'videos') -> Dict:
        """
        Complete process: Download from YouTube, upload to Backblaze, update Supabase
        
        Args:
            youtube_url: The YouTube video URL
            video_id: The video ID in the database
            table_name: The Supabase table name (default: 'videos')
        
        Returns:
            Dict with complete process status
        """
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            
            # Step 1: Download from YouTube
            logger.info("Step 1: Downloading video from YouTube...")
            download_result = self.download_youtube_video(youtube_url, temp_dir)
            
            if not download_result['success']:
                return download_result
            
            file_path = download_result['file_path']
            
            # Step 2: Upload to Backblaze
            logger.info("Step 2: Uploading video to Backblaze...")
            upload_result = self.upload_to_backblaze(file_path)
            
            if not upload_result['success']:
                return upload_result
            
            backblaze_url = upload_result['file_url']
            
            # Step 3: Update Supabase
            logger.info("Step 3: Updating Supabase database...")
            update_result = self.update_supabase_video_url(video_id, backblaze_url, table_name)
            
            if not update_result['success']:
                return update_result
            
            # Clean up downloaded file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return {
                'success': True,
                'youtube_download': download_result,
                'backblaze_upload': upload_result,
                'supabase_update': update_result,
                'final_url': backblaze_url
            }
        
        except Exception as e:
            logger.error(f"Error in video reupload process: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)