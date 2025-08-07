# 🔄 Using YouTube Scraper with Existing Videos Table

If you already have a `videos` table in your Supabase database, this guide will help you integrate the YouTube Video Scraper without losing your existing data.

## 📋 **Your Current Table Structure**

Based on your existing `videos` table with columns:
- `id`, `createdat`, `updatedat`, `title`, `description`, `videourl`, `thumbnailurl`, `duration`
- `userid`, `channelid`, `category`, `tags`, `status`, `privacy`, `viewcount`, `likes`, `dislikes`
- `allowdownloads`, `likecount`, `dislikecount`, `commentcount`

## 🔧 **Migration Steps**

### **Step 1: Run Migration Script**
1. Go to **Supabase → SQL Editor**
2. Copy and paste the contents of `database/migration_existing_videos.sql`
3. Run the script

**What this does:**
- ✅ Creates new tables: `youtube_urls`, `scraping_jobs`, `url_videos`
- ✅ Adds new columns to your existing `videos` table (safely)
- ✅ Creates indexes and triggers for performance
- ✅ **Does NOT** modify your existing video data

### **Step 2: Use the Database Adapter**
The system includes a special adapter (`database_adapter.py`) that maps between the scraper's expected format and your existing table structure.

**Column Mapping:**
| Scraper Expects | Your Table Has | Notes |
|----------------|---------------|--------|
| `url` | `videourl` | Main video URL |
| `thumbnail_url` | `thumbnailurl` | Video thumbnail |
| `view_count` | `viewcount` | View statistics |
| `like_count` | `likecount` | Like statistics |
| `uploader_id` | `channelid` | Channel/uploader ID |

### **Step 3: Configure the Application**
The scraper will automatically detect and use your existing table structure. No code changes needed!

## 🆕 **New Columns Added**

The migration adds these columns to your existing `videos` table:
- `youtube_id` - Unique YouTube video identifier
- `uploader` - Channel/uploader name
- `uploader_id` - Channel ID (maps to your `channelid`)
- `upload_date` - When video was uploaded to YouTube
- `resolution` - Video quality (1080p, 720p, etc.)
- `fps` - Frames per second
- `file_size` - Downloaded file size in bytes
- `format_id` - yt-dlp format identifier
- `b2_file_key` - Backblaze B2 storage key
- `b2_file_url` - Public URL in B2 storage
- `categories` - YouTube categories (array)

**Note:** These are added as optional columns. Your existing data remains unchanged.

## 📊 **New Tables Created**

1. **`youtube_urls`** - Tracks submitted URLs (videos, channels, playlists)
2. **`scraping_jobs`** - Background job status and progress
3. **`url_videos`** - Links submitted URLs to downloaded videos

## 🔍 **How It Works**

1. **User submits URL** → Saved in `youtube_urls` table
2. **Background job created** → Tracked in `scraping_jobs` table  
3. **Videos downloaded** → Saved in your existing `videos` table
4. **Relationships created** → Linked via `url_videos` table

## ✅ **Benefits of This Approach**

- **✅ No data loss** - Your existing videos are preserved
- **✅ Seamless integration** - New scraped videos use same table
- **✅ Backward compatible** - Your existing app continues to work
- **✅ Enhanced features** - Adds YouTube-specific metadata
- **✅ Job tracking** - Monitor scraping progress and status

## 🧪 **Testing the Integration**

After running the migration:

1. **Check tables exist:**
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_name IN ('youtube_urls', 'scraping_jobs', 'url_videos');
   ```

2. **Verify new columns:**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'videos' 
   AND column_name IN ('youtube_id', 'uploader', 'b2_file_key');
   ```

3. **Test the scraper:**
   - Start the application
   - Submit a YouTube URL
   - Check that it appears in your existing `videos` table

## 🔧 **Customization Options**

If you need to modify the column mapping:

1. Edit `database_adapter.py`
2. Update the `map_to_existing_structure()` function
3. Change the mapping between scraper fields and your table columns

**Example:**
```python
# In database_adapter.py
mapped = {
    'title': video_data.get('title'),
    'videourl': video_data.get('url'),
    # Add your custom mappings here
}
```

## ⚠️ **Important Notes**

- **Backup first:** Always backup your database before running migrations
- **Test thoroughly:** Verify the integration works with your existing app
- **Monitor storage:** Video files are stored in Backblaze B2, not your database
- **Column types:** Some columns might need type conversion (e.g., tags array)

## 🚀 **Ready to Use**

Once the migration is complete, the YouTube Video Scraper will:
- Work seamlessly with your existing `videos` table
- Add new YouTube videos alongside your existing content
- Provide enhanced metadata and tracking capabilities
- Maintain full compatibility with your current application

Your existing video data remains untouched while gaining powerful YouTube scraping capabilities! 🎉