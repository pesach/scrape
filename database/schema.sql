-- YouTube Video Scraper Database Schema
-- =====================================
-- This script automatically detects your database setup and applies the correct schema:
-- - If you have NO videos table: Creates complete new schema
-- - If you have EXISTING videos table: Adds missing columns and creates new tables
--
-- USAGE: Copy this entire file and run it in Supabase SQL Editor as one script

BEGIN;

-- Create enums (safe to run multiple times)
DO $$ BEGIN
    CREATE TYPE url_type AS ENUM ('video', 'channel', 'playlist', 'user');
EXCEPTION
    WHEN duplicate_object THEN 
        RAISE NOTICE '✅ url_type enum already exists, skipping';
END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN 
        RAISE NOTICE '✅ job_status enum already exists, skipping';
END $$;

-- Check if videos table exists and create/modify accordingly
DO $$ 
DECLARE
    videos_table_exists BOOLEAN;
BEGIN
    -- Check if videos table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'videos'
    ) INTO videos_table_exists;

    IF videos_table_exists THEN
        RAISE NOTICE '🔄 Found existing videos table - running migration mode';
        
        -- Add missing columns to existing videos table (safe operations)
        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS youtube_id TEXT;
            RAISE NOTICE '✅ Added youtube_id column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ youtube_id column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS uploader TEXT;
            RAISE NOTICE '✅ Added uploader column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ uploader column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS uploader_id TEXT;
            RAISE NOTICE '✅ Added uploader_id column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ uploader_id column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS upload_date DATE;
            RAISE NOTICE '✅ Added upload_date column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ upload_date column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS resolution TEXT;
            RAISE NOTICE '✅ Added resolution column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ resolution column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS fps INTEGER;
            RAISE NOTICE '✅ Added fps column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ fps column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS file_size BIGINT;
            RAISE NOTICE '✅ Added file_size column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ file_size column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS format_id TEXT;
            RAISE NOTICE '✅ Added format_id column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ format_id column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS b2_file_key TEXT;
            RAISE NOTICE '✅ Added b2_file_key column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ b2_file_key column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS b2_file_url TEXT;
            RAISE NOTICE '✅ Added b2_file_url column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ b2_file_url column may already exist';
        END;

        BEGIN
            ALTER TABLE videos ADD COLUMN IF NOT EXISTS categories TEXT[];
            RAISE NOTICE '✅ Added categories column';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ categories column may already exist';
        END;

        -- Create unique index on youtube_id if it doesn't exist
        BEGIN
            CREATE UNIQUE INDEX IF NOT EXISTS idx_videos_youtube_id ON videos(youtube_id) WHERE youtube_id IS NOT NULL;
            RAISE NOTICE '✅ Created unique index on youtube_id';
        EXCEPTION WHEN OTHERS THEN 
            RAISE NOTICE '⚠️ Index on youtube_id may already exist';
        END;

    ELSE
        RAISE NOTICE '🆕 No existing videos table found - creating new schema';
        
        -- Create new videos table with complete structure
        CREATE TABLE videos (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            youtube_id TEXT UNIQUE NOT NULL,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            duration INTEGER, -- in seconds
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
            file_size BIGINT, -- in bytes
            format_id TEXT,
            b2_file_key TEXT, -- key in Backblaze B2
            b2_file_url TEXT, -- public URL in B2
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        RAISE NOTICE '✅ Created new videos table';
    END IF;
END $$;

-- Create youtube_urls table (always needed)
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

-- Create scraping_jobs table (always needed)
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

-- Create url_videos junction table (always needed)
CREATE TABLE IF NOT EXISTS url_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_url_id UUID REFERENCES youtube_urls(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(youtube_url_id, video_id)
);

-- Create indexes for performance (safe to run multiple times)
CREATE INDEX IF NOT EXISTS idx_youtube_urls_url_type ON youtube_urls(url_type);
CREATE INDEX IF NOT EXISTS idx_youtube_urls_submitted_at ON youtube_urls(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_uploader ON videos(uploader);
CREATE INDEX IF NOT EXISTS idx_videos_upload_date ON videos(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_youtube_url_id ON scraping_jobs(youtube_url_id);
CREATE INDEX IF NOT EXISTS idx_url_videos_youtube_url_id ON url_videos(youtube_url_id);
CREATE INDEX IF NOT EXISTS idx_url_videos_video_id ON url_videos(video_id);

-- Create update trigger function (safe to run multiple times)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers (safe to run multiple times)
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

COMMIT;

-- Final verification and summary
DO $$
DECLARE
    table_count INTEGER;
    videos_columns TEXT[];
BEGIN
    -- Count tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('youtube_urls', 'videos', 'scraping_jobs', 'url_videos');

    -- Get videos table columns
    SELECT ARRAY_AGG(column_name ORDER BY ordinal_position) INTO videos_columns
    FROM information_schema.columns 
    WHERE table_name = 'videos' AND table_schema = 'public';

    RAISE NOTICE '';
    RAISE NOTICE '🎉 SCHEMA SETUP COMPLETE!';
    RAISE NOTICE '================================';
    RAISE NOTICE 'Tables created/updated: %', table_count;
    RAISE NOTICE 'Videos table columns: %', array_length(videos_columns, 1);
    RAISE NOTICE '';
    
    IF table_count = 4 THEN
        RAISE NOTICE '✅ SUCCESS: All required tables are ready!';
        RAISE NOTICE '✅ youtube_urls - Track submitted URLs';
        RAISE NOTICE '✅ videos - Store video metadata and files';
        RAISE NOTICE '✅ scraping_jobs - Monitor background tasks';  
        RAISE NOTICE '✅ url_videos - Link URLs to their videos';
    ELSE
        RAISE NOTICE '⚠️  WARNING: Expected 4 tables, found %', table_count;
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Ready to start scraping YouTube videos!';
END $$;