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
        """
        Robust insertion for the `videos` table:
         - Serializes datetime/date to ISO strings
         - Removes None values
         - Provides defaults for required fields (videourl, url, created_at, updated_at)
         - Retries removing unknown columns when PostgREST returns PGRST204
         - After successful insert, merges returned row with the payload and constructs VideoResponse
        """
        payload: Dict[str, Any] = dict(video_data)  # shallow copy

        # --- Defaults for required columns (customize as needed) ---
        # Use youtube_id to build user-friendly url if possible
        youtube_id = payload.get("youtube_id") or ""
        payload.setdefault("videourl", "videos/default.mp4")
        payload.setdefault("url", f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else "https://www.youtube.com/")
        now_iso = datetime.utcnow().isoformat()
        payload.setdefault("created_at", now_iso)
        payload.setdefault("updated_at", now_iso)

        # --- Normalize payload: serialize datetimes and coerce non-serializable objects ---
        for k, v in list(payload.items()):
            if isinstance(v, (datetime, date)):
                payload[k] = v.isoformat()
            elif not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                try:
                    json.dumps(v)
                except Exception:
                    payload[k] = str(v)

        # Remove None values (we already set defaults above)
        payload = {k: v for k, v in payload.items() if v is not None}

        max_retries = 20
        attempt = 0
        removed_columns = []

        while attempt < max_retries and payload:
            try:
                result = self.supabase.table("videos").insert(payload).execute()

                # result.data may be None/empty in some cases (PostgREST config), so build final dict safely
                returned_row = (result.data[0] if getattr(result, "data", None) else {}) or {}

                # Merge: prefer server-returned values when present (returned_row overrides payload)
                final_row = {**payload, **returned_row}

                # Ensure created_at/updated_at exist in final_row
                if not final_row.get("created_at"):
                    final_row["created_at"] = datetime.utcnow().isoformat()
                if not final_row.get("updated_at"):
                    final_row["updated_at"] = datetime.utcnow().isoformat()
                if not final_row.get("url"):
                    final_row["url"] = f"https://www.youtube.com/watch?v={final_row.get('youtube_id','')}"

                # Attempt to build VideoResponse and return
                try:
                    return VideoResponse(**final_row)
                except Exception as ve:
                    # Provide debug context for Pydantic errors
                    logger.exception("VideoResponse validation failed. final_row keys: %s", list(final_row.keys()))
                    raise

            except APIError as e:
                # Example message:
                # "Could not find the 'thumbnail_url' column of 'videos' in the schema cache"
                msg_obj = e.args[0] if e.args else str(e)
                msg = msg_obj if isinstance(msg_obj, str) else json.dumps(msg_obj)
                m = re.search(r"Could not find the '([^']+)' column", msg)
                if m:
                    bad_col = m.group(1)
                    if bad_col in payload:
                        payload.pop(bad_col, None)
                        removed_columns.append(bad_col)
                        attempt += 1
                        logger.warning("Removed unknown column '%s' from payload and retrying (attempt %d).", bad_col, attempt)
                        continue
                # If we couldn't parse a PGRST204 unknown-column, re-raise for visibility
                logger.exception("APIError during insert: %s", msg)
                raise

            except TypeError:
                # JSON serialization problem: coerce problematic values to strings then retry
                for k, v in list(payload.items()):
                    try:
                        json.dumps(v)
                    except Exception:
                        payload[k] = str(v)
                attempt += 1
                logger.warning("Coerced non-serializable values to strings and retrying (attempt %d).", attempt)
                continue

            except Exception:
                # Unknown failure — re-raise so caller sees it
                logger.exception("Unknown error during create_video insert")
                raise

        # If we exit loop without returning:
        logger.error(
            "Failed to insert video after %d attempts. Removed columns: %s. Final payload keys: %s",
            attempt, removed_columns, list(payload.keys())
        )
        raise Exception("Failed to insert video after removing unknown columns or payload became empty")

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
