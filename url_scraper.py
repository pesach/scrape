#!/usr/bin/env python3
"""
URL Scraper Script
Reads URLs from a text file, fetches each URL, scrapes for youtube/* values,
and writes YouTube watch URLs to an output file.
"""

import re
import sys
import requests
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse
import time

def fetch_and_scrape(url, timeout=10):
    """
    Fetch a URL and scrape for youtube/* patterns
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        List of YouTube video IDs found
    """
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url.strip(), headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all text content
        text = soup.get_text()
        
        # Also check HTML source for patterns
        html_content = response.text
        
        # Pattern to match youtube/* or variations
        # This will match patterns like youtube/VIDEO_ID, youtube/*VIDEO_ID, etc.
        patterns = [
            r'youtube/([a-zA-Z0-9_-]{11})',  # Standard YouTube video ID format
            r'youtube/\*([a-zA-Z0-9_-]{11})',  # With asterisk
            r'youtube/\*\s*([a-zA-Z0-9_-]{11})',  # With asterisk and space
            r'"youtube/\*([a-zA-Z0-9_-]{11})"',  # In quotes
            r'youtube/\*"([a-zA-Z0-9_-]{11})"',  # Asterisk before quotes
        ]
        
        video_ids = set()
        
        # Search in both text and HTML
        for pattern in patterns:
            # Search in HTML
            matches = re.findall(pattern, html_content)
            video_ids.update(matches)
            
            # Search in text
            matches = re.findall(pattern, text)
            video_ids.update(matches)
        
        # Also look for patterns where the star might be marking the value differently
        # e.g., *VIDEO_ID in youtube context
        alt_patterns = [
            r'youtube[/:\s]+\*([a-zA-Z0-9_-]{11})',
            r'youtube.*?\*([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in alt_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            video_ids.update(matches)
        
        return list(video_ids)
        
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Unexpected error processing {url}: {e}", file=sys.stderr)
        return []

def process_urls(input_file, output_file, delay=0.5):
    """
    Process URLs from input file and write YouTube URLs to output file
    
    Args:
        input_file: Path to input file with URLs (one per line)
        output_file: Path to output file for YouTube watch URLs
        delay: Delay between requests in seconds (to be respectful)
    """
    youtube_urls = []
    processed_count = 0
    
    try:
        with open(input_file, 'r') as f:
            urls = f.readlines()
        
        print(f"Processing {len(urls)} URLs...")
        
        for i, url in enumerate(urls, 1):
            url = url.strip()
            if not url:
                continue
                
            print(f"[{i}/{len(urls)}] Processing: {url}")
            
            video_ids = fetch_and_scrape(url)
            
            if video_ids:
                print(f"  Found {len(video_ids)} video ID(s): {', '.join(video_ids)}")
                for video_id in video_ids:
                    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                    youtube_urls.append(youtube_url)
            else:
                print(f"  No YouTube video IDs found")
            
            processed_count += 1
            
            # Be respectful with rate limiting
            if i < len(urls):
                time.sleep(delay)
        
        # Write results to output file
        with open(output_file, 'w') as f:
            for url in youtube_urls:
                f.write(url + '\n')
        
        print(f"\n✓ Processed {processed_count} URLs")
        print(f"✓ Found {len(youtube_urls)} YouTube video IDs")
        print(f"✓ Results written to {output_file}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Scrape URLs for YouTube video IDs marked with asterisks'
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default='urls.txt',
        help='Input file containing URLs (default: urls.txt)'
    )
    parser.add_argument(
        'output_file',
        nargs='?',
        default='youtube_urls.txt',
        help='Output file for YouTube watch URLs (default: youtube_urls.txt)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5)'
    )
    
    args = parser.parse_args()
    
    process_urls(args.input_file, args.output_file, args.delay)

if __name__ == '__main__':
    main()