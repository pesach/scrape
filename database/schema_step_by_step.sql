-- YouTube Video Scraper Database Schema - Step by Step
-- =====================================================
-- If the main schema.sql fails, run these commands one by one in Supabase SQL Editor
--
-- STEP 1: Create the enums first (MOST IMPORTANT!)
-- Copy and paste this entire block:

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

-- STEP 2: Create youtube_urls table
-- Copy and paste this:

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

-- STEP 3: Create videos table
-- Copy and paste this:

CREATE TABLE IF NOT EXISTS videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    duration INTEGER,
    view_count BIGINT,
    like_count BIGINT,
    upload_date DATE,
    uploader TEXT,
    uploader_id TEXT,
    thumbnail_url TEXT,
    tags TEXT[],
    categories TEXT[],
    resolution TEXT,
    fps INTEGER,
    file_size BIGINT,
    format_id TEXT,
    b2_file_key TEXT,
    b2_file_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- STEP 4: Create scraping_jobs table
-- Copy and paste this:

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

-- STEP 5: Create url_videos junction table
-- Copy and paste this:

CREATE TABLE IF NOT EXISTS url_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_url_id UUID REFERENCES youtube_urls(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(youtube_url_id, video_id)
);

-- STEP 6: Create indexes for performance
-- Copy and paste this:

CREATE INDEX IF NOT EXISTS idx_youtube_urls_url_type ON youtube_urls(url_type);
CREATE INDEX IF NOT EXISTS idx_youtube_urls_submitted_at ON youtube_urls(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_youtube_id ON videos(youtube_id);
CREATE INDEX IF NOT EXISTS idx_videos_uploader ON videos(uploader);
CREATE INDEX IF NOT EXISTS idx_videos_upload_date ON videos(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_youtube_url_id ON scraping_jobs(youtube_url_id);
CREATE INDEX IF NOT EXISTS idx_url_videos_youtube_url_id ON url_videos(youtube_url_id);
CREATE INDEX IF NOT EXISTS idx_url_videos_video_id ON url_videos(video_id);

-- STEP 7: Create update trigger function
-- Copy and paste this:

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- STEP 8: Create triggers
-- Copy and paste this:

DROP TRIGGER IF EXISTS update_youtube_urls_updated_at ON youtube_urls;
CREATE TRIGGER update_youtube_urls_updated_at 
    BEFORE UPDATE ON youtube_urls
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_videos_updated_at ON videos;
CREATE TRIGGER update_videos_updated_at 
    BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_scraping_jobs_updated_at ON scraping_jobs;
CREATE TRIGGER update_scraping_jobs_updated_at 
    BEFORE UPDATE ON scraping_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- STEP 9: Verify everything was created
-- Copy and paste this:

SELECT 
    'Tables created successfully!' as status,
    COUNT(*) as table_count
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('youtube_urls', 'videos', 'scraping_jobs', 'url_videos');

-- List all your tables
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('youtube_urls', 'videos', 'scraping_jobs', 'url_videos')
ORDER BY table_name;