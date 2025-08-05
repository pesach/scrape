import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging():
    """Configure logging for the application"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler with rotation
            logging.handlers.RotatingFileHandler(
                log_dir / "youtube_scraper.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Configure specific loggers
    loggers = {
        'youtube_scraper': logging.INFO,
        'yt_dlp': logging.WARNING,  # Reduce yt-dlp verbosity
        'boto3': logging.WARNING,   # Reduce boto3 verbosity
        'botocore': logging.WARNING,
        'supabase': logging.INFO,
        'celery': logging.INFO,
        'uvicorn': logging.INFO,
    }
    
    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Create separate error log
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    # Add error handler to root logger
    logging.getLogger().addHandler(error_handler)
    
    logging.info("Logging configured successfully")

if __name__ == "__main__":
    setup_logging()