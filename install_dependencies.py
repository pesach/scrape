#!/usr/bin/env python3
"""
Smart Dependency Installer for YouTube Video Scraper
===================================================

This script automatically handles psycopg2-binary installation issues
by trying multiple approaches and falling back to alternatives.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success!")
            return True
        else:
            print(f"❌ {description} - Failed:")
            print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception: {str(e)}")
        return False

def install_dependencies():
    """Smart dependency installation with fallbacks"""
    print("🚀 YouTube Video Scraper - Smart Dependency Installer")
    print("=" * 55)
    
    # Check if we're in the right directory
    if not os.path.exists('requirements.txt'):
        print("❌ Error: requirements.txt not found!")
        print("   Make sure you're in the project directory")
        return False
    
    # Method 1: Try standard requirements first
    print("\n📦 Method 1: Trying standard requirements.txt...")
    if run_command("pip install -r requirements.txt", "Installing all dependencies"):
        print("\n🎉 All dependencies installed successfully!")
        return True
    
    # Method 2: Try without PostgreSQL dependencies
    print("\n📦 Method 2: Trying without PostgreSQL dependencies...")
    if os.path.exists('requirements-no-postgres.txt'):
        if run_command("pip install -r requirements-no-postgres.txt", "Installing dependencies (no PostgreSQL)"):
            print("\n🎉 Dependencies installed successfully (without psycopg2-binary)!")
            print("ℹ️  Note: This is fine! Supabase uses HTTP API, not direct PostgreSQL connections.")
            return True
    
    # Method 3: Try installing system dependencies first
    print("\n📦 Method 3: Trying to install system dependencies...")
    
    # Detect OS and install system dependencies
    import platform
    system = platform.system().lower()
    
    if system == "linux":
        print("🐧 Detected Linux - installing system dependencies...")
        if run_command("sudo apt-get update && sudo apt-get install -y python3-dev libpq-dev build-essential", 
                      "Installing Linux system dependencies"):
            if run_command("pip install -r requirements.txt", "Retrying pip install"):
                print("\n🎉 Dependencies installed after system package installation!")
                return True
    
    elif system == "darwin":  # macOS
        print("🍎 Detected macOS - installing system dependencies...")
        if run_command("brew install postgresql", "Installing PostgreSQL via Homebrew"):
            if run_command("pip install -r requirements.txt", "Retrying pip install"):
                print("\n🎉 Dependencies installed after Homebrew installation!")
                return True
    
    # Method 4: Try individual package installation
    print("\n📦 Method 4: Trying individual package installation...")
    
    essential_packages = [
        "fastapi==0.104.1",
        "uvicorn==0.24.0", 
        "yt-dlp==2023.12.30",
        "supabase==2.3.0",
        "boto3==1.34.0",
        "celery==5.3.4",
        "redis==5.0.1",
        "pydantic==2.5.0",
        "python-multipart==0.0.6",
        "jinja2==3.1.2",
        "aiofiles==23.2.0",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "sqlalchemy==2.0.23",
        "flask==3.0.0"
    ]
    
    failed_packages = []
    for package in essential_packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            failed_packages.append(package)
    
    if not failed_packages:
        print("\n🎉 All essential packages installed individually!")
        return True
    
    # Final fallback suggestion
    print(f"\n⚠️  Some packages failed to install: {failed_packages}")
    print("\n🐳 Recommended Solution: Use Docker")
    print("   This avoids all dependency issues:")
    print("   1. Install Docker")
    print("   2. Run: docker-compose up --build")
    print("\n📖 For more solutions, see: INSTALLATION_TROUBLESHOOTING.md")
    
    return False

def main():
    """Main installation function"""
    success = install_dependencies()
    
    if success:
        print("\n" + "=" * 55)
        print("✅ Installation completed successfully!")
        print("\n🧪 Next steps:")
        print("   1. Configure your environment variables")
        print("   2. Run: python test_setup.py")
        print("   3. Start: python run.py")
        print("\n📖 See README.md for full setup instructions")
    else:
        print("\n" + "=" * 55)
        print("❌ Installation failed!")
        print("\n🛠️  Try these alternatives:")
        print("   • Use Docker: docker-compose up --build")
        print("   • See INSTALLATION_TROUBLESHOOTING.md")
        print("   • Use requirements-no-postgres.txt")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())