-- Migration Script for Existing Videos Table
-- ==========================================
-- This script adapts the YouTube Video Scraper to work with your existing videos table
-- and creates only the additional tables needed.

BEGIN;

-- Create enums if they don't exist
DO $$ BEGIN
    CREATE TYPE url_type AS ENUM ('video', 'channel', 'playlist', 'user');
EXCEPTION
    WHEN duplicate_object THEN 
        RAISE NOTICE 'Type url_type already exists, skipping';
END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN 
        RAISE NOTICE 'Type job_status already exists, skipping';
END $$;

-- Create youtube_urls table (for tracking submitted URLs)
CREATE TABLE IF NOT EXISTS youtube_urls (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    url TEXT NOT NULL,
    url_type url_type NOT NULL,
    title TEXT,
    description TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create scraping_jobs table (for tracking background jobs)
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_url_id UUID REFERENCES youtube_urls(id) ON DELETE CASCADE,
    status job_status DEFAULT 'pending',
    progress_percent INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add missing columns to your existing videos table (if they don't exist)
-- These columns are needed for the YouTube scraper functionality

-- Add youtube_id column for unique YouTube video identification
DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN youtube_id TEXT;
    CREATE UNIQUE INDEX idx_videos_youtube_id ON videos(youtube_id) WHERE youtube_id IS NOT NULL;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column youtube_id already exists, skipping';
    WHEN duplicate_table THEN 
        RAISE NOTICE 'Index idx_videos_youtube_id already exists, skipping';
END $$;

-- Add uploader information
DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN uploader TEXT;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column uploader already exists, skipping';
END $$;

DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN uploader_id TEXT;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column uploader_id already exists, skipping';
END $$;

-- Add upload_date
DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN upload_date DATE;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column upload_date already exists, skipping';
END $$;

-- Add video quality information
DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN resolution TEXT;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column resolution already exists, skipping';
END $$;

DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN fps INTEGER;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column fps already exists, skipping';
END $$;

DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN file_size BIGINT;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column file_size already exists, skipping';
END $$;

DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN format_id TEXT;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column format_id already exists, skipping';
END $$;

-- Add Backblaze B2 storage information
DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN b2_file_key TEXT;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column b2_file_key already exists, skipping';
END $$;

DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN b2_file_url TEXT;
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column b2_file_url already exists, skipping';
END $$;

-- Convert tags column to array if it's not already
-- Note: This depends on your current tags format
DO $$ BEGIN
    -- Check if tags is already an array type
    IF (SELECT data_type FROM information_schema.columns 
        WHERE table_name = 'videos' AND column_name = 'tags') != 'ARRAY' THEN
        -- If tags is text, you might want to convert it to array
        -- Uncomment and modify this if needed:
        -- ALTER TABLE videos ALTER COLUMN tags TYPE TEXT[] USING string_to_array(tags, ',');
        RAISE NOTICE 'Tags column exists but may need manual conversion to array type';
    END IF;
EXCEPTION
    WHEN others THEN 
        RAISE NOTICE 'Could not check tags column type';
END $$;

-- Add categories as array if not exists
DO $$ BEGIN
    ALTER TABLE videos ADD COLUMN categories TEXT[];
EXCEPTION
    WHEN duplicate_column THEN 
        RAISE NOTICE 'Column categories already exists, skipping';
END $$;

-- Create junction table linking URLs to videos (for playlists/channels)
CREATE TABLE IF NOT EXISTS url_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_url_id UUID REFERENCES youtube_urls(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(youtube_url_id, video_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_youtube_urls_url_type ON youtube_urls(url_type);
CREATE INDEX IF NOT EXISTS idx_youtube_urls_submitted_at ON youtube_urls(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_uploader ON videos(uploader);
CREATE INDEX IF NOT EXISTS idx_videos_upload_date ON videos(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_youtube_url_id ON scraping_jobs(youtube_url_id);
CREATE INDEX IF NOT EXISTS idx_url_videos_youtube_url_id ON url_videos(youtube_url_id);
CREATE INDEX IF NOT EXISTS idx_url_videos_video_id ON url_videos(video_id);

-- Create update trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for new tables (your existing videos table might already have triggers)
DROP TRIGGER IF EXISTS update_youtube_urls_updated_at ON youtube_urls;
CREATE TRIGGER update_youtube_urls_updated_at 
    BEFORE UPDATE ON youtube_urls
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_scraping_jobs_updated_at ON scraping_jobs;
CREATE TRIGGER update_scraping_jobs_updated_at 
    BEFORE UPDATE ON scraping_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add trigger for videos table if it doesn't exist
DO $$ BEGIN
    DROP TRIGGER IF EXISTS update_videos_updated_at ON videos;
    CREATE TRIGGER update_videos_updated_at 
        BEFORE UPDATE ON videos
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION
    WHEN others THEN 
        RAISE NOTICE 'Could not create trigger for videos table, may already exist';
END $$;

COMMIT;

-- Verification
SELECT 'Migration completed successfully!' as status;

-- Show table structure
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'videos'
ORDER BY ordinal_position;