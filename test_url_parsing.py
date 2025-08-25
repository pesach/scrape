#!/usr/bin/env python3
"""
Test URL parsing for the channel URL
"""
import sys
sys.path.insert(0, '/workspace')

from youtube_parser import YouTubeURLParser
from models import URLType

# Test URLs
test_urls = [
    "https://www.youtube.com/@BennysMusic",
    "https://www.youtube.com/@BennysMusic/videos",
    "https://www.youtube.com/@BennysMusic/playlists",
    "https://www.youtube.com/channel/UCefarW8iWzuNO7NedV-om-w",
    "https://www.youtube.com/channel/UCefarW8iWzuNO7NedV-om-w/videos",
]

print("Testing YouTube URL parsing:")
print("="*60)

for url in test_urls:
    print(f"\nURL: {url}")
    try:
        url_type, identifier = YouTubeURLParser.parse_url(url)
        print(f"  ✅ Type: {url_type}, ID: {identifier}")
        
        # Get normalized URL
        normalized = YouTubeURLParser.normalize_url(url)
        print(f"  Normalized: {normalized}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# Now test what yt-dlp thinks about these URLs
print("\n" + "="*60)
print("Testing with yt-dlp:")
print("="*60)

import yt_dlp

for url in test_urls[:2]:  # Just test the first two
    print(f"\nURL: {url}")
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"  ✅ Type: {info.get('_type', 'unknown')}")
            print(f"  Title: {info.get('title', 'N/A')}")
            print(f"  Entries: {len(info.get('entries', []))}")
    except Exception as e:
        print(f"  ❌ Error: {e}")