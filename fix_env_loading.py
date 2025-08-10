#!/usr/bin/env python3
"""
Quick Fix for Environment Loading Issues
=======================================

This script fixes common issues where test_setup.py finds environment variables
but start_worker.py doesn't.
"""

import os
import sys
from pathlib import Path

def main():
    print("🔧 Environment Loading Quick Fix")
    print("=" * 40)
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ No .env file found!")
        print("\n🔧 Creating .env file from template...")
        
        example_file = Path(".env.example")
        if example_file.exists():
            # Copy example file
            with open(example_file, 'r') as f:
                content = f.read()
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("✅ Created .env file from .env.example")
            print("📝 Now edit .env with your actual values:")
            print(f"   nano {env_file}")
            return
        else:
            print("❌ No .env.example file found!")
            return
    
    print("✅ .env file exists")
    
    # Check if python-dotenv is installed
    try:
        import dotenv
        print("✅ python-dotenv is available")
    except ImportError:
        print("❌ python-dotenv not installed!")
        print("\n🔧 Installing python-dotenv...")
        
        try:
            import subprocess
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'python-dotenv'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ python-dotenv installed successfully")
            else:
                print(f"❌ Installation failed: {result.stderr}")
                return
        except Exception as e:
            print(f"❌ Installation error: {e}")
            return
    
    # Load and test environment variables
    print("\n🔍 Loading .env file...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env file loaded")
        
        # Check key variables
        required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "REDIS_URL"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing variables in .env: {missing_vars}")
            print("📝 Edit your .env file to add these values")
        else:
            print("✅ All required variables found")
            
    except Exception as e:
        print(f"❌ Error loading .env: {e}")
        return
    
    print("\n🧪 Testing config module...")
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        from config import config
        if config.SUPABASE_URL and config.REDIS_URL:
            print("✅ Config module working correctly")
            print("\n🎉 Environment loading should now work!")
            print("\n🚀 Try running start_worker.py again:")
            print("   python start_worker.py")
        else:
            print("❌ Config module not loading variables properly")
            print("💡 Try manually exporting variables:")
            print("   export $(cat .env | xargs)")
            print("   python start_worker.py")
            
    except Exception as e:
        print(f"❌ Config module error: {e}")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    main()