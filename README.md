# YouTube Video Scraper

A comprehensive system to scrape YouTube videos and store them in Backblaze B2 with metadata in Supabase. Supports single videos, channels, playlists, and user pages.

## Features

- **Multiple URL Types**: Support for YouTube videos, channels, playlists, and user pages
- **High-Quality Downloads**: Downloads videos in the highest available resolution
- **Cloud Storage**: Stores videos in Backblaze B2 (S3-compatible)
- **Database Integration**: Metadata stored in Supabase PostgreSQL
- **Background Processing**: Uses Celery for asynchronous video processing
- **Web Interface**: Clean web UI for URL submission and monitoring
- **REST API**: Full API for programmatic access
- **Rate Limiting**: Prevents system overload with configurable limits
- **Queue Management**: Priority queues for different content types
- **Scalable Architecture**: Handle high volume with multiple workers
- **Automatic Cleanup**: Videos deleted from server after cloud upload
- **No API Keys**: Uses yt-dlp scraping instead of YouTube API

## Architecture & Flow

### **Request Flow:**
```
User Input → Rate Limit Check → Supabase DB → Redis Queue → Celery Worker → Download → B2 Storage
     ↓              ↓               ↓            ↓             ↓             ↓
  Immediate      Immediate       Immediate    Queued      Background     Async Upload
```

### **System Components:**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │   FastAPI App   │    │   Celery Worker │
│    (Frontend)   │◄──►│   (Backend)     │◄──►│  (Background)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Supabase DB   │    │  Backblaze B2   │
                       │   (Metadata)    │    │   (Videos)      │
                       └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Redis Queue   │
                       │   (Job Queue)   │
                       └─────────────────┘
```

### **High Volume Handling:**

**✅ Built-in Protections:**
- **Rate Limiting**: 10 URLs/minute per IP
- **Queue Management**: Priority queues (videos → high, playlists → normal)
- **System Monitoring**: Automatic capacity checks
- **Graceful Degradation**: Continues without background processing if needed

**📊 Scaling Options:**
- **Horizontal**: Multiple Celery workers
- **Vertical**: Increase worker concurrency
- **Database**: Supabase auto-scales
- **Storage**: Backblaze B2 handles any volume

### **Important Technical Details:**

**🎯 Metadata Extraction:**
- **Source**: yt-dlp scraping (NOT YouTube API)
- **Benefits**: No API keys, no rate limits, more detailed data
- **Method**: Direct web scraping like a browser would do
- **Handles**: Private/unlisted videos if accessible

**💾 Storage & Cleanup:**
- **Process**: Download → Upload to B2 → Save metadata → Delete local file
- **Local Storage**: Temporary only (auto-deleted after upload)
- **Permanent Storage**: Backblaze B2 cloud only
- **Disk Usage**: Near zero (files cleaned up immediately)

**⚡ Request Processing:**
1. **Immediate**: URL validation and database entry
2. **Queued**: Background job creation
3. **Async**: Video download and processing
4. **User Experience**: Can monitor progress via dashboard

## Prerequisites

- Python 3.8+
- Redis (for Celery)
- FFmpeg (for video processing)
- Supabase account
- Backblaze B2 account

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd youtube-scraper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**:
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

4. **Install and start Redis**:
   ```bash
   # Ubuntu/Debian
   sudo apt install redis-server
   sudo systemctl start redis-server
   
   # macOS
   brew install redis
   brew services start redis
   
   # Windows
   # Download from https://redis.io/download
   ```

## Configuration

You can configure the application in two ways:

### **Option 1: GitHub Repository Secrets (Recommended for Production)**

1. **Go to your GitHub repository**
2. **Settings → Secrets and variables → Actions → New repository secret**
3. **Add these secrets:**
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_anon_key
   B2_APPLICATION_KEY_ID=your_b2_key_id
   B2_APPLICATION_KEY=your_b2_application_key
   B2_BUCKET_NAME=your_bucket_name
   B2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
   REDIS_URL=redis://localhost:6379/0
   ```

✅ **Benefits**: Secure, no .env file needed, works with CI/CD, easy deployment

### **Option 2: Local .env File (For Development)**

1. **Copy environment variables**:
   ```bash
   cp .env.example .env
   ```

2. **Configure Supabase**:
   - Create a new project at [supabase.com](https://supabase.com)
   - Get your project URL and anon key
   - Update `.env` with your Supabase credentials
   - Run the database schema:
     ```sql
     -- Execute the contents of database/schema.sql in your Supabase SQL editor
     ```

3. **Configure Backblaze B2**:
   - Create a Backblaze B2 account
   - Create an application key with read/write permissions
   - Create a bucket for storing videos
   - Update `.env` with your B2 credentials

4. **Update environment variables in `.env`** (same values as GitHub secrets above)

## 🐳 **Docker Deployment (Uses Environment Variables)**

```bash
# With environment variables
docker-compose up -d

# Or with explicit variables
SUPABASE_URL=your_url SUPABASE_KEY=your_key docker-compose up -d
```

## ☁️ **Cloud Deployment Examples**

**Heroku:**
```bash
heroku config:set SUPABASE_URL=your_url
heroku config:set SUPABASE_KEY=your_key
# ... other variables
```

**Railway/Render/Vercel:**
- Add environment variables in their dashboard
- No .env file needed!

## Usage

### Starting the Application

1. **Start the web application**:
   ```bash
   python main.py
   ```
   The web interface will be available at `http://localhost:8000`

2. **Start Celery worker** (in a separate terminal):
   ```bash
   celery -A tasks worker --loglevel=info
   ```

3. **Start Celery beat** (optional, for scheduled tasks):
   ```bash
   celery -A tasks beat --loglevel=info
   ```

### Using the Web Interface

1. Navigate to `http://localhost:8000`
2. Enter a YouTube URL in the form
3. Click "Validate URL" to check if the URL is supported
4. Click "Start Scraping" to begin the download process
5. Monitor progress on the Dashboard page

### Supported URL Types

- **Single Video**: `https://www.youtube.com/watch?v=VIDEO_ID`
- **Channel**: `https://www.youtube.com/channel/CHANNEL_ID`
- **Channel Handle**: `https://www.youtube.com/@username`
- **Playlist**: `https://www.youtube.com/playlist?list=PLAYLIST_ID`
- **User**: `https://www.youtube.com/user/USERNAME`

### API Endpoints

#### Submit URL for Scraping
```bash
curl -X POST "http://localhost:8000/api/urls" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

#### List Submitted URLs
```bash
curl "http://localhost:8000/api/urls"
```

#### Get Job Status
```bash
curl "http://localhost:8000/api/jobs/{job_id}"
```

#### Get Videos for URL
```bash
curl "http://localhost:8000/api/urls/{url_id}/videos"
```

## 🧪 **Testing & Verification**

### **GitHub Secrets Verification**

#### **Method 1: Automated Test Workflow (Recommended)**
The most reliable way to verify your GitHub secrets:

1. **Push your code to GitHub**:
   ```bash
   git add -A
   git commit -m "Add GitHub secrets configuration"
   git push origin main
   ```

2. **Run the test workflow**:
   - Go to: **Repository → Actions**
   - Find: **"Test GitHub Secrets Configuration"**
   - Click: **"Run workflow" → "Run workflow"**
   - Watch the results - all steps should pass ✅

3. **Interpret results**:
   - ✅ **All green**: Secrets configured correctly
   - ❌ **Any red**: Check that specific secret in GitHub

#### **Method 2: Local Verification Script**
```bash
python verify_secrets.py
```

This script will:
- 📋 Show expected secret format and examples
- 🔍 Validate secret formats if set locally
- 💡 Provide setup instructions
- 🚀 Guide you through the testing process

#### **Method 3: Manual Component Testing**
Test individual components:

```bash
# Test configuration loading
python -c "from config import config; print('Config:', config.get_config_summary())"

# Test database connection
python -c "from database import db; print('✅ Database ready')"

# Test Backblaze B2 storage
python -c "from storage import storage; print('✅ B2 storage ready')"

# Test YouTube parser
python -c "from youtube_parser import parse_youtube_url; print('✅ Parser ready')"
```

### **Setup Verification**

#### **Comprehensive Setup Test**
```bash
python test_setup.py
```

This tests:
- ✅ All required Python packages
- ✅ Environment variables/configuration
- ✅ Redis connection
- ✅ FFmpeg availability
- ✅ YouTube URL parsing

#### **Simple Metadata Test**
```bash
python simple_demo.py
```
- Opens a test server at `http://localhost:8001`
- Tests metadata extraction without external dependencies
- Good for isolating YouTube parsing issues

### **Health Check Endpoints**

Once your application is running:

```bash
# Check overall system health
curl http://localhost:8000/health

# Debug configuration issues
curl http://localhost:8000/debug

# Monitor queue status and system load
curl http://localhost:8000/api/queue-status
```

### **Required GitHub Secrets Reference**

Your GitHub Repository Secrets should have **exactly** these names and formats:

```
Secret Name: SUPABASE_URL
Format: https://your-project.supabase.co
Example: https://abcdefghijk.supabase.co

Secret Name: SUPABASE_KEY  
Format: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Note: Use the anon/public key, NOT the service_role key

Secret Name: B2_APPLICATION_KEY_ID
Format: 005a1b2c3d4e5f6789abcdef
Length: ~25 characters

Secret Name: B2_APPLICATION_KEY
Format: K005abcdef1234567890...
Length: ~40+ characters

Secret Name: B2_BUCKET_NAME
Format: my-youtube-videos
Rules: Lowercase, numbers, hyphens, underscores only

Secret Name: B2_ENDPOINT_URL
Format: https://s3.us-west-004.backblazeb2.com
Note: Replace region as needed for your B2 bucket
```

### **Testing Checklist**

Before deploying, verify:

- [ ] **GitHub Secrets**: All 6 secrets added with correct names
- [ ] **Test Workflow**: Passes all steps without errors
- [ ] **Local Verification**: `python verify_secrets.py` shows valid config
- [ ] **Setup Test**: `python test_setup.py` passes all components
- [ ] **Health Endpoints**: Return successful responses
- [ ] **Simple Demo**: `python simple_demo.py` works for metadata
- [ ] **Database Schema**: Applied to your Supabase project

### **Common Issues & Solutions**

| Issue | Solution |
|-------|----------|
| "Missing configuration" | Check GitHub secret names match exactly |
| "Invalid Supabase key" | Use anon/public key, not service_role key |
| "B2 upload failed" | Verify bucket name and endpoint URL region |
| "Redis connection failed" | Install and start Redis locally |
| "yt-dlp not found" | Run `pip install yt-dlp` |
| "FFmpeg not found" | Install FFmpeg for your OS |

### **Debugging Tips**

1. **Check logs**: Look in `logs/youtube_scraper.log` and `logs/errors.log`
2. **Use debug endpoint**: Visit `/debug` to see configuration status
3. **Test incrementally**: Start with simple demo, then full system
4. **Monitor workflows**: GitHub Actions will show exact error messages
5. **Validate secrets**: Use the verification script before deployment

This comprehensive testing approach ensures your system works correctly before processing real YouTube videos!

📖 **For detailed testing instructions, see [TESTING.md](TESTING.md)**

## Database Schema

The system uses the following main tables:

- **youtube_urls**: Stores submitted YouTube URLs
- **videos**: Stores individual video metadata
- **scraping_jobs**: Tracks background processing jobs
- **url_videos**: Links videos to their source URLs

## File Structure

```
youtube-scraper/
├── main.py                 # FastAPI web application
├── models.py              # Pydantic models
├── database.py            # Database operations
├── youtube_parser.py      # URL parsing and validation
├── scraper.py             # Video scraping logic
├── storage.py             # Backblaze B2 integration
├── celery_app.py          # Celery configuration
├── tasks.py               # Background tasks
├── logging_config.py      # Logging setup
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── database/
│   └── schema.sql        # Database schema
└── templates/            # HTML templates
    ├── base.html
    ├── index.html
    └── dashboard.html
```

## Monitoring and Logging

- Logs are stored in the `logs/` directory
- Main log: `logs/youtube_scraper.log`
- Error log: `logs/errors.log`
- Web interface provides real-time job monitoring
- Dashboard shows statistics and recent activity

## Error Handling

The system includes comprehensive error handling:

- Invalid URLs are rejected with helpful error messages
- Failed downloads are logged and marked as failed
- Network errors are retried automatically
- Large files exceeding the size limit are skipped
- Database connection issues are handled gracefully

## Performance Considerations

- Videos are processed one at a time to avoid overwhelming YouTube's servers
- File size limits prevent storage of extremely large files
- Temporary files are cleaned up after processing
- Database connections are pooled for efficiency

## Security

- Environment variables are used for sensitive configuration
- Database queries use parameterized statements
- File uploads are validated and sanitized
- CORS is configured appropriately for the web interface

## Troubleshooting

### Quick Test

First, test if metadata extraction works:

```bash
python simple_demo.py
```

This will start a simplified demo on `http://localhost:8001` that only tests YouTube metadata extraction without external dependencies.

### Common Issues

1. **Internal Server Error**
   - Check `/health` endpoint: `http://localhost:8000/health`
   - Check `/debug` endpoint: `http://localhost:8000/debug`
   - Look at logs in `logs/youtube_scraper.log`

2. **"yt-dlp not found"**: 
   ```bash
   pip install yt-dlp
   ```

3. **"FFmpeg not found"**: Install FFmpeg for your operating system
   ```bash
   # Ubuntu/Debian
   sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   ```

4. **Database connection error**: 
   - Ensure Supabase credentials are correct in `.env`
   - Run the database schema in Supabase SQL editor
   - Check network connectivity to Supabase

5. **Redis connection error**: 
   ```bash
   # Install and start Redis
   sudo apt install redis-server
   sudo systemctl start redis-server
   
   # Test Redis connection
   redis-cli ping
   ```

6. **Metadata extraction fails**:
   - YouTube may be rate-limiting or blocking requests
   - Try different videos/channels
   - Check if yt-dlp is up to date: `pip install --upgrade yt-dlp`
   - **Important**: We use yt-dlp scraping, NOT YouTube API
   - This means no API keys needed, but subject to web scraping limitations

### Step-by-Step Debugging

1. **Test setup verification**:
   ```bash
   python test_setup.py
   ```

2. **Test metadata extraction only**:
   ```bash
   python simple_demo.py
   # Open http://localhost:8001
   ```

3. **Check component health**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/debug
   ```

4. **Check logs**:
   ```bash
   tail -f logs/youtube_scraper.log
   tail -f logs/errors.log
   ```

### Debug Mode

Enable debug logging by setting the log level to DEBUG in `logging_config.py`.

## 📋 Key Design Decisions & Rationale

### **Why yt-dlp instead of YouTube API?**
- ✅ **No API keys required** - Easier setup and deployment
- ✅ **No rate limits** - YouTube API has strict quotas
- ✅ **More metadata** - Can extract details not available via API
- ✅ **Private videos** - Can access unlisted/private videos if accessible
- ✅ **Cost effective** - No API usage costs
- ⚠️ **Trade-off**: Subject to YouTube's anti-scraping measures

### **Why immediate database entry + background processing?**
- ✅ **User experience** - Immediate feedback and confirmation
- ✅ **System reliability** - URLs saved even if processing fails
- ✅ **Scalability** - Can handle high volume without blocking
- ✅ **Monitoring** - Users can track progress in real-time
- ✅ **Recovery** - Failed jobs can be retried

### **Why automatic file cleanup?**
- ✅ **Disk space** - Prevents server storage from filling up
- ✅ **Cost efficiency** - Only cloud storage costs, no local storage
- ✅ **Security** - No sensitive content stored locally
- ✅ **Scalability** - Can process unlimited videos without disk limits

### **Why rate limiting?**
- ✅ **System protection** - Prevents overload during traffic spikes
- ✅ **YouTube compliance** - Avoids triggering anti-bot measures
- ✅ **Resource management** - Ensures fair usage across users
- ✅ **Stability** - Maintains consistent performance

## 🔧 Production Deployment Tips

1. **Multiple Workers**: Run 3-5 Celery workers for better throughput
2. **Monitor Queues**: Use `/api/queue-status` endpoint for health checks
3. **Log Monitoring**: Set up alerts for error log patterns
4. **Backup Strategy**: Regular database backups (videos safe in B2)
5. **Rate Limit Tuning**: Adjust limits based on your user base
6. **Resource Monitoring**: Watch CPU/memory usage during peak times

## ❓ Frequently Asked Questions

### **Q: Do videos get deleted from the server after upload?**
**A: Yes!** Videos are automatically deleted immediately after successful upload to Backblaze B2. The server maintains near-zero disk usage.

### **Q: Does this use the YouTube API?**
**A: No!** We use yt-dlp for web scraping instead. This means no API keys needed, no rate limits, and access to more metadata.

### **Q: What happens when too many URLs are submitted quickly?**
**A: The system has built-in protections:**
- Rate limiting (10 URLs/minute per IP)
- Queue management with priorities
- Graceful degradation if overloaded
- URLs are saved immediately, processing happens in background

### **Q: Can it handle private or unlisted videos?**
**A: Yes!** Unlike the YouTube API, yt-dlp can access private/unlisted videos if they're accessible to the scraping process.

### **Q: What video quality does it download?**
**A: Highest available quality** - typically 1080p or 4K depending on what's available for each video.

### **Q: How do I scale for high volume?**
**A: Multiple approaches:**
- Run multiple Celery workers
- Increase worker concurrency
- Monitor `/api/queue-status` for bottlenecks
- Adjust rate limits as needed

### **Q: What if the system gets an internal server error?**
**A: Debug steps:**
1. Check `/health` endpoint for component status
2. Check `/debug` endpoint for configuration issues
3. Run `python test_setup.py` to verify setup
4. Try `python simple_demo.py` to test metadata extraction only

### **Q: How much storage space is needed?**
**A: Minimal!** Videos are only stored temporarily during upload. Permanent storage is in Backblaze B2 cloud.

### **Q: How do I verify my GitHub secrets are configured correctly?**
**A: Multiple ways:**
1. **Best**: Run the "Test GitHub Secrets Configuration" workflow in GitHub Actions
2. **Local**: Run `python verify_secrets.py` to check format and get instructions
3. **Quick**: Check `/health` and `/debug` endpoints once app is running
4. **Component**: Test individual parts with the manual commands in the Testing section

### **Q: The test workflow failed, what does each step mean?**
**A: Each step tests a specific component:**
- **Configuration Loading**: Your secrets are present and valid format
- **Database Connection**: Supabase URL and key work correctly  
- **B2 Configuration**: Backblaze credentials and bucket are accessible
- **YouTube Parser**: yt-dlp can extract metadata from YouTube
- If any step fails, that specific component needs attention

### **Q: Can I test the system without setting up all the external services?**
**A: Yes!** Use the simple demo:
```bash
python simple_demo.py  # Test only YouTube metadata extraction
```
This works without Supabase, Backblaze B2, or Redis - just yt-dlp.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloading
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Celery](https://docs.celeryq.dev/) for background processing
- [Supabase](https://supabase.com/) for the database
- [Backblaze B2](https://www.backblaze.com/b2/) for cloud storage