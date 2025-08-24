#!/usr/bin/env python3
"""
Simple HTTP server for the Link Fetcher Dashboard
Serves the dashboard and provides API endpoints for link management
"""

import http.server
import socketserver
import json
import os
import uuid
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import mimetypes
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from video_handler import VideoHandler
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PORT = 8080

# Initialize Supabase client globally
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if SUPABASE_URL and SUPABASE_KEY:
    SUPABASE_CLIENT = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client initialized successfully")
else:
    print("⚠️ Warning: Supabase credentials not found. Database features will be limited.")
    SUPABASE_CLIENT = None

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for the dashboard"""
    
    def __init__(self, *args, **kwargs):
        # Initialize video handler
        self.video_handler = VideoHandler()
        # Set the directory to serve files from
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        # API endpoint to get all links/videos
        if parsed_path.path == '/api/links':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            links = []
            
            if SUPABASE_CLIENT:
                try:
                    # Get videos from Supabase 'videos' table
                    response = SUPABASE_CLIENT.table('videos').select('*').order('created_at', desc=True).execute()
                    
                    if response.data:
                        for video in response.data:
                            # Convert Supabase video format to dashboard link format
                            links.append({
                                "id": video.get('id', ''),
                                "url": video.get('youtube_url', ''),
                                "status": "completed" if video.get('url') else "pending",
                                "addedAt": video.get('created_at', ''),
                                "fetchedAt": video.get('updated_at'),
                                "attempts": 1,  # Default value
                                "backblazeUrl": video.get('url', ''),  # 'url' field contains the Backblaze URL
                                "title": video.get('title', ''),
                                "description": video.get('description', ''),
                                "duration": video.get('duration'),
                                "views": video.get('views'),
                                "likes": video.get('likes')
                            })
                except Exception as e:
                    print(f"Error fetching from Supabase: {e}")
                    # Return empty list on error
                    links = []
            else:
                # Return sample data if Supabase is not configured
                links = [
                    {
                        "id": "sample_1",
                        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        "status": "completed",
                        "addedAt": datetime.now().isoformat(),
                        "fetchedAt": datetime.now().isoformat(),
                        "attempts": 1,
                        "backblazeUrl": "https://example.backblaze.com/video.mp4",
                        "title": "Sample YouTube Video"
                    }
                ]
            
            self.wfile.write(json.dumps(links).encode())
            return
        
        # Serve static files
        return super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        # API endpoint to add a new link/video
        if parsed_path.path == '/api/links':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                url = data.get('url')
                
                if not url:
                    self.send_error(400, "URL is required")
                    return
                
                link_id = f"link_{uuid.uuid4()}"
                
                if SUPABASE_CLIENT:
                    try:
                        # Extract video ID from YouTube URL
                        video_id = None
                        if 'youtube.com/watch?v=' in url:
                            video_id = url.split('v=')[1].split('&')[0]
                        elif 'youtu.be/' in url:
                            video_id = url.split('youtu.be/')[1].split('?')[0]
                        
                        # Insert into Supabase 'videos' table
                        video_data = {
                            'youtube_url': url,
                            'youtube_id': video_id,
                            'title': f'Video from {url}',
                            'status': 'pending'
                        }
                        
                        response = SUPABASE_CLIENT.table('videos').insert(video_data).execute()
                        
                        if response.data and len(response.data) > 0:
                            link_id = response.data[0].get('id', link_id)
                    except Exception as e:
                        print(f"Error inserting into Supabase: {e}")
                        # Continue with the response even if database insert fails
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    "success": True,
                    "message": f"Link added: {url}",
                    "id": link_id
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_error(500, str(e))
            return
        
        # API endpoint to fetch a link
        if parsed_path.path == '/api/fetch':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                link_id = data.get('linkId')
                
                # In a real app, this would trigger actual fetching
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    "success": True,
                    "message": f"Link {link_id} fetched successfully",
                    "data": {"sample": "data"}
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_error(400, str(e))
            return
        
        # API endpoint to re-download video from YouTube
        if parsed_path.path == '/api/video/redownload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                youtube_url = data.get('youtube_url')
                
                if not youtube_url:
                    raise ValueError("YouTube URL is required")
                
                # Download video
                result = self.video_handler.download_youtube_video(youtube_url)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.send_error(400, str(e))
            return
        
        # API endpoint to re-upload video to Backblaze
        if parsed_path.path == '/api/video/reupload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                file_path = data.get('file_path')
                remote_name = data.get('remote_name')
                
                if not file_path:
                    raise ValueError("File path is required")
                
                # Upload to Backblaze
                result = self.video_handler.upload_to_backblaze(file_path, remote_name)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.send_error(400, str(e))
            return
        
        # API endpoint for complete video re-processing
        if parsed_path.path == '/api/video/reprocess':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                youtube_url = data.get('youtube_url')
                video_id = data.get('video_id')
                table_name = data.get('table_name', 'videos')
                
                if not youtube_url or not video_id:
                    raise ValueError("YouTube URL and video ID are required")
                
                # Process complete re-upload workflow
                result = self.video_handler.process_video_reupload(youtube_url, video_id, table_name)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.send_error(400, str(e))
            return
        
        self.send_error(404, "Endpoint not found")
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

def main():
    """Start the server"""
    Handler = DashboardHandler
    
    print(f"🚀 Starting Link Fetcher Dashboard Server...")
    print(f"📡 Server running at http://localhost:{PORT}")
    print(f"🔗 Open http://localhost:{PORT} in your browser to view the dashboard")
    print(f"Press Ctrl+C to stop the server\n")
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n⛔ Server stopped")
            return

if __name__ == "__main__":
    main()