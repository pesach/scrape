import os
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uuid
import traceback

# Load environment variables FIRST (same as test_setup.py)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

# Load configuration (handles both .env and environment variables)
from config import config

# Setup logging
from logging_config import setup_logging
setup_logging()

from models import (
    YouTubeURLCreate, YouTubeURLResponse, ScrapingJobResponse, 
    VideoResponse, URLType, JobStatus
)

logger = logging.getLogger(__name__)

# Create FastAPI app with better error handling
app = FastAPI(
    title="YouTube Video Scraper",
    description="A system to scrape YouTube videos and store them in Backblaze B2 with metadata in Supabase",
    version="1.0.0",
    debug=True  # Enable debug mode for better error messages
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )

# Initialize database and other components with error handling
db = None
try:
    from database import db as database_instance
    db = database_instance
    logger.info("✅ Database connection initialized")
except Exception as e:
    logger.error(f"❌ Database initialization failed: {str(e)}")
    db = None

# Initialize YouTube parser
youtube_parser = None
try:
    from youtube_parser import YouTubeURLParser, parse_youtube_url
    youtube_parser = YouTubeURLParser
    logger.info("✅ YouTube parser initialized")
except Exception as e:
    logger.error(f"❌ YouTube parser initialization failed: {str(e)}")

# Initialize tasks (optional - may fail if Celery/Redis not available)
scrape_task = None
try:
    from tasks import scrape_youtube_url_task, extract_url_metadata_task
    scrape_task = scrape_youtube_url_task
    logger.info("✅ Celery tasks initialized")
except Exception as e:
    logger.warning(f"⚠️ Celery tasks not available: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    status = {
        "status": "healthy",
        "components": {
            "database": "unknown",
            "youtube_parser": "unknown", 
            "celery": "unknown",
            "environment": "unknown"
        }
    }
    
    # Check database
    if db:
        try:
            # Try a simple database operation
            await db.get_youtube_urls(limit=1)
            status["components"]["database"] = "healthy"
        except Exception as e:
            status["components"]["database"] = f"error: {str(e)}"
            status["status"] = "degraded"
    else:
        status["components"]["database"] = "not initialized"
        status["status"] = "degraded"
    
    # Check YouTube parser
    if youtube_parser:
        try:
            youtube_parser.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            status["components"]["youtube_parser"] = "healthy"
        except Exception as e:
            status["components"]["youtube_parser"] = f"error: {str(e)}"
    else:
        status["components"]["youtube_parser"] = "not initialized"
        status["status"] = "degraded"
    
    # Check Celery
    status["components"]["celery"] = "available" if scrape_task else "not available"
    
    # Check environment variables
    is_valid, missing_vars = config.validate()
    
    if missing_vars:
        status["components"]["environment"] = f"missing variables: {', '.join(missing_vars)}"
        status["status"] = "degraded"
    else:
        status["components"]["environment"] = "configured"
    
    return status

# API Routes
@app.get("/")
async def home(request: Request):
    """Home page with URL submission form"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering home page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Template error: {str(e)}")

@app.post("/api/urls", response_model=dict)
async def submit_url(url_data: YouTubeURLCreate, request: Request):
    """
    Submit a YouTube URL for scraping
    
    PROCESSING FLOW:
    1. Rate limiting check (10/minute per IP)
    2. URL validation and parsing
    3. Metadata extraction (yt-dlp, no API needed)
    4. Database entry (immediate - user gets confirmation)
    5. Background job creation (queued processing)
    6. Return response (user can monitor progress)
    
    HIGH VOLUME HANDLING:
    - URLs saved immediately to database
    - Actual video processing happens asynchronously
    - Rate limiting prevents system overload
    - Graceful degradation if components unavailable
    """
    try:
        # Check rate limits and system capacity
        # IMPORTANT: This prevents system overload during high traffic
        try:
            from rate_limiter import check_request_limits, queue_manager
            await check_request_limits(request, 'submit_url')
        except ImportError:
            logger.warning("Rate limiter not available")
        except HTTPException as e:
            # Return rate limit error with helpful message
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )
        
        try:
            if not db:
                raise HTTPException(status_code=503, detail="Database not available")
            
            if not youtube_parser:
                raise HTTPException(status_code=503, detail="YouTube parser not available")
        
        # Validate and parse the URL
        try:
            url_type, identifier = parse_youtube_url(url_data.url)
            normalized_url = youtube_parser.normalize_url(url_data.url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid YouTube URL: {str(e)}")
        
        # Extract basic metadata using yt-dlp (NO YouTube API needed)
        # IMPORTANT: This uses web scraping, not API calls
        # Benefits: No API keys, no rate limits, works with private videos
        title = None
        description = None
        try:
            metadata = youtube_parser.extract_metadata(normalized_url)
            title = metadata.get('title')
            description = metadata.get('description')
            logger.info(f"✅ Extracted metadata for {normalized_url}")
        except Exception as e:
            logger.warning(f"⚠️ Could not extract metadata for {normalized_url}: {str(e)}")
            # Continue without metadata - we can still create the URL entry
            # This graceful degradation ensures system keeps working even if metadata fails
        
        # Create URL entry in database
        try:
            url_record = await db.create_youtube_url(
                url=normalized_url,
                url_type=url_type,
                title=title,
                description=description
            )
            logger.info(f"✅ Created URL record: {url_record.id}")
        except Exception as e:
            logger.error(f"❌ Database error creating URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        # Create scraping job
        try:
            job_record = await db.create_scraping_job(url_record.id)
            logger.info(f"✅ Created job record: {job_record.id}")
        except Exception as e:
            logger.error(f"❌ Database error creating job: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        # Start background scraping task (if available)
        task_id = None
        if scrape_task:
            try:
                task = scrape_task.delay(
                    str(job_record.id),
                    normalized_url,
                    url_type.value
                )
                task_id = task.id
                logger.info(f"✅ Started background task: {task_id}")
            except Exception as e:
                logger.warning(f"⚠️ Could not start background task: {str(e)}")
                # Continue without background processing
        
        return {
            "success": True,
            "message": "URL submitted successfully",
            "url_id": str(url_record.id),
            "job_id": str(job_record.id),
            "task_id": task_id,
            "url_type": url_type.value,
            "title": title,
            "background_processing": task_id is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in submit_url: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/urls", response_model=List[YouTubeURLResponse])
async def list_urls(limit: int = 50, offset: int = 0):
    """List all submitted YouTube URLs"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        urls = await db.get_youtube_urls(limit=limit, offset=offset)
        return urls
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing URLs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/urls/{url_id}", response_model=YouTubeURLResponse)
async def get_url(url_id: str):
    """Get a specific YouTube URL by ID"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        url_uuid = uuid.UUID(url_id)
        url_record = await db.get_youtube_url(url_uuid)
        if not url_record:
            raise HTTPException(status_code=404, detail="URL not found")
        return url_record
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid URL ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/urls/{url_id}/videos", response_model=List[VideoResponse])
async def get_url_videos(url_id: str):
    """Get all videos for a specific YouTube URL"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        url_uuid = uuid.UUID(url_id)
        videos = await db.get_videos_by_url(url_uuid)
        return videos
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid URL ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/jobs/{job_id}", response_model=ScrapingJobResponse)
async def get_job_status(job_id: str):
    """Get the status of a scraping job"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        job_uuid = uuid.UUID(job_id)
        job = await db.get_scraping_job(job_uuid)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/validate-url")
async def validate_url(url_data: YouTubeURLCreate):
    """Validate a YouTube URL without submitting it"""
    try:
        if not youtube_parser:
            raise HTTPException(status_code=503, detail="YouTube parser not available")
        
        url_type, identifier = parse_youtube_url(url_data.url)
        normalized_url = youtube_parser.normalize_url(url_data.url)
        
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
    except Exception as e:
        logger.error(f"Error validating URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")

@app.get("/dashboard")
async def dashboard(request: Request):
    """Dashboard page showing submitted URLs and their status"""
    try:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Template error: {str(e)}")

@app.get("/api/dashboard-data")
async def dashboard_data():
    """Get dashboard data (URLs, jobs, statistics)"""
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Get recent URLs
        urls = await db.get_youtube_urls(limit=20)
        
        # Get job statistics (simplified for now)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

# Debug endpoint to check what's wrong
@app.get("/debug")
async def debug_info():
    """Debug information endpoint"""
    debug_data = {
        "configuration": config.get_config_summary(),
        "environment_variables": {
            "SUPABASE_URL": "✅" if config.SUPABASE_URL else "❌",
            "SUPABASE_KEY": "✅" if config.SUPABASE_KEY else "❌",
            "B2_APPLICATION_KEY_ID": "✅" if config.B2_APPLICATION_KEY_ID else "❌",
            "B2_APPLICATION_KEY": "✅" if config.B2_APPLICATION_KEY else "❌",
            "B2_BUCKET_NAME": "✅" if config.B2_BUCKET_NAME else "❌",
            "B2_ENDPOINT_URL": "✅" if config.B2_ENDPOINT_URL else "❌",
            "REDIS_URL": "✅" if config.REDIS_URL else "❌",
        },
        "components": {
            "database": db is not None,
            "youtube_parser": youtube_parser is not None,
            "celery_tasks": scrape_task is not None,
        },
        "python_path": os.getcwd(),
        "template_directory_exists": os.path.exists("templates"),
        "config_source": "GitHub Secrets + Environment Variables" if not Path(".env").exists() else ".env file + Environment Variables"
    }
    
    return debug_data

@app.get("/api/queue-status")
async def queue_status():
    """Get current queue status and system load"""
    try:
        from rate_limiter import queue_manager, load_monitor
        
        # Get queue statistics
        queue_stats = await queue_manager.get_queue_stats()
        
        # Get system capacity
        can_handle, message = await load_monitor.check_system_capacity()
        
        return {
            "queue_stats": queue_stats,
            "system_capacity": {
                "can_handle_requests": can_handle,
                "message": message
            },
            "rate_limits": {
                "submit_url": "10 per minute",
                "validate_url": "30 per minute", 
                "dashboard": "60 per minute"
            }
        }
    except ImportError:
        return {"error": "Queue monitoring not available"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)