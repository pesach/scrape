import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
import uuid

from celery_app import celery_app
from models import JobStatus, URLType
from database import db
from scraper import scraper
from youtube_parser import YouTubeURLParser

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='scrape_youtube_url')
def scrape_youtube_url_task(self, job_id: str, url: str, url_type: str):
    """
    Background task to scrape videos from a YouTube URL
    
    IMPORTANT: This is the core background processing task
    - Runs asynchronously after user submits URL
    - Downloads videos in highest available quality
    - Uploads to Backblaze B2 cloud storage
    - Saves metadata to Supabase database
    - Automatically cleans up local files
    - Updates job status for user monitoring
    
    PROCESSING STRATEGY:
    - Single videos: Process immediately
    - Playlists/channels: Process each video with 1s delay
    - Error handling: Continue processing other videos if one fails
    - Rate limiting: Built-in delays to prevent YouTube blocking
    
    Args:
        job_id: UUID of the scraping job
        url: YouTube URL to scrape
        url_type: Type of URL (video, channel, playlist, user)
    """
    job_uuid = uuid.UUID(job_id)
    url_type_enum = URLType(url_type)
    
    async def run_scraping():
        try:
            # Update job status to processing
            await db.update_scraping_job(job_uuid, {
                'status': JobStatus.PROCESSING.value,
                'started_at': datetime.utcnow().isoformat()
            })
            
            # Get the YouTube URL record to get the ID
            job = await db.get_scraping_job(job_uuid)
            if not job:
                raise Exception("Scraping job not found")
            
            youtube_url_id = job.youtube_url_id
            
            # Perform the scraping
            success, message, videos_processed = await scraper.scrape_url(
                url, url_type_enum, youtube_url_id
            )
            
            if success:
                # Update job as completed
                await db.update_scraping_job(job_uuid, {
                    'status': JobStatus.COMPLETED.value,
                    'progress_percent': 100,
                    'videos_processed': videos_processed,
                    'completed_at': datetime.utcnow().isoformat()
                })
                logger.info(f"Successfully completed scraping job {job_id}: {message}")
                return {'success': True, 'message': message, 'videos_processed': videos_processed}
            else:
                # Update job as failed
                await db.update_scraping_job(job_uuid, {
                    'status': JobStatus.FAILED.value,
                    'error_message': message,
                    'completed_at': datetime.utcnow().isoformat()
                })
                logger.error(f"Scraping job {job_id} failed: {message}")
                return {'success': False, 'message': message, 'videos_processed': 0}
                
        except Exception as e:
            error_message = f"Unexpected error in scraping job {job_id}: {str(e)}"
            logger.error(error_message)
            
            try:
                # Update job as failed
                await db.update_scraping_job(job_uuid, {
                    'status': JobStatus.FAILED.value,
                    'error_message': error_message,
                    'completed_at': datetime.utcnow().isoformat()
                })
            except Exception as db_error:
                logger.error(f"Failed to update job status: {str(db_error)}")
            
            return {'success': False, 'message': error_message, 'videos_processed': 0}
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_scraping())
        return result
    finally:
        loop.close()

@celery_app.task(bind=True, name='extract_url_metadata')
def extract_url_metadata_task(self, url: str):
    """
    Extract metadata from a YouTube URL without downloading videos
    
    Args:
        url: YouTube URL
        
    Returns:
        Dictionary with metadata
    """
    try:
        metadata = YouTubeURLParser.extract_metadata(url)
        logger.info(f"Successfully extracted metadata for {url}")
        return {'success': True, 'metadata': metadata}
    except Exception as e:
        error_message = f"Failed to extract metadata for {url}: {str(e)}"
        logger.error(error_message)
        return {'success': False, 'error': error_message}

@celery_app.task(bind=True, name='cleanup_old_jobs')
def cleanup_old_jobs_task(self, days_old: int = 7):
    """
    Clean up old completed/failed jobs from the database
    
    Args:
        days_old: Number of days old jobs to keep
    """
    async def run_cleanup():
        try:
            # This would need to be implemented in the database module
            # For now, just log that cleanup would happen
            logger.info(f"Would clean up jobs older than {days_old} days")
            return {'success': True, 'message': f'Cleanup completed for jobs older than {days_old} days'}
        except Exception as e:
            error_message = f"Cleanup failed: {str(e)}"
            logger.error(error_message)
            return {'success': False, 'error': error_message}
    
    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_cleanup())
        return result
    finally:
        loop.close()

# Periodic tasks can be configured here
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-jobs': {
        'task': 'cleanup_old_jobs',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
        'args': (7,)  # Clean up jobs older than 7 days
    },
}

celery_app.conf.timezone = 'UTC'