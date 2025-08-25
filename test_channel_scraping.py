#!/usr/bin/env python3
"""
Test script to debug channel scraping issues
"""
import asyncio
import logging
import sys
import yt_dlp
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_channel_scraping():
    """Test channel scraping with the actual scraper implementation"""
    
    # First, let's test with raw yt-dlp
    url = 'https://www.youtube.com/@BennysMusic/videos'
    
    print("\n" + "="*60)
    print("TESTING RAW YT-DLP EXTRACTION")
    print("="*60)
    
    # Test 1: Basic extraction with extract_flat
    ydl_opts = {
        'quiet': False,
        'extract_flat': True,  # This is what the scraper uses
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            entries = info.get('entries', [])
            print(f"\n✅ Found {len(entries)} videos with extract_flat=True")
            
            # Check if entries are properly formatted
            if entries:
                first_entry = entries[0]
                print(f"\nFirst entry structure:")
                print(f"  - ID: {first_entry.get('id')}")
                print(f"  - Title: {first_entry.get('title')}")
                print(f"  - URL: {first_entry.get('url')}")
                
        except Exception as e:
            print(f"\n❌ Error with extract_flat=True: {e}")
    
    # Test 2: With 'in_playlist' mode (recommended for channels)
    print("\n" + "-"*60)
    ydl_opts = {
        'quiet': False,
        'extract_flat': 'in_playlist',  # Better for playlists/channels
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            entries = info.get('entries', [])
            print(f"\n✅ Found {len(entries)} videos with extract_flat='in_playlist'")
            
        except Exception as e:
            print(f"\n❌ Error with extract_flat='in_playlist': {e}")
    
    # Now test with the actual scraper
    print("\n" + "="*60)
    print("TESTING WITH ACTUAL SCRAPER")
    print("="*60)
    
    try:
        # Import the scraper
        sys.path.insert(0, '/workspace')
        from scraper import VideoScraper
        import uuid
        
        # Create scraper instance
        scraper = VideoScraper()
        
        # Test the scraper's channel extraction
        print("\nTesting scraper's _build_common_ydl_opts()...")
        common_opts = scraper._build_common_ydl_opts()
        print(f"Common options: {common_opts}")
        
        # Build the options the scraper would use
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # This is what the scraper uses
            'playlistend': None,  # No limit
        }
        ydl_opts.update(common_opts)
        
        print("\nTesting with scraper's options...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get('entries', [])
            print(f"\n✅ Scraper would find {len(entries)} videos")
            
            # Check for None entries
            none_entries = sum(1 for e in entries if e is None)
            if none_entries > 0:
                print(f"⚠️  Warning: {none_entries} entries are None")
            
            valid_entries = [e for e in entries if e is not None]
            print(f"✅ {len(valid_entries)} valid entries")
            
    except Exception as e:
        print(f"\n❌ Error testing with scraper: {e}")
        import traceback
        traceback.print_exc()
    
    # Test the actual scrape_playlist_or_channel method
    print("\n" + "="*60)
    print("TESTING SCRAPER'S scrape_playlist_or_channel METHOD")
    print("="*60)
    
    try:
        from scraper import scraper as global_scraper
        
        # Create a mock UUID for testing
        test_uuid = uuid.uuid4()
        
        # Test with max_videos limit first
        print("\nTesting with max_videos=5...")
        success, message, count = await global_scraper.scrape_playlist_or_channel(
            url, test_uuid, max_videos=5
        )
        print(f"Result: success={success}, message='{message}', count={count}")
        
    except Exception as e:
        print(f"\n❌ Error testing scrape_playlist_or_channel: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting channel scraping test...")
    asyncio.run(test_channel_scraping())