#!/usr/bin/env python3
"""
Celery worker startup script for YouTube Video Scraper
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables FIRST (same as test_setup.py)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

# Load configuration (handles both .env and GitHub secrets)
from config import config

# Setup logging
from logging_config import setup_logging
setup_logging()

import logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Check Redis connection
    redis_url = config.REDIS_URL
    
    try:
        import redis
        r = redis.from_url(redis_url)
        r.ping()
        logger.info(f"✅ Connected to Redis at {redis_url}")
    except Exception as e:
        logger.error(f"❌ Cannot connect to Redis at {redis_url}: {str(e)}")
        print(f"❌ Cannot connect to Redis at {redis_url}")
        print("Please ensure Redis is running and accessible.")
        sys.exit(1)
    
    print("🔧 Starting Celery worker for YouTube Video Scraper...")
    print("📊 Monitor tasks at: http://localhost:5555 (if flower is installed)")
    
    # Import celery app
    from celery_app import celery_app
    
    # Start worker
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',  # Limit concurrent downloads
        '--queues=default,scraping'
    ])