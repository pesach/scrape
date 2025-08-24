#!/usr/bin/env python3
"""
Environment Configuration Checker for YouTube Scraper
This script checks if the application can access required credentials
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if we're running in GitHub Actions or local environment"""
    
    print("=" * 60)
    print("🔍 YouTube Scraper - Environment Configuration Check")
    print("=" * 60)
    
    # Check if we're in GitHub Actions
    is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
    is_codespace = os.getenv("CODESPACES") == "true"
    
    print("\n📍 Current Environment:")
    if is_github_actions:
        print("  ✅ Running in GitHub Actions")
        print("  → GitHub Secrets should be available as environment variables")
    elif is_codespace:
        print("  🔧 Running in GitHub Codespace")
        print("  → GitHub Secrets may be available if configured")
    else:
        print("  💻 Running in Local/Development Environment")
        print("  → GitHub Secrets are NOT available")
        print("  → You need to set environment variables manually")
    
    print(f"\n📂 Working Directory: {os.getcwd()}")
    
    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        print(f"  ✅ .env file found at: {env_file.absolute()}")
    else:
        print("  ℹ️ No .env file found (using environment variables only)")
    
    # Check required environment variables
    print("\n🔐 Required Environment Variables:")
    
    required_vars = {
        "SUPABASE_URL": "Supabase project URL",
        "SUPABASE_KEY": "Supabase anonymous key",
        "B2_APPLICATION_KEY_ID": "Backblaze B2 key ID",
        "B2_APPLICATION_KEY": "Backblaze B2 application key",
        "B2_BUCKET_NAME": "Backblaze B2 bucket name",
        "B2_ENDPOINT_URL": "Backblaze B2 endpoint URL",
        "REDIS_URL": "Redis connection URL"
    }
    
    all_set = True
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            # Check if it's a placeholder
            if "your-" in value.lower() or "your_" in value.lower() or value == "":
                print(f"  ⚠️ {var_name}: Set but appears to be a placeholder")
                all_set = False
            else:
                # Show partial value for debugging
                if var_name in ["SUPABASE_URL", "B2_ENDPOINT_URL", "REDIS_URL"]:
                    print(f"  ✅ {var_name}: {value[:30]}...")
                else:
                    print(f"  ✅ {var_name}: Set (hidden for security)")
        else:
            print(f"  ❌ {var_name}: Not set - {description}")
            all_set = False
    
    # Provide guidance based on environment
    print("\n" + "=" * 60)
    print("📋 Next Steps:")
    print("=" * 60)
    
    if is_github_actions:
        if all_set:
            print("✅ All environment variables are set!")
            print("The application should work correctly.")
        else:
            print("⚠️ Some environment variables are missing or invalid.")
            print("\nTo fix this:")
            print("1. Go to your GitHub repository")
            print("2. Navigate to Settings → Secrets and variables → Actions")
            print("3. Add the missing Repository Secrets")
            print("4. Re-run the GitHub Action")
    else:
        print("\n🚨 You're not in GitHub Actions, so GitHub Secrets are not available.")
        print("\nYou have three options:\n")
        
        print("Option 1: Create a .env file (Recommended for local development)")
        print("-" * 40)
        print("Create a .env file with your actual credentials:")
        print("""
cat > .env << 'EOF'
SUPABASE_URL=https://your-actual-project.supabase.co
SUPABASE_KEY=your-actual-anon-key
B2_APPLICATION_KEY_ID=your-actual-key-id
B2_APPLICATION_KEY=your-actual-key
B2_BUCKET_NAME=your-actual-bucket
B2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
REDIS_URL=redis://localhost:6379/0
EOF
""")
        
        print("\nOption 2: Export environment variables in your shell")
        print("-" * 40)
        print("Run these commands (replace with actual values):")
        print("""
export SUPABASE_URL="https://your-actual-project.supabase.co"
export SUPABASE_KEY="your-actual-anon-key"
export B2_APPLICATION_KEY_ID="your-actual-key-id"
export B2_APPLICATION_KEY="your-actual-key"
export B2_BUCKET_NAME="your-actual-bucket"
export B2_ENDPOINT_URL="https://s3.us-west-004.backblazeb2.com"
export REDIS_URL="redis://localhost:6379/0"
""")
        
        print("\nOption 3: Run in GitHub Actions")
        print("-" * 40)
        print("1. Push your code to GitHub")
        print("2. Set up Repository Secrets in GitHub Settings")
        print("3. Run the GitHub Actions workflow")
        print("4. The secrets will be automatically available there")
    
    print("\n" + "=" * 60)
    print("📚 Documentation:")
    print("  - Setting up credentials: SETUP_CREDENTIALS.md")
    print("  - GitHub Secrets guide: GITHUB_SECRETS_TROUBLESHOOTING.md")
    print("=" * 60)
    
    return all_set

if __name__ == "__main__":
    all_configured = check_environment()
    sys.exit(0 if all_configured else 1)