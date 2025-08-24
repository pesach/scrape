import os
import yt_dlp
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, date
from models import URLType, VideoCreate
from storage import storage, generate_video_key
from database import db
import uuid
import asyncio
import random

logger = logging.getLogger(__name__)

class VideoScraper:
    """
    YouTube video scraper using yt-dlp or ScraperAPI
    
    IMPORTANT DESIGN DECISIONS:
    
    1. METADATA SOURCE: Uses yt-dlp scraping OR ScraperAPI (NOT YouTube API)
       - yt-dlp: No API keys needed, downloads videos, more complete metadata
       - ScraperAPI: Handles CAPTCHAs, proxy rotation, metadata only (no download)
       - Method: Direct web scraping like a browser
       - Handles: Private/unlisted videos if accessible
    
    2. STORAGE STRATEGY: Temporary local → Permanent cloud
       - Downloads to temp directory first (yt-dlp only)
       - Uploads to Backblaze B2 cloud storage
       - Immediately deletes local file after upload
       - Result: Near-zero local disk usage
    
    3. PROCESSING FLOW:
       - Single videos: High priority queue (faster)
       - Playlists/channels: Normal priority queue
       - Rate limiting: 1 second delay between videos
       - Error handling: Continues processing other videos if one fails
    """
    
    def __init__(self):
        from config import config
        
        self.download_path = config.DOWNLOAD_PATH
        self.max_file_size_gb = config.MAX_FILE_SIZE_GB
        self.config = config
        
        # Create download directory if it doesn't exist
        Path(self.download_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize ScraperAPI client if enabled
        self.scraperapi_client = None
        if self.config.USE_SCRAPERAPI and self.config.SCRAPERAPI_KEY:
            from scraperapi_client import ScraperAPIClient
            self.scraperapi_client = ScraperAPIClient(
                api_key=self.config.SCRAPERAPI_KEY,
                endpoint=self.config.SCRAPERAPI_ENDPOINT,
                render=self.config.SCRAPERAPI_RENDER,
                premium=self.config.SCRAPERAPI_PREMIUM,
                retry_failed=self.config.SCRAPERAPI_RETRY_FAILED,
                timeout=self.config.SCRAPERAPI_TIMEOUT
            )
            logger.info("ScraperAPI client initialized for YouTube scraping")
    
    def _build_common_ydl_opts(self) -> Dict[str, Any]:
        """Build common yt-dlp options for headers, cookies, and politeness."""
        opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'http_headers': {
                'User-Agent': self.config.SCRAPER_USER_AGENT,
                'Accept-Language': self.config.SCRAPER_ACCEPT_LANGUAGE,
                'Referer': 'https://www.youtube.com/',
            },
        }
        # Cookies
        if self.config.YT_COOKIES_FILE:
            # Log which cookies file is being used and whether it exists
            try:
                cookies_path = Path(self.config.YT_COOKIES_FILE)
                if cookies_path.exists():
                    logger.info("Using cookies file: %s", cookies_path)
                else:
                    logger.warning("Cookies file set but not found: %s", cookies_path)
            except Exception:
                pass
            opts['cookiefile'] = self.config.YT_COOKIES_FILE
        elif self.config.COOKIES_FROM_BROWSER:
            # e.g., ('chrome',) or ('firefox',)
            browser = self.config.COOKIES_FROM_BROWSER.strip().lower()
            logger.info("Using cookies from browser: %s", browser)
            opts['cookiesfrombrowser'] = (browser, )
        
        # Request pacing inside yt-dlp
        opts['sleep_interval_requests'] = self.config.HUMAN_DELAY_MIN_SEC
        opts['max_sleep_interval_requests'] = self.config.HUMAN_DELAY_MAX_SEC
        return opts
    
    def _compute_watchlike_ratelimit(self, info: Dict[str, Any]) -> Optional[int]:
        """
        Compute bytes/sec to approximate playback rate.
        Priorities:
          1) Config DOWNLOAD_RATELIMIT_BPS if set
          2) filesize/duration adjusted by WATCH_SPEED
          3) Heuristic by resolution
        """
        if self.config.DOWNLOAD_RATELIMIT_BPS and self.config.DOWNLOAD_RATELIMIT_BPS > 0:
            return int(self.config.DOWNLOAD_RATELIMIT_BPS)
        
        if not self.config.SIMULATE_WATCH_TIME:
            return None
        
        try:
            duration = info.get('duration') or 0
            if duration and duration > 0:
                # Try precise filesize from selected format if present
                preferred_filesize = None
                # formats may contain filesize for muxed or individual streams
                for f in (info.get('formats') or []):
                    if f.get('ext') in {'mp4', 'mkv', 'webm'} and f.get('filesize'):
                        preferred_filesize = f.get('filesize')
                        break
                total_bytes = preferred_filesize or info.get('filesize') or info.get('filesize_approx')
                if total_bytes and total_bytes > 0:
                    bps = total_bytes / (duration / max(0.1, self.config.WATCH_SPEED))
                    return max(64_000, int(bps))  # >= 64KB/s
        except Exception:
            pass
        
        # Heuristic fallback by resolution
        width = height = 0
        best_format = None
        for f in (info.get('formats') or []):
            if f.get('vcodec') != 'none':
                if (f.get('height', 0), f.get('width', 0)) > (height, width):
                    height = f.get('height', 0)
                    width = f.get('width', 0)
                    best_format = f
        # Typical AVC bitrates (very rough)
        if height >= 1080:
            mbps = 8.0
        elif height >= 720:
            mbps = 3.0
        elif height >= 480:
            mbps = 1.0
        else:
            mbps = 0.6
        bps = (mbps * 1_000_000) / max(0.1, self.config.WATCH_SPEED)
        return int(bps)
    
    def get_ydl_opts(self, output_path: str, info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get yt-dlp options for downloading highest quality video"""
        opts: Dict[str, Any] = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'writeinfojson': True,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'extractaudio': False,
            'audioformat': 'mp3',
            'embed_subs': False,
            'embed_thumbnail': False,
            'add_metadata': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            # Size limit
            'max_filesize': int(self.max_file_size_gb * 1024 * 1024 * 1024),  # Convert GB to bytes
        }
        
        # Merge common options (headers, cookies, request-sleep)
        opts.update(self._build_common_ydl_opts())
        
        # Rate limiting to simulate watch-time
        ratelimit_bps = self._compute_watchlike_ratelimit(info or {})
        if ratelimit_bps:
            opts['ratelimit'] = ratelimit_bps
            logger.debug(f"Using ratelimit {ratelimit_bps} B/s to simulate watch-time")
        
        return opts
    
    def extract_video_info(self, url: str) -> Dict[str, Any]:
        """Extract video information without downloading"""
        # Use ScraperAPI if enabled and available
        if self.scraperapi_client:
            try:
                logger.info(f"Using ScraperAPI to extract video info for {url}")
                info = self.scraperapi_client.get_video_info(url)
                # Convert ScraperAPI format to yt-dlp compatible format
                return self._convert_scraperapi_to_ytdlp_format(info)
            except Exception as e:
                logger.warning(f"ScraperAPI failed, falling back to yt-dlp: {str(e)}")
                # Fall back to yt-dlp if ScraperAPI fails
        
        # Original yt-dlp extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        # Use same headers/cookies for info extraction
        ydl_opts.update(self._build_common_ydl_opts())
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return info
            except Exception as e:
                logger.exception(f"Failed to extract video info for {url}: {str(e)}")
                raise
    
    def _convert_scraperapi_to_ytdlp_format(self, scraperapi_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ScraperAPI response format to yt-dlp compatible format
        
        Args:
            scraperapi_info: Video info from ScraperAPI
        
        Returns:
            yt-dlp compatible info dictionary
        """
        # Parse upload date if present
        upload_date = None
        if scraperapi_info.get('upload_date'):
            try:
                # Try to parse ISO format date
                dt = datetime.fromisoformat(scraperapi_info['upload_date'].replace('Z', '+00:00'))
                upload_date = dt.strftime('%Y%m%d')
            except:
                pass
        
        # Convert to yt-dlp format
        ytdlp_info = {
            'id': scraperapi_info.get('youtube_id', ''),
            'title': scraperapi_info.get('title', ''),
            'description': scraperapi_info.get('description', ''),
            'duration': scraperapi_info.get('duration'),
            'view_count': scraperapi_info.get('view_count'),
            'like_count': scraperapi_info.get('like_count'),
            'upload_date': upload_date,
            'uploader': scraperapi_info.get('channel_name', ''),
            'uploader_url': scraperapi_info.get('channel_url', ''),
            'thumbnail': scraperapi_info.get('thumbnail_url', ''),
            'webpage_url': scraperapi_info.get('url', ''),
            'tags': scraperapi_info.get('tags', []),
            'categories': [scraperapi_info.get('category')] if scraperapi_info.get('category') else [],
            'is_live': scraperapi_info.get('is_live', False),
            'age_limit': 18 if scraperapi_info.get('is_age_restricted') else 0,
            # ScraperAPI doesn't provide these, set defaults
            'formats': [],
            'width': None,
            'height': None,
            'fps': None,
            'vcodec': None,
            'acodec': None,
            'filesize': None,
            '_scraperapi_metadata': True,  # Flag to indicate this came from ScraperAPI
        }
        
        return ytdlp_info
    
    def download_video(self, url: str, video_id: str, info: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Download a single video
        
        Args:
            url: Video URL
            video_id: YouTube video ID
            info: Extracted video info for ratelimit computation
        
        Returns:
            Tuple of (success, message, file_path)
        """
        # Check if this is ScraperAPI metadata (no download capability)
        if info.get('_scraperapi_metadata'):
            logger.warning(f"Video {video_id} metadata was extracted via ScraperAPI. Download requires yt-dlp.")
            # Try to re-extract with yt-dlp for download
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                }
                ydl_opts.update(self._build_common_ydl_opts())
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                return False, f"Cannot download video {video_id}: ScraperAPI provides metadata only, and yt-dlp failed: {str(e)}", None
        
        # Original download logic continues...
        try:
            # Create temporary directory for this download
            with tempfile.TemporaryDirectory(dir=self.download_path) as temp_dir:
                output_template = os.path.join(temp_dir, f"{video_id}.%(ext)s")
                ydl_opts = self.get_ydl_opts(output_template, info)
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    logger.info(f"Starting download for video {video_id}")
                    ydl.download([url])
                    
                    # Find the downloaded video file
                    video_files = list(Path(temp_dir).glob(f"{video_id}.*"))
                    video_files = [f for f in video_files if f.suffix.lower() in ['.mp4', '.mkv', '.webm', '.avi']]
                    
                    if not video_files:
                        return False, "No video file found after download", None
                    
                    video_file = video_files[0]
                    
                    # Move file to a permanent location temporarily
                    final_path = os.path.join(self.download_path, f"{video_id}_{int(datetime.now().timestamp())}.mp4")
                    shutil.move(str(video_file), final_path)
                    
                    logger.info(f"Successfully downloaded video {video_id} to {final_path}")
                    return True, f"Downloaded video {video_id}", final_path
                    
        except Exception as e:
            error_msg = f"Failed to download video {video_id}: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg, None
    
    def process_video_metadata(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean video metadata from yt-dlp info"""
        
        # Parse upload date
        upload_date = None
        if info.get('upload_date'):
            try:
                upload_date = datetime.strptime(info['upload_date'], '%Y%m%d').date()
            except (ValueError, TypeError):
                pass
        
        # Get the best format info
        formats = info.get('formats', [])
        best_format = None
        if formats:
            # Find the best video format
            video_formats = [f for f in formats if f.get('vcodec') != 'none']
            if video_formats:
                best_format = max(video_formats, key=lambda x: (x.get('height', 0), x.get('width', 0)))
        
        return {
            'youtube_id': info.get('id', ''),
            'url': info.get('webpage_url', ''),
            'title': info.get('title', ''),
            'description': info.get('description', ''),
            'duration': info.get('duration'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'upload_date': upload_date,
            'uploader': info.get('uploader'),
            'uploader_id': info.get('uploader_id'),
            'thumbnail_url': info.get('thumbnail'),
            'tags': info.get('tags', []),
            'categories': info.get('categories', []),
            'resolution': f"{best_format.get('width', 0)}x{best_format.get('height', 0)}" if best_format else None,
            'fps': best_format.get('fps') if best_format else None,
            'format_id': best_format.get('format_id') if best_format else None,
        }
    
    async def scrape_single_video(self, url: str, youtube_url_id: uuid.UUID) -> Tuple[bool, str]:
        """
        Scrape a single video: extract info, download, upload to B2, save to DB
        
        Args:
            url: Video URL
            youtube_url_id: ID of the YouTube URL record
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Extract video information
            logger.info(f"Extracting info for video: {url}")
            info = self.extract_video_info(url)
            video_id = info.get('id')
            
            if not video_id:
                return False, "Could not extract video ID"
            
            # Check if video already exists in database
            existing_video = await db.get_video_by_youtube_id(video_id)
            if existing_video:
                # Link existing video to this URL
                await db.link_video_to_url(youtube_url_id, existing_video.id)
                return True, f"Video {video_id} already exists, linked to URL"
            
            # Process metadata
            video_data = self.process_video_metadata(info)
            
            # Download video
            success, message, file_path = self.download_video(url, video_id, info)
            if not success:
                return False, f"Download failed: {message}"
            
            try:
                # Get file size
                file_size = os.path.getsize(file_path)
                video_data['file_size'] = file_size
                
                # Generate B2 key
                b2_key = generate_video_key(video_id, video_data['title'])
                
                # Upload to Backblaze B2
                logger.info(f"Uploading video {video_id} to B2")
                upload_success, upload_result = storage.upload_file(file_path, b2_key, 'video/mp4')
                
                if upload_success:
                    video_data['b2_file_key'] = b2_key
                    video_data['b2_file_url'] = upload_result
                    logger.info(f"Successfully uploaded video {video_id} to B2")
                else:
                    logger.error(f"Failed to upload video {video_id} to B2: {upload_result}")
                    return False, f"Upload to B2 failed: {upload_result}"
                
                # Save video to database
                video_record = await db.create_video(video_data)
                
                # Link video to URL
                await db.link_video_to_url(youtube_url_id, video_record.id)
                
                logger.info(f"Successfully processed video {video_id}")
                return True, f"Successfully processed video {video_id}"
                
            finally:
                # CRITICAL: Clean up downloaded file to prevent disk space issues
                # This ensures the server doesn't accumulate video files
                # Files are only stored temporarily during upload process
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up temporary file: {file_path}")
                    # At this point, video exists ONLY in Backblaze B2 cloud storage
                    
        except Exception as e:
            error_msg = f"Error processing video {url}: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg
    
    async def scrape_playlist_or_channel(self, url: str, youtube_url_id: uuid.UUID, max_videos: int = None) -> Tuple[bool, str, int]:
        """
        Scrape all videos from a playlist or channel
        
        Args:
            url: Playlist or channel URL
            youtube_url_id: ID of the YouTube URL record
            max_videos: Maximum number of videos to process (None for all)
        
        Returns:
            Tuple of (success, message, videos_processed)
        """
        try:
            logger.info(f"Extracting playlist/channel info: {url}")
            
            # Extract playlist/channel information
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,  # Only get video URLs, don't extract full info yet
                'playlistend': max_videos,
            }
            ydl_opts.update(self._build_common_ydl_opts())
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
            if 'entries' not in info:
                return False, "No videos found in playlist/channel", 0
            
            entries = info['entries']
            total_videos = len(entries)
            processed_videos = 0
            failed_videos = 0
            
            logger.info(f"Found {total_videos} videos to process")
            
            for i, entry in enumerate(entries):
                if not entry:
                    continue
                
                video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                
                try:
                    success, message = await self.scrape_single_video(video_url, youtube_url_id)
                    if success:
                        processed_videos += 1
                        logger.info(f"Processed video {i+1}/{total_videos}: {entry.get('title', 'Unknown')}")
                    else:
                        failed_videos += 1
                        logger.warning(f"Failed to process video {i+1}/{total_videos}: {message}")
                        
                except Exception as e:
                    failed_videos += 1
                    logger.exception(f"Error processing video {i+1}/{total_videos}: {str(e)}")
                
                # Human-like randomized delay between videos
                delay = random.uniform(self.config.HUMAN_DELAY_MIN_SEC, self.config.HUMAN_DELAY_MAX_SEC)
                await asyncio.sleep(delay)
            
            success_msg = f"Processed {processed_videos} videos successfully"
            if failed_videos > 0:
                success_msg += f", {failed_videos} failed"
            
            return True, success_msg, processed_videos
            
        except Exception as e:
            error_msg = f"Error processing playlist/channel {url}: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg, 0
    
    async def scrape_url(self, url: str, url_type: URLType, youtube_url_id: uuid.UUID) -> Tuple[bool, str, int]:
        """
        Scrape videos from any YouTube URL type
        
        Args:
            url: YouTube URL
            url_type: Type of URL (video, playlist, channel, user)
            youtube_url_id: ID of the YouTube URL record
        
        Returns:
            Tuple of (success, message, videos_processed)
        """
        if url_type == URLType.VIDEO:
            success, message = await self.scrape_single_video(url, youtube_url_id)
            return success, message, 1 if success else 0
        else:
            return await self.scrape_playlist_or_channel(url, youtube_url_id)

# Global scraper instance
scraper = VideoScraper()