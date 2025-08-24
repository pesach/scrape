#!/usr/bin/env python3
"""
Video Processing Pipeline
Downloads videos from YouTube, uploads to Backblaze B2, updates Supabase, and cleans up local files.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

import requests
import yt_dlp
from supabase import create_client, Client


class VideoProcessor:
    """Handles the complete video processing pipeline"""
    
    def __init__(self, verbose: bool = False):
        self.configure_logging(verbose)
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.b2_key_id = self.read_required_env("B2_KEY_ID")
        self.b2_app_key = self.read_required_env("B2_APP_KEY")
        self.b2_bucket_name = self.read_required_env("B2_BUCKET_NAME")
        
        self.supabase_url = self.read_required_env("SUPABASE_URL")
        self.supabase_key = self.read_required_env("SUPABASE_ANON_KEY")
        self.supabase_table = os.getenv("SUPABASE_TABLE", "videos")
        
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # B2 authorization data (will be populated on first use)
        self.b2_auth_data = None
        self.b2_bucket_id = None
        
        # Configure download directory
        self.download_dir = Path(os.getenv("VIDEO_DOWNLOAD_DIR", tempfile.gettempdir())) / "video_downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def configure_logging(self, verbose: bool) -> None:
        """Configure logging settings"""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def read_required_env(self, name: str) -> str:
        """Read required environment variable"""
        value = os.getenv(name)
        if not value:
            raise SystemExit(f"Environment variable {name} is required")
        return value
    
    def download_video(self, url: str, video_id: Optional[str] = None) -> Tuple[Path, Dict]:
        """
        Download video from YouTube
        Returns: (file_path, metadata)
        """
        self.logger.info(f"Downloading video from: {url}")
        
        # Configure yt-dlp options
        output_template = str(self.download_dir / "%(title)s-%(id)s.%(ext)s")
        ydl_opts = {
            'outtmpl': output_template,
            'format': 'best[ext=mp4]/best',  # Prefer mp4 format
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': False,
            'no_color': True,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'referer': 'https://www.youtube.com/',
            'cookiefile': os.getenv('YOUTUBE_COOKIES_FILE'),  # Optional: for age-restricted videos
            'progress_hooks': [self._download_progress_hook],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info
                info = ydl.extract_info(url, download=True)
                
                # Get the downloaded file path
                filename = ydl.prepare_filename(info)
                # Handle cases where extension might be different
                if not os.path.exists(filename):
                    # Try with common video extensions
                    for ext in ['.mp4', '.webm', '.mkv', '.avi']:
                        test_path = filename.rsplit('.', 1)[0] + ext
                        if os.path.exists(test_path):
                            filename = test_path
                            break
                
                file_path = Path(filename)
                
                if not file_path.exists():
                    raise FileNotFoundError(f"Downloaded file not found: {filename}")
                
                # Prepare metadata
                metadata = {
                    'youtube_id': info.get('id', video_id),
                    'title': info.get('title', 'Unknown'),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'file_size': file_path.stat().st_size,
                    'file_name': file_path.name,
                    'download_timestamp': datetime.utcnow().isoformat(),
                }
                
                self.logger.info(f"Video downloaded successfully: {file_path.name}")
                return file_path, metadata
                
        except Exception as e:
            self.logger.error(f"Failed to download video: {e}")
            raise
    
    def _download_progress_hook(self, d):
        """Progress hook for yt-dlp downloads"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            self.logger.debug(f"Downloading: {percent} at {speed}")
        elif d['status'] == 'finished':
            self.logger.info("Download completed, processing...")
    
    def compute_sha1(self, file_path: Path) -> str:
        """Compute SHA1 hash of file"""
        hasher = hashlib.sha1()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def b2_authorize(self) -> None:
        """Authorize with Backblaze B2"""
        if self.b2_auth_data:
            return  # Already authorized
            
        self.logger.info("Authorizing with Backblaze B2...")
        resp = requests.get(
            "https://api.backblazeb2.com/b2api/v3/b2_authorize_account",
            auth=(self.b2_key_id, self.b2_app_key),
            timeout=30,
        )
        if resp.status_code != 200:
            raise SystemExit(f"B2 Authorization failed: {resp.status_code} {resp.text}")
        
        self.b2_auth_data = resp.json()
        self.logger.info(f"B2 Authorized. Account: {self.b2_auth_data['accountId']}")
        
        # Get bucket ID
        self._get_bucket_id()
    
    def _get_bucket_id(self) -> None:
        """Get bucket ID from bucket name"""
        self.logger.info(f"Resolving bucket id for '{self.b2_bucket_name}'...")
        
        resp = requests.post(
            f"{self.b2_auth_data['apiUrl']}/b2api/v3/b2_get_bucket",
            headers={
                "Authorization": self.b2_auth_data['authorizationToken'],
                "Content-Type": "application/json"
            },
            json={
                "accountId": self.b2_auth_data['accountId'],
                "bucketName": self.b2_bucket_name
            },
            timeout=30,
        )
        
        if resp.status_code != 200:
            raise SystemExit(f"Get bucket failed: {resp.status_code} {resp.text}")
        
        bucket_data = resp.json()
        self.b2_bucket_id = bucket_data['bucketId']
        self.logger.info(f"Bucket id: {self.b2_bucket_id}")
    
    def upload_to_backblaze(self, file_path: Path, destination_name: Optional[str] = None) -> str:
        """
        Upload file to Backblaze B2
        Returns: Public URL of uploaded file
        """
        # Ensure we're authorized
        self.b2_authorize()
        
        if not destination_name:
            # Create a unique destination name with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            destination_name = f"videos/{timestamp}_{file_path.name}"
        
        self.logger.info(f"Uploading to B2: {file_path.name} -> {destination_name}")
        
        # Get upload URL
        upload_url_resp = requests.post(
            f"{self.b2_auth_data['apiUrl']}/b2api/v3/b2_get_upload_url",
            headers={
                "Authorization": self.b2_auth_data['authorizationToken'],
                "Content-Type": "application/json"
            },
            json={"bucketId": self.b2_bucket_id},
            timeout=30,
        )
        
        if upload_url_resp.status_code != 200:
            raise SystemExit(f"Get upload URL failed: {upload_url_resp.status_code} {upload_url_resp.text}")
        
        upload_data = upload_url_resp.json()
        
        # Compute SHA1 and upload
        sha1_hex = self.compute_sha1(file_path)
        encoded_name = urllib.parse.quote(destination_name)
        
        with open(file_path, "rb") as fh:
            resp = requests.post(
                upload_data['uploadUrl'],
                headers={
                    "Authorization": upload_data['authorizationToken'],
                    "X-Bz-File-Name": encoded_name,
                    "Content-Type": "video/mp4",  # You might want to detect this dynamically
                    "X-Bz-Content-Sha1": sha1_hex,
                },
                data=fh,
                timeout=600,  # 10 minutes timeout for large files
            )
        
        if resp.status_code != 200:
            raise SystemExit(f"Upload failed: {resp.status_code} {resp.text}")
        
        upload_result = resp.json()
        file_id = upload_result['fileId']
        
        # Construct public URL
        # Format: https://f{server_number}.backblazeb2.com/file/{bucket_name}/{file_name}
        # Or using the download URL from auth data
        download_url = self.b2_auth_data.get('downloadUrl', f"https://f002.backblazeb2.com")
        public_url = f"{download_url}/file/{self.b2_bucket_name}/{destination_name}"
        
        self.logger.info(f"Upload succeeded. File ID: {file_id}")
        self.logger.info(f"Public URL: {public_url}")
        
        return public_url
    
    def update_supabase(self, video_id: str, b2_url: str, metadata: Dict) -> None:
        """Update Supabase with video information and B2 URL"""
        self.logger.info(f"Updating Supabase for video: {video_id}")
        
        # Prepare data for Supabase
        data = {
            'youtube_id': video_id,
            'b2_url': b2_url,
            'title': metadata.get('title'),
            'description': metadata.get('description'),
            'duration': metadata.get('duration'),
            'uploader': metadata.get('uploader'),
            'upload_date': metadata.get('upload_date'),
            'view_count': metadata.get('view_count'),
            'like_count': metadata.get('like_count'),
            'thumbnail': metadata.get('thumbnail'),
            'file_size': metadata.get('file_size'),
            'file_name': metadata.get('file_name'),
            'processed_at': datetime.utcnow().isoformat(),
            'status': 'completed'
        }
        
        try:
            # Try to update existing record first
            result = self.supabase.table(self.supabase_table).update(data).eq('youtube_id', video_id).execute()
            
            # If no rows were updated, insert new record
            if not result.data:
                result = self.supabase.table(self.supabase_table).insert(data).execute()
                self.logger.info(f"Inserted new record in Supabase for video: {video_id}")
            else:
                self.logger.info(f"Updated existing record in Supabase for video: {video_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to update Supabase: {e}")
            raise
    
    def cleanup_local_file(self, file_path: Path) -> None:
        """Delete local video file after successful upload"""
        try:
            if file_path.exists():
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                file_path.unlink()
                self.logger.info(f"Deleted local file: {file_path.name} ({file_size_mb:.2f} MB)")
            else:
                self.logger.warning(f"File already deleted or not found: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to delete local file: {e}")
            # Don't raise - this is not critical
    
    def process_video(self, url: str, video_id: Optional[str] = None, keep_local: bool = False) -> Dict:
        """
        Complete video processing pipeline
        1. Download from YouTube
        2. Upload to Backblaze
        3. Update Supabase
        4. Clean up local file
        """
        self.logger.info(f"Starting video processing pipeline for: {url}")
        
        file_path = None
        try:
            # Step 1: Download video
            file_path, metadata = self.download_video(url, video_id)
            
            # Extract video ID if not provided
            if not video_id:
                video_id = metadata.get('youtube_id')
            
            # Step 2: Upload to Backblaze
            b2_url = self.upload_to_backblaze(file_path)
            
            # Step 3: Update Supabase
            self.update_supabase(video_id, b2_url, metadata)
            
            # Step 4: Clean up local file (unless keep_local is True)
            if not keep_local:
                self.cleanup_local_file(file_path)
            
            self.logger.info(f"Video processing completed successfully for: {video_id}")
            
            return {
                'success': True,
                'video_id': video_id,
                'b2_url': b2_url,
                'metadata': metadata,
                'local_file_kept': keep_local
            }
            
        except Exception as e:
            self.logger.error(f"Video processing failed: {e}")
            
            # Clean up on failure if file exists
            if file_path and file_path.exists() and not keep_local:
                self.cleanup_local_file(file_path)
            
            # Update Supabase with error status if we have video_id
            if video_id:
                try:
                    self.supabase.table(self.supabase_table).update({
                        'youtube_id': video_id,
                        'status': 'failed',
                        'error_message': str(e),
                        'processed_at': datetime.utcnow().isoformat()
                    }).eq('youtube_id', video_id).execute()
                except:
                    pass  # Ignore Supabase update errors during error handling
            
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Video Processing Pipeline - Download from YouTube, upload to Backblaze, update Supabase"
    )
    parser.add_argument("url", help="YouTube video URL to process")
    parser.add_argument("--video-id", help="Optional video ID for tracking")
    parser.add_argument("--keep-local", action="store_true", help="Keep local file after upload")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    try:
        processor = VideoProcessor(verbose=args.verbose)
        result = processor.process_video(
            url=args.url,
            video_id=args.video_id,
            keep_local=args.keep_local
        )
        
        print(f"\n✅ Success! Video processed: {result['video_id']}")
        print(f"📍 B2 URL: {result['b2_url']}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())