#!/usr/bin/env python3
"""
Main application runner for YouTube Video Scraper
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

# Setup logging first
from logging_config import setup_logging
setup_logging()
from logging_config import request_id_ctx_var

# Now import and run the main application
from main import app
import uvicorn

if __name__ == "__main__":
    # Check required configuration
    is_valid, missing_vars = config.validate()
    if not is_valid:
        print(f"❌ Missing required configuration: {', '.join(missing_vars)}")
        print("Please configure via GitHub Repository Secrets or .env file:")
        print("GitHub: Repository → Settings → Secrets and variables → Actions")
        print("Local: Copy .env.example to .env and configure")
        sys.exit(1)
    
    print("🚀 Starting YouTube Video Scraper...")
    print("📱 Web interface: http://localhost:8000")
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("📖 API docs: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info"
    )