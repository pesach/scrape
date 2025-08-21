import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def _get_first_env(names, default_value=""):
    """
    Return the first non-empty environment variable from the provided list.
    """
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default_value

def _resolve_path_maybe_relative(path_str: str) -> str:
    """
    Expand user and env vars and resolve relative paths to project root.
    Return the resolved string path (even if it doesn't exist).
    """
    if not path_str:
        return ""
    expanded = os.path.expandvars(os.path.expanduser(path_str))
    p = Path(expanded)
    if not p.is_absolute():
        # Resolve relative to repo root (this file's parent directory)
        repo_root = Path(__file__).parent
        p = (repo_root / p).resolve()
    return str(p)

def load_config():
    """
    Load configuration from multiple sources in priority order:
    1. Environment variables (for production/GitHub Actions)
    2. .env file (for local development)
    3. Default values (for fallback)
    
    This allows the app to work with GitHub Repository Secrets
    without requiring a .env file in production.
    """
    
    # Try to load .env file if it exists (for local development)
    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✅ Loaded configuration from .env file")
        except ImportError:
            logger.warning("⚠️ python-dotenv not available, using environment variables only")
    else:
        logger.info("📝 No .env file found, using environment variables")

class Config:
    """
    Configuration class that handles environment variables with fallbacks
    
    Priority order:
    1. Environment variables (set by GitHub Actions, Docker, etc.)
    2. .env file values (loaded by load_config())
    3. Default values (for development)
    """
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # Backblaze B2 Configuration
    B2_APPLICATION_KEY_ID: str = os.getenv("B2_APPLICATION_KEY_ID", "")
    B2_APPLICATION_KEY: str = os.getenv("B2_APPLICATION_KEY", "")
    B2_BUCKET_NAME: str = os.getenv("B2_BUCKET_NAME", "")
    B2_ENDPOINT_URL: str = os.getenv("B2_ENDPOINT_URL", "https://s3.us-west-004.backblazeb2.com")
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Application Configuration
    DOWNLOAD_PATH: str = os.getenv("DOWNLOAD_PATH", "/tmp/youtube_downloads")
    MAX_FILE_SIZE_GB: float = float(os.getenv("MAX_FILE_SIZE_GB", "5"))
    
    # Optional: Environment detection
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # --- Scraping realism settings ---
    # Realistic browser headers
    SCRAPER_USER_AGENT: str = os.getenv(
        "SCRAPER_USER_AGENT",
        # Chrome 126 on Linux x86_64
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    )
    SCRAPER_ACCEPT_LANGUAGE: str = os.getenv("SCRAPER_ACCEPT_LANGUAGE", "en-US,en;q=0.9")

    # Cookies: provide either a cookies.txt file or a browser name for cookiesfrombrowser
    # Accept common fallback env names for convenience
    _RAW_COOKIES_FILE: str = _get_first_env([
        "YT_COOKIES_FILE",
        "COOKIES_FILE",
        "COOKIES",
        "COOKIES_TXT",
        "COOKIEFILE",
    ], "")
    YT_COOKIES_FILE: str = _resolve_path_maybe_relative(_RAW_COOKIES_FILE)  # Path to Netscape cookies.txt
    COOKIES_FROM_BROWSER: str = _get_first_env([
        "COOKIES_FROM_BROWSER",
        "COOKIES_BROWSER",
        "BROWSER_COOKIES",
    ], "")  # e.g., chrome|firefox|brave|edge

    # Pacing
    SIMULATE_WATCH_TIME: bool = os.getenv("SIMULATE_WATCH_TIME", "false").lower() in ("true", "1", "yes")
    WATCH_SPEED: float = float(os.getenv("WATCH_SPEED", "1.25"))  # 1.0 = realtime, >1 faster than realtime
    HUMAN_DELAY_MIN_SEC: float = float(os.getenv("HUMAN_DELAY_MIN_SEC", "3.0"))
    HUMAN_DELAY_MAX_SEC: float = float(os.getenv("HUMAN_DELAY_MAX_SEC", "10.0"))
    
    # Optional hard cap on download rate (bytes/sec). If set, overrides watch-time-derived rate
    DOWNLOAD_RATELIMIT_BPS: int = int(os.getenv("DOWNLOAD_RATELIMIT_BPS", "0"))
    
    # --- ScraperAPI Configuration ---
    # Enable ScraperAPI for YouTube scraping (alternative to yt-dlp)
    USE_SCRAPERAPI: bool = os.getenv("USE_SCRAPERAPI", "false").lower() in ("true", "1", "yes")
    SCRAPERAPI_KEY: str = os.getenv("SCRAPERAPI_KEY", "")
    SCRAPERAPI_ENDPOINT: str = os.getenv("SCRAPERAPI_ENDPOINT", "https://api.scraperapi.com")
    # Render JavaScript content (required for YouTube)
    SCRAPERAPI_RENDER: bool = os.getenv("SCRAPERAPI_RENDER", "true").lower() in ("true", "1", "yes")
    # Premium proxy pool for better success rates
    SCRAPERAPI_PREMIUM: bool = os.getenv("SCRAPERAPI_PREMIUM", "false").lower() in ("true", "1", "yes")
    # Retry failed requests
    SCRAPERAPI_RETRY_FAILED: bool = os.getenv("SCRAPERAPI_RETRY_FAILED", "true").lower() in ("true", "1", "yes")
    # Timeout for ScraperAPI requests (seconds)
    SCRAPERAPI_TIMEOUT: int = int(os.getenv("SCRAPERAPI_TIMEOUT", "60"))

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate that all required configuration is present
        
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        required_vars = {
            "SUPABASE_URL": cls.SUPABASE_URL,
            "SUPABASE_KEY": cls.SUPABASE_KEY,
            "B2_APPLICATION_KEY_ID": cls.B2_APPLICATION_KEY_ID,
            "B2_APPLICATION_KEY": cls.B2_APPLICATION_KEY,
            "B2_BUCKET_NAME": cls.B2_BUCKET_NAME,
        }
        
        # Add ScraperAPI key to required if enabled
        if cls.USE_SCRAPERAPI:
            required_vars["SCRAPERAPI_KEY"] = cls.SCRAPERAPI_KEY
        
        missing = [name for name, value in required_vars.items() if not value]
        
        if missing:
            logger.error(f"❌ Missing required configuration: {', '.join(missing)}")
            return False, missing
        else:
            logger.info("✅ All required configuration present")
            return True, []
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Get a summary of current configuration (without sensitive values)"""
        return {
            "supabase_configured": bool(cls.SUPABASE_URL and cls.SUPABASE_KEY),
            "b2_configured": bool(cls.B2_APPLICATION_KEY_ID and cls.B2_APPLICATION_KEY and cls.B2_BUCKET_NAME),
            "redis_url": cls.REDIS_URL,
            "download_path": cls.DOWNLOAD_PATH,
            "max_file_size_gb": cls.MAX_FILE_SIZE_GB,
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG,
            # Non-sensitive scraper settings
            "simulate_watch_time": cls.SIMULATE_WATCH_TIME,
            "watch_speed": cls.WATCH_SPEED,
            "cookies_file_set": bool(cls.YT_COOKIES_FILE),
            "cookies_from_browser": cls.COOKIES_FROM_BROWSER or None,
            # ScraperAPI settings
            "use_scraperapi": cls.USE_SCRAPERAPI,
            "scraperapi_configured": bool(cls.SCRAPERAPI_KEY),
            "scraperapi_premium": cls.SCRAPERAPI_PREMIUM,
        }

# Initialize configuration on import
load_config()

# Create global config instance
config = Config()

# Validate configuration on startup
is_valid, missing = config.validate()
if not is_valid:
    logger.warning(f"⚠️ Configuration validation failed. Missing: {', '.join(missing)}")
    if config.ENVIRONMENT == "production":
        raise ValueError(f"Missing required configuration in production: {', '.join(missing)}")
else:
    logger.info("🎉 Configuration loaded successfully")

# Log cookies configuration clarity at startup
try:
    if config.YT_COOKIES_FILE:
        cookies_path = Path(config.YT_COOKIES_FILE)
        if cookies_path.exists():
            logger.info(f"🍪 Using cookies file at: {cookies_path}")
        else:
            logger.warning(f"🍪 Cookies file is set but was not found: {cookies_path}")
    elif config.COOKIES_FROM_BROWSER:
        logger.info(f"🍪 Using cookies from browser: {config.COOKIES_FROM_BROWSER}")
    else:
        logger.info("🍪 No cookies configuration provided. Proceeding without cookies.")
except Exception:
    # Avoid breaking startup due to logging issues
    pass