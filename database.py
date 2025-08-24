import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from models import URLType, JobStatus, YouTubeURLResponse, VideoResponse, ScrapingJobResponse
import uuid
from datetime import datetime

class Database:
    def __init__(self):
        from config import config
        
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
        
        self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    
    async def create_youtube_url(self, url: str, url_type: URLType, title: str = None, description: str = None) -> YouTubeURLResponse:
        """Create a new YouTube URL entry"""
        data = {
            "url": url,
            "url_type": url_type.value,
            "title": title,
            "description": description
        }
        
        result = self.supabase.table("youtube_urls").insert(data).execute()
        if result.data:
            return YouTubeURLResponse(**result.data[0])
        raise Exception("Failed to create YouTube URL entry")
    
    async def get_youtube_url(self, url_id: uuid.UUID) -> Optional[YouTubeURLResponse]:
        """Get a YouTube URL by ID"""
        result = self.supabase.table("youtube_urls").select("*").eq("id", str(url_id)).execute()
        if result.data:
            return YouTubeURLResponse(**result.data[0])
        return None
    
    async def get_youtube_urls(self, limit: int = 100, offset: int = 0) -> List[YouTubeURLResponse]:
        """Get all YouTube URLs with pagination"""
        result = self.supabase.table("youtube_urls").select("*").range(offset, offset + limit - 1).order("created_at", desc=True).execute()
        return [YouTubeURLResponse(**item) for item in result.data or []]
    
    async def create_video(self, video_data: Dict[str, Any]) -> VideoResponse:
        """Create a new video entry, filtering out unknown columns."""
        allowed_columns = [
            "youtube_id", "url", "title", "description",
            "duration", "view_count", "upload_date", "uploader",
            "uploader_id", "thumbnail_url", "tags", "categories",
            "resolution", "fps", "format_id", "file_size",
            "b2_file_key", "b2_file_url"
        ]
        filtered_data = {k: v for k, v in video_data.items() if k in allowed_columns}

        # Convert any datetime/date objects to ISO strings
        for k, v in filtered_data.items():
            if isinstance(v, (datetime, date)):
                filtered_data[k] = v.isoformat()

        result = self.supabase.table("videos").insert(filtered_data).execute()
        if result.data:
            return VideoResponse(**result.data[0])
        raise Exception("Failed to create video entry")
    
    async def get_video_by_youtube_id(self, youtube_id: str) -> Optional[VideoResponse]:
        """Get a video by YouTube ID"""
        result = self.supabase.table("videos").select("*").eq("youtube_id", youtube_id).execute()
        if result.data:
            return VideoResponse(**result.data[0])
        return None
    
    async def update_video(self, video_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[VideoResponse]:
        """Update a video entry"""
        result = self.supabase.table("videos").update(update_data).eq("id", str(video_id)).execute()
        if result.data:
            return VideoResponse(**result.data[0])
        return None
    
    async def get_videos_by_url(self, url_id: uuid.UUID) -> List[VideoResponse]:
        """Get all videos for a specific YouTube URL"""
        result = self.supabase.table("url_videos").select(
            "videos(*)"
        ).eq("youtube_url_id", str(url_id)).execute()
        
        videos = []
        for item in result.data or []:
            if item.get("videos"):
                videos.append(VideoResponse(**item["videos"]))
        return videos
    
    async def create_scraping_job(self, youtube_url_id: uuid.UUID) -> ScrapingJobResponse:
        """Create a new scraping job"""
        data = {
            "youtube_url_id": str(youtube_url_id),
            "status": JobStatus.PENDING.value
        }
        
        result = self.supabase.table("scraping_jobs").insert(data).execute()
        if result.data:
            return ScrapingJobResponse(**result.data[0])
        raise Exception("Failed to create scraping job")
    
    async def update_scraping_job(self, job_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[ScrapingJobResponse]:
        """Update a scraping job"""
        result = self.supabase.table("scraping_jobs").update(update_data).eq("id", str(job_id)).execute()
        if result.data:
            return ScrapingJobResponse(**result.data[0])
        return None
    
    async def get_scraping_job(self, job_id: uuid.UUID) -> Optional[ScrapingJobResponse]:
        """Get a scraping job by ID"""
        result = self.supabase.table("scraping_jobs").select("*").eq("id", str(job_id)).execute()
        if result.data:
            return ScrapingJobResponse(**result.data[0])
        return None
    
    async def get_scraping_jobs_by_url(self, url_id: uuid.UUID) -> List[ScrapingJobResponse]:
        """Get all scraping jobs for a URL"""
        result = self.supabase.table("scraping_jobs").select("*").eq("youtube_url_id", str(url_id)).order("created_at", desc=True).execute()
        return [ScrapingJobResponse(**item) for item in result.data or []]
    
    async def get_pending_jobs(self) -> List[ScrapingJobResponse]:
        """Get all pending scraping jobs"""
        result = self.supabase.table("scraping_jobs").select("*").eq("status", JobStatus.PENDING.value).order("created_at").execute()
        return [ScrapingJobResponse(**item) for item in result.data or []]
    
    async def link_video_to_url(self, youtube_url_id: uuid.UUID, video_id: uuid.UUID, position: int = None):
        """Link a video to a YouTube URL (for playlists/channels)"""
        data = {
            "youtube_url_id": str(youtube_url_id),
            "video_id": str(video_id),
            "position": position
        }
        
        # Use upsert to handle duplicates
        result = self.supabase.table("url_videos").upsert(data).execute()
        return result.data

# Global database instance
db = Database()