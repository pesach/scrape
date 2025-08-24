#!/usr/bin/env python3
"""
Simple HTTP server for the Link Fetcher Dashboard
Serves the dashboard and provides API endpoints for link management
"""

import http.server
import socketserver
import json
import os
from urllib.parse import urlparse, parse_qs
import mimetypes
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from video_handler import VideoHandler

PORT = 8080

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for the dashboard"""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)
        # Initialize video handler
        self.video_handler = VideoHandler()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        # Serve the dashboard at root
        if parsed_path.path == '/':
            self.path = '/dashboard.html'
        
        # API endpoint to get links
        if parsed_path.path == '/api/links':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Sample response (in a real app, this would come from a database)
            links = [
                {
                    "id": "link_1",
                    "url": "https://api.example.com/data",
                    "status": "pending",
                    "addedAt": "2024-01-01T12:00:00Z",
                    "attempts": 0
                }
            ]
            self.wfile.write(json.dumps(links).encode())
            return
        
        # Serve static files
        return super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
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
        
        # API endpoint to add a new link
        if parsed_path.path == '/api/links':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                url = data.get('url')
                
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    "success": True,
                    "message": f"Link added: {url}",
                    "id": f"link_{hash(url)}"
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