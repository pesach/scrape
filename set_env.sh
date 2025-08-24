#!/bin/bash
# This script sets environment variables for the YouTube scraper
# In production or GitHub Actions, these would come from GitHub Secrets

echo "Setting environment variables for YouTube scraper..."

# You need to replace these with your actual values
# These are placeholders that need to be configured
export SUPABASE_URL="https://your-project-id.supabase.co"
export SUPABASE_KEY="your-supabase-anon-key-here"
export B2_APPLICATION_KEY_ID="your-b2-key-id-here"
export B2_APPLICATION_KEY="your-b2-application-key-here"
export B2_BUCKET_NAME="your-bucket-name-here"
export B2_ENDPOINT_URL="https://s3.us-west-004.backblazeb2.com"
export REDIS_URL="redis://localhost:6379/0"

echo "Environment variables set (using placeholders - replace with actual values)"
echo "To use GitHub Secrets, run this in a GitHub Actions workflow instead"
