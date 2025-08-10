import logging
import logging.handlers
import os
from pathlib import Path
import contextvars

# Context variable to hold request/task correlation IDs across the app
request_id_ctx_var = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects request_id from contextvars into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = request_id_ctx_var.get()
        except Exception:
            record.request_id = "-"
        return True


def setup_logging():
    """Configure logging for the application with structured, detailed error logs."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Common format including rich context
    common_format = (
        "%(asctime)s | %(levelname)s | %(name)s | req_id=%(request_id)s | "
        "%(process)d/%(threadName)s | %(filename)s:%(lineno)d %(funcName)s | %(message)s"
    )
    common_formatter = logging.Formatter(common_format)

    # Root logger baseline
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Ensure handlers are not duplicated on repeated setup
    if getattr(root_logger, "_youtube_logging_configured", False):
        return

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(common_formatter)
    console_handler.addFilter(RequestIdFilter())

    # Rotating file handler for general logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "youtube_scraper.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(common_formatter)
    file_handler.addFilter(RequestIdFilter())

    # Separate error log (brief)
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(common_formatter)
    error_handler.addFilter(RequestIdFilter())

    # Highly detailed error log: stack traces will be included when exc_info is set
    detailed_error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors_detailed.log",
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=5,
        encoding="utf-8",
    )
    detailed_error_handler.setLevel(logging.ERROR)
    detailed_error_handler.setFormatter(common_formatter)
    detailed_error_handler.addFilter(RequestIdFilter())

    # Attach handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(detailed_error_handler)

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
        logger.addFilter(RequestIdFilter())

    logging.info("Logging configured successfully")

    # Marker to prevent duplicate configuration
    setattr(root_logger, "_youtube_logging_configured", True)


if __name__ == "__main__":
    setup_logging()