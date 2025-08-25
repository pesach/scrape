"""
Database Adapter for Existing Videos Table
==========================================

This module adapts the YouTube Video Scraper to work with an existing videos table
that has different column names than expected.

Existing table structure:
- id, createdat, updatedat, title, description, videourl, thumbnailurl, duration
- userid, channelid, category, tags, status, privacy, viewcount, likes, dislikes
- allowdownloads, likecount, dislikecount, commentcount

Mapping to scraper expectations:
- videourl -> url (main video URL)  
- thumbnailurl -> thumbnail_url
- likecount -> like_count
- viewcount -> view_count
- etc.
"""

from supabase import create_client, Client
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExistingVideosAdapter:
    """Adapter to work with existing videos table structure"""
    
    def __init__(self):
        from config import config
        
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
        
        self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    def map_to_existing_structure(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map scraper video data to existing table structure"""
        mapped = {
            # Core video information
            'title': video_data.get('title'),
            'description': video_data.get('description'),
            'videourl': video_data.get('url'),  # Main video URL
            'thumbnailurl': video_data.get('thumbnail_url'),
            'duration': video_data.get('duration'),  # Already in seconds
            
            # Statistics (map to existing columns)
            'viewcount': video_data.get('view_count', 0),
            'likecount': video_data.get('like_count', 0),
            'dislikecount': video_data.get('dislike_count', 0),  # Often 0 due to YouTube changes
            'commentcount': 0,  # Would need separate API call
            
            # Channel information
            'channelid': video_data.get('uploader_id'),
            'category': video_data.get('categories', [None])[0] if video_data.get('categories') else None,
            'tags': video_data.get('tags', []),  # Keep as array or convert to string if needed
            
            # Status and privacy
            'status': video_data.get('status', 'pending'),  # Video processing status: pending/fetching/done/failed
            'privacy': 'public',  # Assume public since we can scrape it
            'allowdownloads': True,  # We downloaded it, so it's allowed
            
            # New columns added by migration (if they exist)
            'youtube_id': video_data.get('youtube_id'),
            'uploader': video_data.get('uploader'),
            'uploader_id': video_data.get('uploader_id'),
            'upload_date': video_data.get('upload_date'),
            'resolution': video_data.get('resolution'),
            'fps': video_data.get('fps'),
            'file_size': video_data.get('file_size'),
            'format_id': video_data.get('format_id'),
            'b2_file_key': video_data.get('b2_file_key'),
            'b2_file_url': video_data.get('b2_file_url'),
            'categories': video_data.get('categories', []),
        }
        
        # Remove None values to avoid overwriting existing data
        return {k: v for k, v in mapped.items() if v is not None}
    
    def create_video(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new video record using existing table structure"""
        try:
            mapped_data = self.map_to_existing_structure(video_data)
            
            # Check if video already exists by youtube_id (if column exists)
            youtube_id = video_data.get('youtube_id')
            if youtube_id:
                existing = self.supabase.table('videos').select('*').eq('youtube_id', youtube_id).execute()
                if existing.data:
                    logger.info(f"Video already exists: {youtube_id}")
                    return existing.data[0]
            
            # Create new video record
            result = self.supabase.table('videos').insert(mapped_data).execute()
            
            if result.data:
                logger.info(f"Created video record: {result.data[0]['id']}")
                return result.data[0]
            else:
                logger.error(f"Failed to create video: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            return None
    
    def update_video(self, video_id: str, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update existing video record"""
        try:
            mapped_data = self.map_to_existing_structure(video_data)
            
            result = self.supabase.table('videos').update(mapped_data).eq('id', video_id).execute()
            
            if result.data:
                logger.info(f"Updated video record: {video_id}")
                return result.data[0]
            else:
                logger.error(f"Failed to update video: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating video: {str(e)}")
            return None
    
    def get_video_by_youtube_id(self, youtube_id: str) -> Optional[Dict[str, Any]]:
        """Get video by YouTube ID (if column exists)"""
        try:
            result = self.supabase.table('videos').select('*').eq('youtube_id', youtube_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching video by youtube_id: {str(e)}")
            return None
    
    def get_video_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video by URL"""
        try:
            result = self.supabase.table('videos').select('*').eq('videourl', url).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching video by URL: {str(e)}")
            return None
    
    def get_videos_by_channel(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get all videos from a specific channel"""
        try:
            result = self.supabase.table('videos').select('*').eq('channelid', channel_id).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching videos by channel: {str(e)}")
            return []
    
    def get_recent_videos(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recently added videos"""
        try:
            result = self.supabase.table('videos').select('*').order('createdat', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching recent videos: {str(e)}")
            return []

# Wrapper functions to maintain compatibility with existing code
class Database:
    """Main database class that uses the existing videos table"""
    
    def __init__(self):
        from config import config
        
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
        
        self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self.videos_adapter = ExistingVideosAdapter()
    
    # YouTube URLs methods (new tables)
    def create_youtube_url(self, url_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new YouTube URL record"""
        try:
            result = self.supabase.table('youtube_urls').insert(url_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating YouTube URL: {str(e)}")
            return None
    
    def get_youtube_url(self, url_id: str) -> Optional[Dict[str, Any]]:
        """Get YouTube URL by ID"""
        try:
            result = self.supabase.table('youtube_urls').select('*').eq('id', url_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error fetching YouTube URL: {str(e)}")
            return None
    
    # Video methods (using adapter for existing table)
    def create_video(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create video using existing table structure"""
        return self.videos_adapter.create_video(video_data)
    
    def get_video_by_youtube_id(self, youtube_id: str) -> Optional[Dict[str, Any]]:
        """Get video by YouTube ID"""
        return self.videos_adapter.get_video_by_youtube_id(youtube_id)
    
    # Scraping jobs methods (new table)
    def create_scraping_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new scraping job"""
        try:
            result = self.supabase.table('scraping_jobs').insert(job_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating scraping job: {str(e)}")
            return None
    
    def update_scraping_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update scraping job status"""
        try:
            result = self.supabase.table('scraping_jobs').update(updates).eq('id', job_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating scraping job: {str(e)}")
            return None
    
    def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """Get all pending scraping jobs"""
        try:
            result = self.supabase.table('scraping_jobs').select('*').eq('status', 'pending').execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching pending jobs: {str(e)}")
            return []
    
    # URL-Video relationships (new table)
    def link_url_to_video(self, youtube_url_id: str, video_id: str) -> bool:
        """Create relationship between URL and video"""
        try:
            result = self.supabase.table('url_videos').insert({
                'youtube_url_id': youtube_url_id,
                'video_id': video_id
            }).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error linking URL to video: {str(e)}")
            return False
    
    def get_videos_for_url(self, youtube_url_id: str) -> List[Dict[str, Any]]:
        """Get all videos associated with a YouTube URL"""
        try:
            # Join url_videos with videos table
            result = self.supabase.table('url_videos').select(
                '*, videos(*)'
            ).eq('youtube_url_id', youtube_url_id).execute()
            
            return [item['videos'] for item in result.data if item['videos']] if result.data else []
        except Exception as e:
            logger.error(f"Error fetching videos for URL: {str(e)}")
            return []

# Create global database instance
db = Database()