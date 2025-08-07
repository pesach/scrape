#!/usr/bin/env python3
"""
Verify GitHub Secrets Configuration
This script helps you verify that your secrets are configured correctly
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_github_secrets_format():
    """Check if the required secrets are in the expected format"""
    print("🔍 Checking GitHub Secrets Format...\n")
    
    # Expected secret names and their descriptions
    expected_secrets = {
        "SUPABASE_URL": {
            "description": "Supabase project URL",
            "example": "https://your-project.supabase.co",
            "validation": lambda x: x.startswith("https://") and ".supabase.co" in x
        },
        "SUPABASE_KEY": {
            "description": "Supabase anon/public key",
            "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "validation": lambda x: x.startswith("eyJ") and len(x) > 100
        },
        "B2_APPLICATION_KEY_ID": {
            "description": "Backblaze B2 application key ID",
            "example": "005a1b2c3d4e5f6789abcdef",
            "validation": lambda x: len(x) >= 20
        },
        "B2_APPLICATION_KEY": {
            "description": "Backblaze B2 application key",
            "example": "K005abcdef1234567890...",
            "validation": lambda x: len(x) >= 30
        },
        "B2_BUCKET_NAME": {
            "description": "Backblaze B2 bucket name",
            "example": "my-youtube-videos",
            "validation": lambda x: len(x) >= 3 and x.replace("-", "").replace("_", "").isalnum()
        },
        "B2_ENDPOINT_URL": {
            "description": "Backblaze B2 endpoint URL",
            "example": "https://s3.us-west-004.backblazeb2.com",
            "validation": lambda x: x.startswith("https://") and "backblazeb2.com" in x
        }
    }
    
    print("📋 Required GitHub Repository Secrets:")
    print("=" * 50)
    
    for secret_name, info in expected_secrets.items():
        print(f"\n🔑 {secret_name}")
        print(f"   Description: {info['description']}")
        print(f"   Example: {info['example']}")
        
        # Check if you have this in your environment (for testing)
        value = os.getenv(secret_name, "")
        if value:
            is_valid = info['validation'](value)
            status = "✅ Valid format" if is_valid else "⚠️ Check format"
            print(f"   Status: {status}")
        else:
            print(f"   Status: ⚪ Not set locally (expected in GitHub)")
    
    print("\n" + "=" * 50)
    return expected_secrets

def verify_local_config():
    """Verify configuration if running locally with secrets"""
    print("\n🧪 Testing Local Configuration (if secrets are set)...\n")
    
    try:
        from config import config
        
        print("📊 Configuration Summary:")
        summary = config.get_config_summary()
        for key, value in summary.items():
            print(f"   {key}: {value}")
        
        print("\n🔍 Validation Results:")
        is_valid, missing = config.validate()
        
        if is_valid:
            print("✅ All required configuration present!")
            
            # Test components
            try:
                from database import db
                print("✅ Database client initialized")
            except Exception as e:
                print(f"⚠️ Database client issue: {str(e)}")
            
            try:
                from storage import storage
                print("✅ Backblaze B2 client initialized")
            except Exception as e:
                print(f"⚠️ B2 client issue: {str(e)}")
                
        else:
            print(f"❌ Missing configuration: {', '.join(missing)}")
            print("💡 These should be set as GitHub Repository Secrets")
            
    except Exception as e:
        print(f"⚠️ Configuration test failed: {str(e)}")

def show_github_instructions():
    """Show instructions for setting up GitHub secrets"""
    print("\n📚 How to Add GitHub Repository Secrets:")
    print("=" * 50)
    print("1. Go to your GitHub repository")
    print("2. Click Settings → Secrets and variables → Actions")
    print("3. Click 'New repository secret'")
    print("4. Add each secret with the exact names shown above")
    print("5. Save each secret")
    print("\n🚀 Then run the test workflow:")
    print("   Repository → Actions → 'Test GitHub Secrets Configuration' → Run workflow")

def show_test_workflow_instructions():
    """Show how to run the test workflow"""
    print("\n🧪 How to Test Your GitHub Secrets:")
    print("=" * 50)
    print("1. Push this code to your GitHub repository")
    print("2. Go to: Repository → Actions")
    print("3. Find: 'Test GitHub Secrets Configuration'")
    print("4. Click: 'Run workflow' → 'Run workflow'")
    print("5. Watch the results!")
    print("\n✅ If all steps pass, your secrets are configured correctly!")
    print("❌ If any step fails, check that secret in GitHub")

def main():
    """Main verification function"""
    print("🔐 GitHub Secrets Verification Tool")
    print("=" * 50)
    
    # Check expected format
    expected_secrets = check_github_secrets_format()
    
    # Try to verify locally if secrets are available
    verify_local_config()
    
    # Show instructions
    show_github_instructions()
    show_test_workflow_instructions()
    
    print("\n🎯 Summary:")
    print("- Add the secrets listed above to GitHub Repository Secrets")
    print("- Push this code to GitHub")
    print("- Run the 'Test GitHub Secrets Configuration' workflow")
    print("- Check the workflow results to verify everything works!")
    
    print("\n💡 Pro tip: The test workflow will show you exactly which secrets are missing or incorrect!")

if __name__ == "__main__":
    main()