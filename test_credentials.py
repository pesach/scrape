#!/usr/bin/env python3
"""
Test script to verify your credentials are working correctly.
Run this after setting up your .env file.
"""

import sys
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase():
    """Test Supabase connection"""
    print("🔍 Testing Supabase connection...")
    try:
        from database import Database
        db = Database()
        # Try a simple operation
        result = db.supabase.table('youtube_urls').select('*').limit(1).execute()
        print("✅ Supabase connection successful!")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {str(e)}")
        if "Invalid API key" in str(e):
            print("   💡 Check your SUPABASE_KEY - use the 'anon public' key, not secret!")
        elif "not found" in str(e).lower():
            print("   💡 Check your SUPABASE_URL - should end with .supabase.co")
        return False

def test_b2_storage():
    """Test Backblaze B2 connection"""
    print("\n☁️ Testing Backblaze B2 connection...")
    try:
        from storage import BackblazeB2Storage
        storage = BackblazeB2Storage()
        # Try to list objects (this tests credentials)
        storage.client.list_objects_v2(Bucket=storage.bucket_name, MaxKeys=1)
        print("✅ Backblaze B2 connection successful!")
        return True
    except Exception as e:
        print(f"❌ Backblaze B2 connection failed: {str(e)}")
        if "InvalidAccessKeyId" in str(e):
            print("   💡 Check your B2_APPLICATION_KEY_ID")
        elif "SignatureDoesNotMatch" in str(e):
            print("   💡 Check your B2_APPLICATION_KEY")
        elif "NoSuchBucket" in str(e):
            print("   💡 Check your B2_BUCKET_NAME - does the bucket exist?")
        return False

def test_redis():
    """Test Redis connection"""
    print("\n⚡ Testing Redis connection...")
    try:
        import redis
        from config import config
        r = redis.from_url(config.REDIS_URL)
        r.ping()
        print("✅ Redis connection successful!")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {str(e)}")
        if "Connection refused" in str(e):
            print("   💡 Redis server not running. Start it with: redis-server --daemonize yes")
        return False

def test_youtube_parser():
    """Test YouTube URL parsing"""
    print("\n🎥 Testing YouTube parser...")
    try:
        from youtube_parser import YouTubeURLParser
        parser = YouTubeURLParser()
        
        # Test with a known video
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = parser.extract_metadata(test_url)
        
        if result and result.get('title'):
            print(f"✅ YouTube parser working! Found: {result['title'][:50]}...")
            return True
        else:
            print("❌ YouTube parser returned no results")
            return False
    except Exception as e:
        print(f"❌ YouTube parser failed: {str(e)}")
        if "yt-dlp" in str(e).lower():
            print("   💡 Install yt-dlp: pip install yt-dlp")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing YouTube Video Scraper Credentials")
    print("=" * 50)
    
    # Test environment loading first
    try:
        from config import config
        print(f"📁 Config loaded from: {config.__class__.__module__}")
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return
    
    # Run all tests
    results = []
    results.append(("Supabase", test_supabase()))
    results.append(("Backblaze B2", test_b2_storage()))
    results.append(("Redis", test_redis()))
    results.append(("YouTube Parser", test_youtube_parser()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Your setup is ready!")
        print("\nNext steps:")
        print("1. python3 run.py        # Start web server")
        print("2. python3 start_worker.py # Start background worker")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nFor help, check:")
        print("- SETUP_CREDENTIALS.md")
        print("- python3 debug_env.py")

if __name__ == "__main__":
    main()