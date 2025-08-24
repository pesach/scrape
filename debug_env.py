#!/usr/bin/env python3
"""
Environment Variables Debug Script
=================================

This script helps debug why environment variables work in one context but not another.
"""

import os
import sys
from pathlib import Path

print("🔍 Environment Variables Debug")
print("=" * 40)

# Check current working directory
print(f"📁 Current directory: {os.getcwd()}")
print(f"📄 Script location: {Path(__file__).parent}")

# Check if .env file exists
env_file = Path(".env")
print(f"📝 .env file exists: {env_file.exists()}")
if env_file.exists():
    print(f"📍 .env file location: {env_file.absolute()}")

# Check if python-dotenv is available
try:
    from dotenv import load_dotenv
    print("✅ python-dotenv is available")
    
    # Try loading .env file
    if env_file.exists():
        load_dotenv()
        print("✅ .env file loaded")
    else:
        print("⚠️  No .env file to load")
        
except ImportError:
    print("❌ python-dotenv NOT available")
    print("   Install with: pip install python-dotenv")

print("\n🔍 Environment Variables Check:")
print("-" * 40)

# Check key environment variables
env_vars = [
    "SUPABASE_URL",
    "SUPABASE_KEY", 
    "B2_APPLICATION_KEY_ID",
    "B2_APPLICATION_KEY",
    "B2_BUCKET_NAME",
    "B2_ENDPOINT_URL",
    "REDIS_URL"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Show first/last few characters for security
        if len(value) > 20:
            display_value = f"{value[:10]}...{value[-5:]}"
        else:
            display_value = f"{value[:5]}..."
        print(f"  ✅ {var}: {display_value}")
    else:
        print(f"  ❌ {var}: Not set")

print("\n🧪 Testing Config Module:")
print("-" * 40)

try:
    # Add current directory to path (same as start_worker.py)
    sys.path.insert(0, str(Path(__file__).parent))
    
    from config import config
    print("✅ Config module imported successfully")
    
    # Test specific config values
    config_vars = [
        ("SUPABASE_URL", config.SUPABASE_URL),
        ("SUPABASE_KEY", config.SUPABASE_KEY),
        ("REDIS_URL", config.REDIS_URL),
        ("B2_BUCKET_NAME", config.B2_BUCKET_NAME)
    ]
    
    for name, value in config_vars:
        if value:
            if len(value) > 20:
                display_value = f"{value[:10]}...{value[-5:]}"
            else:
                display_value = f"{value[:5]}..."
            print(f"  ✅ config.{name}: {display_value}")
        else:
            print(f"  ❌ config.{name}: Empty/None")
            
except Exception as e:
    print(f"❌ Config module error: {str(e)}")

print("\n🔍 Celery Worker Environment Check:")
print("-" * 40)

try:
    # Test Redis connection (same as start_worker.py)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"📡 Redis URL: {redis_url}")
    
    import redis
    r = redis.from_url(redis_url)
    r.ping()
    print("✅ Redis connection successful")
    
except Exception as e:
    print(f"❌ Redis connection failed: {str(e)}")

print("\n💡 Recommendations:")
print("-" * 40)

# Check if we're missing python-dotenv
try:
    import dotenv
    dotenv_available = True
except ImportError:
    dotenv_available = False

if not dotenv_available:
    print("🔧 Install python-dotenv:")
    print("   pip install python-dotenv")

if not env_file.exists():
    print("🔧 Create .env file:")
    print("   cp .env.example .env")
    print("   nano .env  # Add your actual values")

# Check if any environment variables are set
any_env_set = any(os.getenv(var) for var in env_vars)
if not any_env_set:
    print("🔧 No environment variables found!")
    print("   Either:")
    print("   1. Create .env file with your values")
    print("   2. Set environment variables manually")
    print("   3. Export variables in current shell")

print("\n🚀 Quick Fix Commands:")
print("-" * 40)
print("# If using .env file:")
print("export $(cat .env | xargs)")
print("")
print("# If setting manually:")
print("export SUPABASE_URL='your_url_here'")
print("export SUPABASE_KEY='your_key_here'")
print("# ... etc")
print("")
print("# Then try start_worker again:")
print("python start_worker.py")