import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

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