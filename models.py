from datetime import datetime, date
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, HttpUrl, Field
import uuid

class URLType(str, Enum):
    VIDEO = "video"
    CHANNEL = "channel"
    PLAYLIST = "playlist"
    USER = "user"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class YouTubeURLCreate(BaseModel):
    url: str = Field(..., description="YouTube URL to scrape")

class YouTubeURLResponse(BaseModel):
    id: uuid.UUID
    url: str
    url_type: URLType
    title: Optional[str] = None
    description: Optional[str] = None
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

class VideoCreate(BaseModel):
    youtube_id: str
    url: str
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    upload_date: Optional[date] = None
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    file_size: Optional[int] = None
    format_id: Optional[str] = None
    b2_file_key: Optional[str] = None
    b2_file_url: Optional[str] = None

class VideoResponse(BaseModel):
    id: uuid.UUID
    youtube_id: str
    url: str
    title: str
    description: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    upload_date: Optional[date] = None
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None
    file_size: Optional[int] = None
    format_id: Optional[str] = None
    b2_file_key: Optional[str] = None
    b2_file_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ScrapingJobCreate(BaseModel):
    youtube_url_id: uuid.UUID

class ScrapingJobResponse(BaseModel):
    id: uuid.UUID
    youtube_url_id: uuid.UUID
    status: JobStatus
    progress_percent: int = 0
    videos_found: int = 0
    videos_processed: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class ScrapingJobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    progress_percent: Optional[int] = None
    videos_found: Optional[int] = None
    videos_processed: Optional[int] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None