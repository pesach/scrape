#!/usr/bin/env python3
"""
Setup verification script for YouTube Video Scraper
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_imports():
    """Test all required imports"""
    print("🔍 Testing imports...")
    
    try:
        import yt_dlp
        print("  ✅ yt-dlp")
    except ImportError:
        print("  ❌ yt-dlp - run: pip install yt-dlp")
        return False
    
    try:
        import fastapi
        print("  ✅ FastAPI")
    except ImportError:
        print("  ❌ FastAPI - run: pip install fastapi")
        return False
    
    try:
        import celery
        print("  ✅ Celery")
    except ImportError:
        print("  ❌ Celery - run: pip install celery")
        return False
    
    try:
        import supabase
        print("  ✅ Supabase")
    except ImportError:
        print("  ❌ Supabase - run: pip install supabase")
        return False
    
    try:
        import boto3
        print("  ✅ Boto3")
    except ImportError:
        print("  ❌ Boto3 - run: pip install boto3")
        return False
    
    try:
        import redis
        print("  ✅ Redis")
    except ImportError:
        print("  ❌ Redis - run: pip install redis")
        return False
    
    return True

def test_environment():
    """Test environment variables"""
    print("\n🔧 Testing environment variables...")
    
    required_vars = {
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_KEY": "Supabase anon key",
        "B2_APPLICATION_KEY_ID": "Backblaze B2 key ID",
        "B2_APPLICATION_KEY": "Backblaze B2 application key",
        "B2_BUCKET_NAME": "Backblaze B2 bucket name",
        "B2_ENDPOINT_URL": "Backblaze B2 endpoint URL"
    }
    
    all_set = True
    for var, description in required_vars.items():
        if os.getenv(var):
            print(f"  ✅ {var}")
        else:
            print(f"  ❌ {var} - {description}")
            all_set = False
    
    return all_set

def test_redis_connection():
    """Test Redis connection"""
    print("\n🔌 Testing Redis connection...")
    
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        print(f"  ✅ Connected to Redis at {redis_url}")
        return True
    except Exception as e:
        print(f"  ❌ Redis connection failed: {str(e)}")
        return False

def test_ffmpeg():
    """Test FFmpeg availability"""
    print("\n🎬 Testing FFmpeg...")
    
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("  ✅ FFmpeg is available")
            return True
        else:
            print("  ❌ FFmpeg not working properly")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  ❌ FFmpeg not found - please install FFmpeg")
        return False

def test_youtube_parser():
    """Test YouTube URL parsing"""
    print("\n🔗 Testing YouTube URL parsing...")
    
    try:
        from youtube_parser import parse_youtube_url
        
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/channel/UCefarW8iWzuNO7NedV-om-w",
            "https://www.youtube.com/@username",
            "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy8VbX6gf_1bSC6WcqDi8Wq"
        ]
        
        for url in test_urls:
            try:
                url_type, identifier = parse_youtube_url(url)
                print(f"  ✅ {url_type.value}: {url}")
            except Exception as e:
                print(f"  ❌ Failed to parse {url}: {str(e)}")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ YouTube parser test failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🧪 YouTube Video Scraper - Setup Verification\n")
    
    tests = [
        ("Imports", test_imports),
        ("Environment Variables", test_environment),
        ("Redis Connection", test_redis_connection),
        ("FFmpeg", test_ffmpeg),
        ("YouTube Parser", test_youtube_parser),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_func():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Run the web app: python run.py")
        print("2. Start worker: python start_worker.py")
        print("3. Visit: http://localhost:8000")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()