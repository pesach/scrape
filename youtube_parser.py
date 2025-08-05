import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs
from models import URLType
import yt_dlp

class YouTubeURLParser:
    """Parser and validator for YouTube URLs"""
    
    # Regular expressions for different YouTube URL patterns
    PATTERNS = {
        URLType.VIDEO: [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
        ],
        URLType.CHANNEL: [
            r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'youtube\.com/@([a-zA-Z0-9_.-]+)',
        ],
        URLType.PLAYLIST: [
            r'youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?.*list=([a-zA-Z0-9_-]+)',
        ],
        URLType.USER: [
            r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        ]
    }
    
    @classmethod
    def parse_url(cls, url: str) -> Tuple[URLType, str]:
        """
        Parse a YouTube URL and return its type and extracted ID/identifier
        
        Args:
            url: YouTube URL to parse
            
        Returns:
            Tuple of (URLType, identifier)
            
        Raises:
            ValueError: If URL is not a valid YouTube URL
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Normalize URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Parse URL components
        parsed = urlparse(url)
        if parsed.netloc not in ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']:
            raise ValueError("Not a valid YouTube URL")
        
        # Check each pattern type
        for url_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    return url_type, match.group(1)
        
        raise ValueError("Could not determine YouTube URL type")
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        Validate if a URL is a supported YouTube URL
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            cls.parse_url(url)
            return True
        except ValueError:
            return False
    
    @classmethod
    def normalize_url(cls, url: str) -> str:
        """
        Normalize a YouTube URL to a standard format
        
        Args:
            url: YouTube URL to normalize
            
        Returns:
            Normalized URL
        """
        try:
            url_type, identifier = cls.parse_url(url)
            
            if url_type == URLType.VIDEO:
                return f"https://www.youtube.com/watch?v={identifier}"
            elif url_type == URLType.CHANNEL:
                # Try to determine if it's a channel ID or handle
                if identifier.startswith('UC') and len(identifier) == 24:
                    return f"https://www.youtube.com/channel/{identifier}"
                else:
                    return f"https://www.youtube.com/@{identifier}"
            elif url_type == URLType.PLAYLIST:
                return f"https://www.youtube.com/playlist?list={identifier}"
            elif url_type == URLType.USER:
                return f"https://www.youtube.com/user/{identifier}"
            
        except ValueError:
            pass
        
        return url
    
    @classmethod
    def extract_metadata(cls, url: str) -> dict:
        """
        Extract metadata from a YouTube URL using yt-dlp
        
        Args:
            url: YouTube URL
            
        Returns:
            Dictionary containing metadata
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just extract metadata
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Clean up the metadata
                metadata = {
                    'title': info.get('title'),
                    'description': info.get('description'),
                    'uploader': info.get('uploader'),
                    'uploader_id': info.get('uploader_id'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'upload_date': info.get('upload_date'),
                    'thumbnail': info.get('thumbnail'),
                    'tags': info.get('tags', []),
                    'categories': info.get('categories', []),
                    'webpage_url': info.get('webpage_url'),
                    'id': info.get('id'),
                }
                
                # Handle playlist/channel specific data
                if 'entries' in info:
                    metadata['entries_count'] = len(info['entries'])
                    metadata['entries'] = info['entries']
                
                return {k: v for k, v in metadata.items() if v is not None}
                
        except Exception as e:
            raise ValueError(f"Failed to extract metadata: {str(e)}")

def parse_youtube_url(url: str) -> Tuple[URLType, str]:
    """Convenience function to parse YouTube URL"""
    return YouTubeURLParser.parse_url(url)

def validate_youtube_url(url: str) -> bool:
    """Convenience function to validate YouTube URL"""
    return YouTubeURLParser.validate_url(url)