# database.py
import os
import re
import json
import uuid
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from postgrest.exceptions import APIError
from supabase import create_client, Client

from models import URLType, JobStatus, VideoStatus, YouTubeURLResponse, VideoResponse, ScrapingJobResponse
from config import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class Database:
    def __init__(self):
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
        self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        self._table_columns_cache = {}
    
    async def get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table (cached for efficiency)"""
        if table_name in self._table_columns_cache:
            return self._table_columns_cache[table_name]
        
        # Query the information schema to get columns
        # For Supabase, we'll use a simple approach - try to get one row and extract keys
        try:
            result = self.supabase.table(table_name).select("*").limit(1).execute()
            if result.data:
                columns = list(result.data[0].keys())
            else:
                # If no data, use default columns based on table name
                if table_name == "videos":
                    columns = ['id', 'youtube_id', 'url', 'title', 'description', 'duration', 
                              'view_count', 'like_count', 'upload_date', 'uploader', 'uploader_id',
                              'thumbnail_url', 'tags', 'categories', 'resolution', 'fps', 'file_size',
                              'format_id', 'b2_file_key', 'b2_file_url', 'status', 'created_at', 'updated_at',
                              'videourl', 'thumbnailurl', 'viewcount', 'likecount', 'dislikecount',
                              'commentcount', 'channelid', 'category', 'privacy', 'allowdownloads']
                else:
                    columns = []
            
            self._table_columns_cache[table_name] = columns
            return columns
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
            # Return a sensible default for videos table
            if table_name == "videos":
                return ['id', 'youtube_id', 'url', 'title', 'description', 'status', 'created_at', 'updated_at']
            return []

    async def create_video(self, video_data: Dict[str, Any]) -> VideoResponse:
        # --- Get current schema columns (cached in production for efficiency) ---
        videos_columns = await self.get_table_columns("videos")

        # --- Set defaults for required fields ---
        youtube_id = video_data.get("youtube_id", "")
        video_data.setdefault("videourl", "videos/default.mp4")
        video_data.setdefault("url", f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else "https://www.youtube.com/")
        video_data.setdefault("status", "pending")  # Default status for new videos
        now_iso = datetime.utcnow().isoformat()
        video_data.setdefault("created_at", now_iso)
        video_data.setdefault("updated_at", now_iso)

        # --- Keep only columns that exist in the table ---
        filtered_data = {k: v for k, v in video_data.items() if k in videos_columns}

        # --- Serialize datetime/date objects ---
        for k, v in filtered_data.items():
            if isinstance(v, (datetime, date)):
                filtered_data[k] = v.isoformat()

        # --- Insert into database ---
        result = self.supabase.table("videos").insert(filtered_data).execute()

        if result.data:
            # Merge server-returned values to satisfy Pydantic model
            final_row = {**filtered_data, **(result.data[0] or {})}
            return VideoResponse(**final_row)

        raise Exception("Failed to create video entry")

    # --- The rest of your DB helper methods (unchanged) ---
    async def get_youtube_url(self, url_id: uuid.UUID) -> Optional[YouTubeURLResponse]:
        result = self.supabase.table("youtube_urls").select("*").eq("id", str(url_id)).execute()
        if result.data:
            return YouTubeURLResponse(**result.data[0])
        return None

    async def get_youtube_urls(self, limit: int = 100, offset: int = 0) -> List[YouTubeURLResponse]:
        result = self.supabase.table("youtube_urls").select("*").range(offset, offset + limit - 1).order("created_at", desc=True).execute()
        return [YouTubeURLResponse(**item) for item in result.data or []]

    async def get_video_by_youtube_id(self, youtube_id: str) -> Optional[VideoResponse]:
        result = self.supabase.table("videos").select("*").eq("youtube_id", youtube_id).execute()
        if result.data:
            return VideoResponse(**result.data[0])
        return None

    async def update_video(self, video_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[VideoResponse]:
        result = self.supabase.table("videos").update(update_data).eq("id", str(video_id)).execute()
        if result.data:
            return VideoResponse(**result.data[0])
        return None

    async def get_videos_by_url(self, url_id: uuid.UUID) -> List[VideoResponse]:
        result = self.supabase.table("url_videos").select("videos(*)").eq("youtube_url_id", str(url_id)).execute()
        videos = []
        for item in result.data or []:
            if item.get("videos"):
                videos.append(VideoResponse(**item["videos"]))
        return videos

    async def create_scraping_job(self, youtube_url_id: uuid.UUID) -> ScrapingJobResponse:
        data = {
            "youtube_url_id": str(youtube_url_id),
            "status": JobStatus.PENDING.value
        }
        result = self.supabase.table("scraping_jobs").insert(data).execute()
        if result.data:
            return ScrapingJobResponse(**result.data[0])
        raise Exception("Failed to create scraping job")

    async def update_scraping_job(self, job_id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[ScrapingJobResponse]:
        result = self.supabase.table("scraping_jobs").update(update_data).eq("id", str(job_id)).execute()
        if result.data:
            return ScrapingJobResponse(**result.data[0])
        return None

    async def get_scraping_job(self, job_id: uuid.UUID) -> Optional[ScrapingJobResponse]:
        result = self.supabase.table("scraping_jobs").select("*").eq("id", str(job_id)).execute()
        if result.data:
            return ScrapingJobResponse(**result.data[0])
        return None

    async def get_scraping_jobs_by_url(self, url_id: uuid.UUID) -> List[ScrapingJobResponse]:
        result = self.supabase.table("scraping_jobs").select("*").eq("youtube_url_id", str(url_id)).order("created_at", desc=True).execute()
        return [ScrapingJobResponse(**item) for item in result.data or []]

    async def get_pending_jobs(self) -> List[ScrapingJobResponse]:
        result = self.supabase.table("scraping_jobs").select("*").eq("status", JobStatus.PENDING.value).order("created_at").execute()
        return [ScrapingJobResponse(**item) for item in result.data or []]

    async def link_video_to_url(self, youtube_url_id: uuid.UUID, video_id: uuid.UUID, position: int = None):
        data = {
            "youtube_url_id": str(youtube_url_id),
            "video_id": str(video_id),
            "position": position
        }
        result = self.supabase.table("url_videos").upsert(data).execute()
        return result.data
    
    async def get_pending_videos(self, limit: int = 10) -> List[VideoResponse]:
        """Get videos with status 'pending' for processing"""
        result = self.supabase.table("videos").select("*").eq("status", VideoStatus.PENDING.value).limit(limit).order("created_at").execute()
        return [VideoResponse(**item) for item in result.data or []]
    
    async def update_video_status(self, video_id: uuid.UUID, status: VideoStatus) -> Optional[VideoResponse]:
        """Update the status of a video"""
        update_data = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        result = self.supabase.table("videos").update(update_data).eq("id", str(video_id)).execute()
        if result.data:
            return VideoResponse(**result.data[0])
        return None
    
    async def mark_video_as_fetching(self, video_id: uuid.UUID) -> Optional[VideoResponse]:
        """Mark a video as being fetched (with atomic update to prevent race conditions)"""
        # First check if the video is still pending
        check_result = self.supabase.table("videos").select("status").eq("id", str(video_id)).execute()
        if not check_result.data or check_result.data[0].get("status") != VideoStatus.PENDING.value:
            return None  # Already being processed or done
        
        # Update only if still pending (race condition protection)
        update_data = {
            "status": VideoStatus.FETCHING.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        result = self.supabase.table("videos").update(update_data).eq("id", str(video_id)).eq("status", VideoStatus.PENDING.value).execute()
        if result.data:
            return VideoResponse(**result.data[0])
        return None


# Global database instance
db = Database()
