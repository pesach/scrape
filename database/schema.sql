-- Create enum for URL types
CREATE TYPE url_type AS ENUM ('video', 'channel', 'playlist', 'user');

-- Create enum for job status
CREATE TYPE job_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');

-- Create table for YouTube URLs submitted by users
CREATE TABLE youtube_urls (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    url TEXT NOT NULL,
    url_type url_type NOT NULL,
    title TEXT,
    description TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for individual videos
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

-- Create table for scraping jobs
CREATE TABLE scraping_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_url_id UUID REFERENCES youtube_urls(id) ON DELETE CASCADE,
    status job_status DEFAULT 'pending',
    progress_percent INTEGER DEFAULT 0,
    videos_found INTEGER DEFAULT 0,
    videos_processed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create junction table for videos belonging to URLs (for playlists/channels)
CREATE TABLE url_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_url_id UUID REFERENCES youtube_urls(id) ON DELETE CASCADE,
    video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
    position INTEGER, -- for playlists
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(youtube_url_id, video_id)
);

-- Create indexes for better performance
CREATE INDEX idx_youtube_urls_url ON youtube_urls(url);
CREATE INDEX idx_youtube_urls_type ON youtube_urls(url_type);
CREATE INDEX idx_videos_youtube_id ON videos(youtube_id);
CREATE INDEX idx_videos_uploader ON videos(uploader);
CREATE INDEX idx_scraping_jobs_status ON scraping_jobs(status);
CREATE INDEX idx_scraping_jobs_youtube_url_id ON scraping_jobs(youtube_url_id);
CREATE INDEX idx_url_videos_youtube_url_id ON url_videos(youtube_url_id);
CREATE INDEX idx_url_videos_video_id ON url_videos(video_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_youtube_urls_updated_at BEFORE UPDATE ON youtube_urls FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_scraping_jobs_updated_at BEFORE UPDATE ON scraping_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();