import os
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uuid

from models import (
    YouTubeURLCreate, YouTubeURLResponse, ScrapingJobResponse, 
    VideoResponse, URLType, JobStatus
)
from database import db
from youtube_parser import YouTubeURLParser, parse_youtube_url
from tasks import scrape_youtube_url_task, extract_url_metadata_task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="YouTube Video Scraper",
    description="A system to scrape YouTube videos and store them in Backblaze B2 with metadata in Supabase",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")

# API Routes
@app.get("/")
async def home(request: Request):
    """Home page with URL submission form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/urls", response_model=dict)
async def submit_url(url_data: YouTubeURLCreate):
    """Submit a YouTube URL for scraping"""
    try:
        # Validate and parse the URL
        url_type, identifier = parse_youtube_url(url_data.url)
        normalized_url = YouTubeURLParser.normalize_url(url_data.url)
        
        # Extract basic metadata
        try:
            metadata = YouTubeURLParser.extract_metadata(normalized_url)
            title = metadata.get('title')
            description = metadata.get('description')
        except Exception as e:
            logger.warning(f"Could not extract metadata for {normalized_url}: {str(e)}")
            title = None
            description = None
        
        # Create URL entry in database
        url_record = await db.create_youtube_url(
            url=normalized_url,
            url_type=url_type,
            title=title,
            description=description
        )
        
        # Create scraping job
        job_record = await db.create_scraping_job(url_record.id)
        
        # Start background scraping task
        task = scrape_youtube_url_task.delay(
            str(job_record.id),
            normalized_url,
            url_type.value
        )
        
        return {
            "success": True,
            "message": "URL submitted successfully",
            "url_id": str(url_record.id),
            "job_id": str(job_record.id),
            "task_id": task.id,
            "url_type": url_type.value,
            "title": title
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/urls", response_model=List[YouTubeURLResponse])
async def list_urls(limit: int = 50, offset: int = 0):
    """List all submitted YouTube URLs"""
    try:
        urls = await db.get_youtube_urls(limit=limit, offset=offset)
        return urls
    except Exception as e:
        logger.error(f"Error listing URLs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/urls/{url_id}", response_model=YouTubeURLResponse)
async def get_url(url_id: str):
    """Get a specific YouTube URL by ID"""
    try:
        url_uuid = uuid.UUID(url_id)
        url_record = await db.get_youtube_url(url_uuid)
        if not url_record:
            raise HTTPException(status_code=404, detail="URL not found")
        return url_record
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid URL ID format")
    except Exception as e:
        logger.error(f"Error getting URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/urls/{url_id}/videos", response_model=List[VideoResponse])
async def get_url_videos(url_id: str):
    """Get all videos for a specific YouTube URL"""
    try:
        url_uuid = uuid.UUID(url_id)
        videos = await db.get_videos_by_url(url_uuid)
        return videos
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid URL ID format")
    except Exception as e:
        logger.error(f"Error getting videos: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/jobs/{job_id}", response_model=ScrapingJobResponse)
async def get_job_status(job_id: str):
    """Get the status of a scraping job"""
    try:
        job_uuid = uuid.UUID(job_id)
        job = await db.get_scraping_job(job_uuid)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/jobs", response_model=List[ScrapingJobResponse])
async def list_jobs():
    """List all scraping jobs"""
    try:
        jobs = await db.get_pending_jobs()
        return jobs
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/validate-url")
async def validate_url(url_data: YouTubeURLCreate):
    """Validate a YouTube URL without submitting it"""
    try:
        url_type, identifier = parse_youtube_url(url_data.url)
        normalized_url = YouTubeURLParser.normalize_url(url_data.url)
        
        return {
            "valid": True,
            "url_type": url_type.value,
            "normalized_url": normalized_url,
            "identifier": identifier
        }
    except ValueError as e:
        return {
            "valid": False,
            "error": str(e)
        }

@app.get("/dashboard")
async def dashboard(request: Request):
    """Dashboard page showing submitted URLs and their status"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/dashboard-data")
async def dashboard_data():
    """Get dashboard data (URLs, jobs, statistics)"""
    try:
        # Get recent URLs
        urls = await db.get_youtube_urls(limit=20)
        
        # Get job statistics
        # This would need more database methods to get proper statistics
        stats = {
            "total_urls": len(urls),
            "pending_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "total_videos": 0
        }
        
        return {
            "urls": [url.dict() for url in urls],
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)