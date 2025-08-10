"""
ScraperAPI Client for YouTube Data Extraction

This module provides an alternative to yt-dlp for scraping YouTube metadata
using ScraperAPI, which handles proxies, CAPTCHAs, and JavaScript rendering.
"""

import requests
import logging
import re
import json
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class ScraperAPIClient:
    """
    Client for scraping YouTube data using ScraperAPI
    
    Features:
    - Automatic proxy rotation
    - CAPTCHA handling
    - JavaScript rendering
    - Rate limit management
    """
    
    def __init__(self, api_key: str, endpoint: str = "https://api.scraperapi.com", 
                 render: bool = True, premium: bool = False, retry_failed: bool = True,
                 timeout: int = 60):
        """
        Initialize ScraperAPI client
        
        Args:
            api_key: ScraperAPI API key
            endpoint: ScraperAPI endpoint URL
            render: Whether to render JavaScript (required for YouTube)
            premium: Whether to use premium proxy pool
            retry_failed: Whether to retry failed requests
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.render = render
        self.premium = premium
        self.retry_failed = retry_failed
        self.timeout = timeout
        
    def _make_request(self, url: str, **extra_params) -> requests.Response:
        """
        Make a request through ScraperAPI
        
        Args:
            url: Target URL to scrape
            **extra_params: Additional ScraperAPI parameters
            
        Returns:
            Response object
        """
        params = {
            'api_key': self.api_key,
            'url': url,
            'render': str(self.render).lower(),
            'premium': str(self.premium).lower() if self.premium else 'false',
            'retry_failed': str(self.retry_failed).lower(),
        }
        params.update(extra_params)
        
        try:
            response = requests.get(
                self.endpoint,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"ScraperAPI request failed for {url}: {str(e)}")
            raise
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video ID or None if not found
        """
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try parsing query parameters
        parsed = urlparse(url)
        if parsed.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                return query_params['v'][0]
        
        return None
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract video information from YouTube video page
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary containing video metadata
        """
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract video ID
            video_id = self.extract_video_id(url)
            
            # Try to find JSON-LD structured data
            json_ld = soup.find('script', type='application/ld+json')
            structured_data = {}
            if json_ld:
                try:
                    structured_data = json.loads(json_ld.string)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON-LD structured data")
            
            # Extract from meta tags and page content
            video_info = {
                'youtube_id': video_id,
                'url': url,
                'title': self._extract_title(soup, structured_data),
                'description': self._extract_description(soup, structured_data),
                'duration': self._extract_duration(soup, structured_data),
                'view_count': self._extract_view_count(soup),
                'like_count': self._extract_like_count(soup),
                'upload_date': self._extract_upload_date(soup, structured_data),
                'channel_name': self._extract_channel_name(soup, structured_data),
                'channel_url': self._extract_channel_url(soup),
                'thumbnail_url': self._extract_thumbnail(soup, structured_data),
                'tags': self._extract_tags(soup),
                'category': self._extract_category(soup),
                'is_live': self._is_live_stream(soup),
                'is_age_restricted': self._is_age_restricted(soup),
            }
            
            # Clean up None values
            video_info = {k: v for k, v in video_info.items() if v is not None}
            
            return video_info
            
        except Exception as e:
            logger.error(f"Failed to extract video info for {url}: {str(e)}")
            raise
    
    def _extract_title(self, soup: BeautifulSoup, structured_data: Dict) -> Optional[str]:
        """Extract video title"""
        # Try structured data first
        if structured_data and 'name' in structured_data:
            return structured_data['name']
        
        # Try meta property
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content']
        
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
            # Remove " - YouTube" suffix
            if title.endswith(' - YouTube'):
                title = title[:-10]
            return title
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup, structured_data: Dict) -> Optional[str]:
        """Extract video description"""
        # Try structured data
        if structured_data and 'description' in structured_data:
            return structured_data['description']
        
        # Try meta description
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        return None
    
    def _extract_duration(self, soup: BeautifulSoup, structured_data: Dict) -> Optional[int]:
        """Extract video duration in seconds"""
        # Try structured data
        if structured_data and 'duration' in structured_data:
            duration_str = structured_data['duration']
            # Parse ISO 8601 duration (e.g., "PT4M33S")
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                return hours * 3600 + minutes * 60 + seconds
        
        # Try meta tag
        meta_duration = soup.find('meta', {'itemprop': 'duration'})
        if meta_duration and meta_duration.get('content'):
            # Similar parsing for ISO 8601
            duration_str = meta_duration['content']
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                return hours * 3600 + minutes * 60 + seconds
        
        return None
    
    def _extract_view_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract view count"""
        # Try meta tag
        meta_views = soup.find('meta', {'itemprop': 'interactionCount'})
        if meta_views and meta_views.get('content'):
            try:
                return int(meta_views['content'])
            except ValueError:
                pass
        
        # Try to find in page text (less reliable)
        view_pattern = re.compile(r'([\d,]+)\s+views?', re.IGNORECASE)
        for text in soup.stripped_strings:
            match = view_pattern.search(text)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        return None
    
    def _extract_like_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract like count"""
        # This is harder to get without JavaScript rendering
        # Try to find in rendered content
        like_pattern = re.compile(r'([\d,]+)\s+likes?', re.IGNORECASE)
        for text in soup.stripped_strings:
            match = like_pattern.search(text)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        return None
    
    def _extract_upload_date(self, soup: BeautifulSoup, structured_data: Dict) -> Optional[str]:
        """Extract upload date"""
        # Try structured data
        if structured_data:
            if 'uploadDate' in structured_data:
                return structured_data['uploadDate']
            if 'datePublished' in structured_data:
                return structured_data['datePublished']
        
        # Try meta tag
        meta_date = soup.find('meta', {'itemprop': 'datePublished'})
        if meta_date and meta_date.get('content'):
            return meta_date['content']
        
        meta_date = soup.find('meta', property='article:published_time')
        if meta_date and meta_date.get('content'):
            return meta_date['content']
        
        return None
    
    def _extract_channel_name(self, soup: BeautifulSoup, structured_data: Dict) -> Optional[str]:
        """Extract channel name"""
        # Try structured data
        if structured_data and 'author' in structured_data:
            if isinstance(structured_data['author'], dict):
                return structured_data['author'].get('name')
            elif isinstance(structured_data['author'], str):
                return structured_data['author']
        
        # Try link tag
        channel_link = soup.find('link', {'itemprop': 'name'})
        if channel_link and channel_link.get('content'):
            return channel_link['content']
        
        # Try meta tag
        meta_channel = soup.find('meta', {'itemprop': 'channelName'})
        if meta_channel and meta_channel.get('content'):
            return meta_channel['content']
        
        return None
    
    def _extract_channel_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract channel URL"""
        # Try to find channel link
        channel_link = soup.find('a', {'class': re.compile(r'channel|owner')})
        if channel_link and channel_link.get('href'):
            href = channel_link['href']
            if href.startswith('/'):
                return f"https://www.youtube.com{href}"
            return href
        
        return None
    
    def _extract_thumbnail(self, soup: BeautifulSoup, structured_data: Dict) -> Optional[str]:
        """Extract thumbnail URL"""
        # Try structured data
        if structured_data and 'thumbnailUrl' in structured_data:
            thumbnails = structured_data['thumbnailUrl']
            if isinstance(thumbnails, list) and thumbnails:
                return thumbnails[0]
            elif isinstance(thumbnails, str):
                return thumbnails
        
        # Try meta tag
        meta_thumb = soup.find('meta', property='og:image')
        if meta_thumb and meta_thumb.get('content'):
            return meta_thumb['content']
        
        # Try link tag
        link_thumb = soup.find('link', {'itemprop': 'thumbnailUrl'})
        if link_thumb and link_thumb.get('href'):
            return link_thumb['href']
        
        return None
    
    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract video tags"""
        tags = []
        
        # Try meta keywords
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            tags = [tag.strip() for tag in meta_keywords['content'].split(',')]
        
        return tags
    
    def _extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract video category"""
        # Try meta tag
        meta_genre = soup.find('meta', {'itemprop': 'genre'})
        if meta_genre and meta_genre.get('content'):
            return meta_genre['content']
        
        return None
    
    def _is_live_stream(self, soup: BeautifulSoup) -> bool:
        """Check if video is a live stream"""
        # Look for live indicators in the page
        live_indicators = ['LIVE NOW', 'Started streaming', 'Streamed live']
        page_text = soup.get_text()
        
        for indicator in live_indicators:
            if indicator in page_text:
                return True
        
        return False
    
    def _is_age_restricted(self, soup: BeautifulSoup) -> bool:
        """Check if video is age restricted"""
        # Look for age restriction indicators
        age_indicators = ['Age-restricted', 'Sign in to confirm your age', 'This video may be inappropriate']
        page_text = soup.get_text()
        
        for indicator in age_indicators:
            if indicator in page_text:
                return True
        
        return False
    
    def get_channel_info(self, channel_url: str) -> Dict[str, Any]:
        """
        Extract channel information from YouTube channel page
        
        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@channelname/about)
            
        Returns:
            Dictionary containing channel metadata
        """
        # Ensure we're on the about page
        if '/about' not in channel_url:
            if channel_url.endswith('/'):
                channel_url = channel_url + 'about'
            else:
                channel_url = channel_url + '/about'
        
        try:
            response = self._make_request(channel_url)
            soup = BeautifulSoup(response.text, 'lxml')
            
            channel_info = {
                'url': channel_url.replace('/about', ''),
                'name': self._extract_channel_name_from_page(soup),
                'description': self._extract_channel_description(soup),
                'subscriber_count': self._extract_subscriber_count(soup),
                'video_count': self._extract_video_count(soup),
                'view_count': self._extract_total_views(soup),
                'joined_date': self._extract_joined_date(soup),
                'country': self._extract_country(soup),
                'links': self._extract_channel_links(soup),
            }
            
            # Clean up None values
            channel_info = {k: v for k, v in channel_info.items() if v is not None}
            
            return channel_info
            
        except Exception as e:
            logger.error(f"Failed to extract channel info for {channel_url}: {str(e)}")
            raise
    
    def _extract_channel_name_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract channel name from channel page"""
        # Try meta property
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content']
        
        # Try to find channel name element
        channel_name = soup.find('yt-formatted-string', {'class': re.compile(r'channel-name')})
        if channel_name:
            return channel_name.text.strip()
        
        return None
    
    def _extract_channel_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract channel description"""
        # Try meta description
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        # Try to find description element
        desc_elem = soup.find('div', {'id': 'description-container'})
        if desc_elem:
            return desc_elem.text.strip()
        
        return None
    
    def _extract_subscriber_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract subscriber count"""
        # Look for subscriber count in text
        sub_pattern = re.compile(r'([\d.]+[KMB]?)\s+subscribers?', re.IGNORECASE)
        for text in soup.stripped_strings:
            match = sub_pattern.search(text)
            if match:
                count_str = match.group(1)
                return self._parse_count(count_str)
        
        return None
    
    def _extract_video_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract total video count"""
        # Look for video count in text
        video_pattern = re.compile(r'([\d,]+)\s+videos?', re.IGNORECASE)
        for text in soup.stripped_strings:
            match = video_pattern.search(text)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        return None
    
    def _extract_total_views(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract total channel views"""
        # Look for view count in text
        view_pattern = re.compile(r'([\d,]+)\s+views?', re.IGNORECASE)
        for text in soup.stripped_strings:
            match = view_pattern.search(text)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        
        return None
    
    def _extract_joined_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract channel creation date"""
        # Look for joined date in text
        joined_pattern = re.compile(r'Joined\s+(.+)', re.IGNORECASE)
        for text in soup.stripped_strings:
            match = joined_pattern.search(text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_country(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract channel country"""
        # Look for country in various places
        country_elem = soup.find('span', {'class': re.compile(r'country')})
        if country_elem:
            return country_elem.text.strip()
        
        return None
    
    def _extract_channel_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract channel's external links"""
        links = []
        
        # Find links section
        links_section = soup.find('div', {'id': 'links-section'})
        if links_section:
            for link in links_section.find_all('a', href=True):
                href = link['href']
                if 'youtube.com' not in href:
                    links.append(href)
        
        return links
    
    def _parse_count(self, count_str: str) -> int:
        """
        Parse count string with K/M/B suffixes
        
        Args:
            count_str: String like "1.5M" or "10K"
            
        Returns:
            Integer count
        """
        count_str = count_str.upper().replace(',', '')
        
        multipliers = {
            'K': 1000,
            'M': 1000000,
            'B': 1000000000,
        }
        
        for suffix, multiplier in multipliers.items():
            if suffix in count_str:
                number = float(count_str.replace(suffix, ''))
                return int(number * multiplier)
        
        try:
            return int(float(count_str))
        except ValueError:
            return 0
    
    def get_playlist_info(self, playlist_url: str) -> Dict[str, Any]:
        """
        Extract playlist information
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            Dictionary containing playlist metadata and video list
        """
        try:
            response = self._make_request(playlist_url)
            soup = BeautifulSoup(response.text, 'lxml')
            
            playlist_info = {
                'url': playlist_url,
                'title': self._extract_playlist_title(soup),
                'description': self._extract_playlist_description(soup),
                'video_count': self._extract_playlist_video_count(soup),
                'channel_name': self._extract_playlist_owner(soup),
                'videos': self._extract_playlist_videos(soup),
            }
            
            return playlist_info
            
        except Exception as e:
            logger.error(f"Failed to extract playlist info for {playlist_url}: {str(e)}")
            raise
    
    def _extract_playlist_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract playlist title"""
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content']
        
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.text.strip().replace(' - YouTube', '')
        
        return None
    
    def _extract_playlist_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract playlist description"""
        meta_desc = soup.find('meta', property='og:description')
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        return None
    
    def _extract_playlist_video_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract playlist video count"""
        count_pattern = re.compile(r'(\d+)\s+videos?', re.IGNORECASE)
        for text in soup.stripped_strings:
            match = count_pattern.search(text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        
        return None
    
    def _extract_playlist_owner(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract playlist owner/channel name"""
        # Look for channel name in various places
        owner_elem = soup.find('a', {'class': re.compile(r'channel|owner')})
        if owner_elem:
            return owner_elem.text.strip()
        
        return None
    
    def _extract_playlist_videos(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract list of videos from playlist"""
        videos = []
        
        # This is a simplified extraction - in practice, you might need
        # to handle pagination or use the YouTube Data API for complete lists
        video_elements = soup.find_all('a', {'id': 'video-title'})
        
        for elem in video_elements[:100]:  # Limit to first 100 videos
            video = {
                'title': elem.text.strip(),
                'url': f"https://www.youtube.com{elem['href']}" if elem.get('href', '').startswith('/') else elem.get('href', ''),
            }
            
            # Try to extract video ID from URL
            video_id = self.extract_video_id(video['url'])
            if video_id:
                video['video_id'] = video_id
            
            videos.append(video)
        
        return videos