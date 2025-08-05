#!/usr/bin/env python3
"""
Main application runner for YouTube Video Scraper
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup logging first
from logging_config import setup_logging
setup_logging()

# Now import and run the main application
from main import app
import uvicorn

if __name__ == "__main__":
    # Check required environment variables
    required_vars = [
        "SUPABASE_URL", "SUPABASE_KEY",
        "B2_APPLICATION_KEY_ID", "B2_APPLICATION_KEY", 
        "B2_BUCKET_NAME", "B2_ENDPOINT_URL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please copy .env.example to .env and configure the required variables.")
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