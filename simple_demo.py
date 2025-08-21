#!/usr/bin/env python3
"""
Simplified YouTube Video Scraper Demo
Works without Supabase/Backblaze B2 for testing metadata extraction
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import json

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# Try to import yt-dlp
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

app = FastAPI(title="YouTube Metadata Demo", version="1.0.0")
templates = Jinja2Templates(directory="templates")

class SimpleYouTubeParser:
    """Simplified YouTube parser for demo purposes"""
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Simple URL validation"""
        return "youtube.com" in url or "youtu.be" in url
    
    @staticmethod
    def extract_metadata(url: str) -> Dict[str, Any]:
        """Extract metadata using yt-dlp"""
        if not YT_DLP_AVAILABLE:
            raise Exception("yt-dlp not available. Install with: pip install yt-dlp")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,  # Don't download, just get metadata
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                
                # Extract relevant metadata
                metadata = {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'description': info.get('description', '')[:500] + '...' if info.get('description') else None,
                    'uploader': info.get('uploader'),
                    'uploader_id': info.get('uploader_id'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'upload_date': info.get('upload_date'),
                    'thumbnail': info.get('thumbnail'),
                    'webpage_url': info.get('webpage_url'),
                    'format_info': [],
                }
                
                # Get format information
                formats = info.get('formats', [])
                for fmt in formats[-5:]:  # Last 5 formats (usually best quality)
                    if fmt.get('height'):
                        metadata['format_info'].append({
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'resolution': f"{fmt.get('width', 'N/A')}x{fmt.get('height', 'N/A')}",
                            'fps': fmt.get('fps'),
                            'filesize': fmt.get('filesize'),
                            'vcodec': fmt.get('vcodec'),
                            'acodec': fmt.get('acodec'),
                        })
                
                # Handle playlist/channel data
                if 'entries' in info:
                    metadata['type'] = 'playlist/channel'
                    metadata['entry_count'] = len(info['entries'])
                    metadata['entries_sample'] = []
                    
                    # Get first few entries as samples
                    for entry in info['entries'][:3]:
                        if entry:
                            metadata['entries_sample'].append({
                                'id': entry.get('id'),
                                'title': entry.get('title'),
                                'duration': entry.get('duration'),
                            })
                else:
                    metadata['type'] = 'video'
                
                return metadata
                
            except Exception as e:
                raise Exception(f"Failed to extract metadata: {str(e)}")

@app.get("/")
async def home(request: Request):
    """Home page"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Metadata Demo</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <h1>🎬 YouTube Metadata Demo</h1>
            <p class="text-muted">Test YouTube metadata extraction without external dependencies</p>
            
            <div class="card">
                <div class="card-body">
                    <form id="metadataForm">
                        <div class="mb-3">
                            <label class="form-label">YouTube URL</label>
                            <input type="url" class="form-control" id="url" placeholder="https://www.youtube.com/watch?v=..." required>
                        </div>
                        <button type="submit" class="btn btn-primary">Extract Metadata</button>
                    </form>
                    
                    <div id="result" class="mt-4" style="display:none;"></div>
                </div>
            </div>
        </div>
        
        <script>
        document.getElementById('metadataForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('url').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '<div class="text-center"><i class="spinner-border"></i> Extracting metadata...</div>';
            resultDiv.style.display = 'block';
            
            try {
                const response = await fetch('/extract-metadata', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    resultDiv.innerHTML = `
                        <h5>✅ Metadata Extracted Successfully</h5>
                        <pre class="bg-light p-3 rounded"><code>${JSON.stringify(data.metadata, null, 2)}</code></pre>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="alert alert-danger">❌ Error: ${data.error}</div>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<div class="alert alert-danger">❌ Network Error: ${error.message}</div>`;
            }
        });
        </script>
    </body>
    </html>
    """)

@app.post("/extract-metadata")
async def extract_metadata(request: Request):
    """Extract metadata from YouTube URL"""
    try:
        data = await request.json()
        url = data.get('url', '').strip()
        
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        if not SimpleYouTubeParser.validate_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        # Extract metadata
        metadata = SimpleYouTubeParser.extract_metadata(url)
        
        return {
            "success": True,
            "url": url,
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "yt_dlp_available": YT_DLP_AVAILABLE,
        "message": "This is a simplified demo version for testing metadata extraction"
    }

@app.get("/test-urls")
async def test_urls():
    """Provide test URLs"""
    return {
        "test_urls": [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo
            "https://www.youtube.com/channel/UCefarW8iWzuNO7NedV-om-w",  # Channel
            "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy8VbX6gf_1bSC6WcqDi8Wq"  # Playlist
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting YouTube Metadata Demo...")
    print("📱 Open: http://localhost:8001")
    print("🔍 Health check: http://localhost:8001/health")
    print("🧪 Test URLs: http://localhost:8001/test-urls")
    
    if not YT_DLP_AVAILABLE:
        print("⚠️  Warning: yt-dlp not available. Install with: pip install yt-dlp")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)