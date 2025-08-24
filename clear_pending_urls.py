#!/usr/bin/env python3
"""
Clear Pending URLs from Supabase Tables
========================================
This script removes all pending URLs waiting to be fetched from the Supabase database.
It clears:
1. Pending scraping jobs from scraping_jobs table
2. URLs that haven't been processed yet from youtube_urls table
"""

import os
import sys
from datetime import datetime
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clear_pending_urls():
    """Clear all pending URLs from Supabase tables"""
    
    try:
        # Try to load environment variables
        load_dotenv()
        
        # Get Supabase credentials from environment
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_KEY")
        
        # Validate configuration
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("❌ SUPABASE_URL and SUPABASE_KEY must be configured")
            logger.info("Please set these environment variables or create a .env file")
            logger.info("\nExample .env file:")
            logger.info("SUPABASE_URL=https://your-project.supabase.co")
            logger.info("SUPABASE_KEY=your_supabase_anon_key")
            return False
        
        logger.info("🔄 Connecting to Supabase...")
        logger.info(f"   URL: {SUPABASE_URL}")
        
        # Create Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 1. Clear pending scraping jobs
        logger.info("\n📋 Checking scraping_jobs table for pending jobs...")
        
        # First, count pending jobs
        pending_jobs_result = supabase.table('scraping_jobs').select('id', count='exact').eq('status', 'pending').execute()
        pending_jobs_count = len(pending_jobs_result.data) if pending_jobs_result.data else 0
        
        if pending_jobs_count > 0:
            logger.info(f"   Found {pending_jobs_count} pending scraping jobs")
            
            # Delete pending jobs
            delete_jobs_result = supabase.table('scraping_jobs').delete().eq('status', 'pending').execute()
            logger.info(f"   ✅ Deleted {len(delete_jobs_result.data) if delete_jobs_result.data else 0} pending scraping jobs")
        else:
            logger.info("   ✅ No pending scraping jobs found")
        
        # 2. Clear processing jobs (optional - these might be stuck)
        processing_jobs_result = supabase.table('scraping_jobs').select('id', count='exact').eq('status', 'processing').execute()
        processing_jobs_count = len(processing_jobs_result.data) if processing_jobs_result.data else 0
        
        if processing_jobs_count > 0:
            logger.info(f"\n⚠️  Found {processing_jobs_count} jobs stuck in 'processing' status")
            response = input("   Do you want to delete these as well? (y/n): ").strip().lower()
            
            if response == 'y':
                delete_processing_result = supabase.table('scraping_jobs').delete().eq('status', 'processing').execute()
                logger.info(f"   ✅ Deleted {len(delete_processing_result.data) if delete_processing_result.data else 0} processing jobs")
            else:
                logger.info("   ⏭️  Skipping processing jobs")
        
        # 3. Check youtube_urls table for URLs without completed jobs
        logger.info("\n📋 Checking youtube_urls table...")
        
        # Get all URLs
        all_urls_result = supabase.table('youtube_urls').select('id, url, url_type, created_at').execute()
        all_urls_count = len(all_urls_result.data) if all_urls_result.data else 0
        
        if all_urls_count > 0:
            logger.info(f"   Found {all_urls_count} total URLs in youtube_urls table")
            
            # Find URLs without completed jobs
            urls_to_check = []
            for url_record in all_urls_result.data:
                # Check if this URL has any completed jobs
                jobs_result = supabase.table('scraping_jobs').select('status').eq('youtube_url_id', url_record['id']).execute()
                
                has_completed = any(job['status'] == 'completed' for job in (jobs_result.data or []))
                
                if not has_completed:
                    urls_to_check.append(url_record)
            
            if urls_to_check:
                logger.info(f"   Found {len(urls_to_check)} URLs without completed jobs:")
                for url in urls_to_check[:5]:  # Show first 5
                    logger.info(f"     - {url['url_type']}: {url['url'][:80]}...")
                if len(urls_to_check) > 5:
                    logger.info(f"     ... and {len(urls_to_check) - 5} more")
                
                response = input("\n   Do you want to delete these unprocessed URLs? (y/n): ").strip().lower()
                
                if response == 'y':
                    deleted_count = 0
                    for url in urls_to_check:
                        try:
                            # Delete the URL (this will cascade delete related jobs and url_videos entries)
                            supabase.table('youtube_urls').delete().eq('id', url['id']).execute()
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"     ❌ Failed to delete URL {url['id']}: {e}")
                    
                    logger.info(f"   ✅ Deleted {deleted_count} unprocessed URLs")
                else:
                    logger.info("   ⏭️  Skipping URL deletion")
            else:
                logger.info("   ✅ All URLs have been processed or have completed jobs")
        else:
            logger.info("   ✅ No URLs found in youtube_urls table")
        
        # 4. Check for videos with pending status
        logger.info("\n📋 Checking videos table for pending entries...")
        
        pending_videos_result = supabase.table('videos').select('id, youtube_id, status', count='exact').eq('status', 'pending').execute()
        pending_videos_count = len(pending_videos_result.data) if pending_videos_result.data else 0
        
        if pending_videos_count > 0:
            logger.info(f"   Found {pending_videos_count} videos with 'pending' status")
            response = input("   Do you want to delete these pending videos? (y/n): ").strip().lower()
            
            if response == 'y':
                delete_videos_result = supabase.table('videos').delete().eq('status', 'pending').execute()
                logger.info(f"   ✅ Deleted {len(delete_videos_result.data) if delete_videos_result.data else 0} pending videos")
            else:
                logger.info("   ⏭️  Skipping pending videos")
        else:
            logger.info("   ✅ No pending videos found")
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("🎉 CLEANUP COMPLETE!")
        logger.info("="*50)
        
        # Final status check
        final_pending_jobs = supabase.table('scraping_jobs').select('id', count='exact').eq('status', 'pending').execute()
        final_processing_jobs = supabase.table('scraping_jobs').select('id', count='exact').eq('status', 'processing').execute()
        final_pending_videos = supabase.table('videos').select('id', count='exact').eq('status', 'pending').execute()
        
        logger.info("\n📊 Final Status:")
        logger.info(f"   Pending scraping jobs: {len(final_pending_jobs.data) if final_pending_jobs.data else 0}")
        logger.info(f"   Processing scraping jobs: {len(final_processing_jobs.data) if final_processing_jobs.data else 0}")
        logger.info(f"   Pending videos: {len(final_pending_videos.data) if final_pending_videos.data else 0}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {str(e)}")
        logger.error(f"   Type: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    logger.info("🧹 Supabase Pending URLs Cleaner")
    logger.info("=" * 50)
    
    success = clear_pending_urls()
    
    if success:
        logger.info("\n✅ Script completed successfully!")
        sys.exit(0)
    else:
        logger.info("\n❌ Script failed. Please check the errors above.")
        sys.exit(1)