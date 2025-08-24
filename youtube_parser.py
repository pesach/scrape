import re
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse, parse_qs
from models import URLType
import yt_dlp
from config import config

logger = logging.getLogger(__name__)

class YouTubeURLParser:
    """
    Parser and validator for YouTube URLs
    
    METADATA EXTRACTION STRATEGY:
    - Uses yt-dlp for web scraping (NOT YouTube API)
    - No API keys or authentication required
    - No rate limiting from YouTube API
    - Can access more metadata than API provides
    - Works with private/unlisted videos if accessible
    - More reliable than API for bulk operations
    
    SUPPORTED URL TYPES:
    - Single videos: youtube.com/watch?v=ID, youtu.be/ID
    - Channels: youtube.com/channel/ID, youtube.com/@handle
    - Playlists: youtube.com/playlist?list=ID
    - User pages: youtube.com/user/USERNAME
    """
    
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
        # Build base options
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just extract metadata
            'http_headers': {
                'User-Agent': config.SCRAPER_USER_AGENT,
                'Accept-Language': config.SCRAPER_ACCEPT_LANGUAGE,
                'Referer': 'https://www.youtube.com/',
            },
        }

        # Prefer cookies if configured
        cookies_details: Optional[Dict[str, Any]] = None
        if config.YT_COOKIES_FILE:
            cookies_details = cls._validate_cookies_file(config.YT_COOKIES_FILE)
            # Log a concise summary
            logger.info(
                "Cookies check: exists=%s readable=%s size=%s youtube_lines=%s netscape_like=%s path=%s",
                cookies_details.get('exists'),
                cookies_details.get('readable'),
                cookies_details.get('size_bytes'),
                cookies_details.get('youtube_cookie_lines'),
                cookies_details.get('is_netscape_like'),
                cookies_details.get('path'),
            )
            if cookies_details.get('exists') and cookies_details.get('readable'):
                ydl_opts['cookiefile'] = config.YT_COOKIES_FILE
            else:
                logger.warning("Cookie file is not usable; proceeding without cookies: %s", cookies_details)
        elif config.COOKIES_FROM_BROWSER:
            browser = config.COOKIES_FROM_BROWSER.strip().lower()
            logger.info("Using cookies from browser: %s", browser)
            ydl_opts['cookiesfrombrowser'] = (browser, )
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

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

            if 'entries' in info:
                metadata['entries_count'] = len(info['entries'])
                metadata['entries'] = info['entries']

            return {k: v for k, v in metadata.items() if v is not None}

        except Exception as e:
            # Attach cookie diagnostics when present to aid troubleshooting
            error_message = f"Failed to extract metadata: {str(e)}"
            if cookies_details is not None:
                error_message += f" | cookies={cookies_details}"
            logger.exception(error_message)
            raise ValueError(error_message)

    @classmethod
    def _validate_cookies_file(cls, path_str: str) -> Dict[str, Any]:
        """
        Perform basic sanity checks on a Netscape-format cookies.txt file.

        Returns a dictionary with keys: exists, readable, size_bytes, is_netscape_like,
        youtube_cookie_lines, path
        """
        details: Dict[str, Any] = {
            'path': _safe_str(path_str),
            'exists': False,
            'readable': False,
            'size_bytes': 0,
            'is_netscape_like': False,
            'youtube_cookie_lines': 0,
        }

        try:
            p = Path(os.path.expanduser(os.path.expandvars(path_str)))
            details['path'] = str(p)
            if not p.exists():
                return details
            details['exists'] = True

            try:
                st = p.stat()
                details['size_bytes'] = st.st_size
            except Exception:
                pass

            try:
                with p.open('r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                details['readable'] = True
            except Exception:
                return details

            non_comment = [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith('#')]
            # Netscape format has 7 tab-separated fields
            if non_comment:
                sample = non_comment[0]
                parts = sample.split('\t')
                details['is_netscape_like'] = (len(parts) >= 6)
            details['youtube_cookie_lines'] = sum(1 for ln in non_comment if 'youtube.com' in ln)

            return details
        except Exception:
            return details


def _safe_str(obj: Any) -> str:
    try:
        return str(obj)
    except Exception:
        return "-"

    @classmethod
    def probe_with_cookies(cls, url: str) -> Dict[str, Any]:
        """
        Attempt yt-dlp extraction using only the provided cookie source to verify
        that authentication/captcha-bypass works for a single URL.

        Returns a dictionary with keys:
          - success: bool
          - error: optional str
          - cookies: cookie diagnostics dict
        """
        result: Dict[str, Any] = {
            'success': False,
            'error': None,
            'cookies': None,
        }

        cookies_details: Optional[Dict[str, Any]] = None
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': False,
            'extract_flat': True,
            'http_headers': {
                'User-Agent': config.SCRAPER_USER_AGENT,
                'Accept-Language': config.SCRAPER_ACCEPT_LANGUAGE,
                'Referer': 'https://www.youtube.com/',
            },
        }

        if config.YT_COOKIES_FILE:
            cookies_details = cls._validate_cookies_file(config.YT_COOKIES_FILE)
            if cookies_details.get('exists') and cookies_details.get('readable'):
                ydl_opts['cookiefile'] = config.YT_COOKIES_FILE
            else:
                result['error'] = f"Cookie file not usable: {cookies_details}"
                result['cookies'] = cookies_details
                return result
        elif config.COOKIES_FROM_BROWSER:
            browser = config.COOKIES_FROM_BROWSER.strip().lower()
            cookies_details = {'from_browser': browser}
            ydl_opts['cookiesfrombrowser'] = (browser, )
        else:
            result['error'] = "No cookies configured (YT_COOKIES_FILE or COOKIES_FROM_BROWSER)"
            result['cookies'] = {}
            return result

        result['cookies'] = cookies_details or {}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=False)
            result['success'] = True
            return result
        except Exception as e:
            result['error'] = _safe_str(e)
            return result

def parse_youtube_url(url: str) -> Tuple[URLType, str]:
    """Convenience function to parse YouTube URL"""
    return YouTubeURLParser.parse_url(url)

def validate_youtube_url(url: str) -> bool:
    """Convenience function to validate YouTube URL"""
    return YouTubeURLParser.validate_url(url)