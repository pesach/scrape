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

from models import URLType, JobStatus, YouTubeURLResponse, VideoResponse, ScrapingJobResponse
from config import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


class Database:
    def __init__(self):
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
        self.supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    async def create_video(self, video_data: Dict[str, Any]) -> VideoResponse:
        # --- Get current schema columns (cached in production for efficiency) ---
        videos_columns = await self.get_table_columns("videos")

        # --- Set defaults for required fields ---
        youtube_id = video_data.get("youtube_id", "")
        video_data.setdefault("videourl", "videos/default.mp4")
        video_data.setdefault("url", f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else "https://www.youtube.com/")
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


# Global database instance
db = Database()
