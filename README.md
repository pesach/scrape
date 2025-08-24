# Video Processing Pipeline

A complete video processing system that downloads videos from YouTube, uploads them to Backblaze B2, updates Supabase with the video information, and cleans up local files.

## Features

- 📥 **YouTube Download**: Downloads videos from YouTube using yt-dlp
- ☁️ **Backblaze B2 Upload**: Automatically uploads videos to Backblaze B2 storage
- 🗄️ **Supabase Integration**: Updates video metadata and B2 URLs in Supabase
- 🧹 **Automatic Cleanup**: Deletes local files after successful upload
- 📊 **Progress Tracking**: Detailed logging and status updates
- ⚡ **Error Handling**: Robust error handling with automatic retry capabilities

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `B2_KEY_ID`: Your Backblaze B2 Key ID
- `B2_APP_KEY`: Your Backblaze B2 Application Key
- `B2_BUCKET_NAME`: Your B2 bucket name
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous key

### 3. Set Up Supabase Table

Run the SQL schema in your Supabase SQL editor:

```sql
-- See supabase_schema.sql for the complete schema
```

## Usage

### Video Processing Pipeline

Process a YouTube video through the complete pipeline:

```bash
# Basic usage
python video_processor.py "https://www.youtube.com/watch?v=VIDEO_ID"

# With verbose logging
python video_processor.py -v "https://www.youtube.com/watch?v=VIDEO_ID"

# Keep local file after upload
python video_processor.py --keep-local "https://www.youtube.com/watch?v=VIDEO_ID"

# Specify custom video ID for tracking
python video_processor.py --video-id "custom_id" "https://www.youtube.com/watch?v=VIDEO_ID"
```

The script will:
1. Download the video from YouTube
2. Upload it to your Backblaze B2 bucket
3. Update the Supabase database with the video information and B2 URL
4. Delete the local file (unless `--keep-local` is specified)

### Programmatic Usage

You can also use the VideoProcessor class in your own scripts:

```python
from video_processor import VideoProcessor

# Initialize the processor
processor = VideoProcessor(verbose=True)

# Process a video
result = processor.process_video(
    url="https://www.youtube.com/watch?v=VIDEO_ID",
    video_id="optional_custom_id",
    keep_local=False
)

print(f"Video uploaded to: {result['b2_url']}")
```

## Database Schema

The Supabase `videos` table stores:
- Video metadata (title, description, duration, etc.)
- YouTube information (ID, uploader, view count, etc.)
- B2 storage URL
- Processing status and timestamps
- Error messages for failed uploads

## Backblaze B2 Test Scripts

The repository also includes minimal test scripts for Backblaze B2:

### Bash Script

```bash
B2_KEY_ID=xxxx B2_APP_KEY=yyyy B2_BUCKET_NAME=my-bucket \
./scripts/test-backblaze.sh /path/to/local/file.txt optional-remote-name.txt
```

### Python Script

```bash
B2_KEY_ID=xxxx B2_APP_KEY=yyyy B2_BUCKET_NAME=my-bucket \
python scripts/test_backblaze_connection.py /path/to/local/file.txt optional-remote-name.txt
```

## Error Handling

The video processor includes comprehensive error handling:
- Automatic retry on network failures
- Graceful cleanup on errors
- Status updates in Supabase for failed uploads
- Detailed logging for debugging

## Security Notes

- Never commit your `.env` file with real credentials
- Use environment variables or secure secret management in production
- Consider using Supabase Row Level Security (RLS) for additional security
- Rotate your Backblaze and Supabase keys regularly

## License

MIT