import os
from celery import Celery
from kombu import Queue

# Load environment variables FIRST (same as test_setup.py)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Fail silently for Celery worker

# Create Celery instance
celery_app = Celery('youtube_scraper')

# Load configuration
from config import config

# Configuration
celery_app.conf.update(
    # Broker settings
    broker_url=config.REDIS_URL,
    result_backend=config.REDIS_URL,
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        'scrape_youtube_url': {'queue': 'scraping'},
        'process_single_video': {'queue': 'scraping'},
    },
    
    # Queue definitions
    task_default_queue='default',
    task_queues=(
        Queue('default'),
        Queue('scraping', routing_key='scraping'),
    ),
    
    # Task time limits
    task_soft_time_limit=3600,  # 1 hour soft limit
    task_time_limit=7200,       # 2 hour hard limit
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
)