-- Supabase schema for videos table
-- Run this in your Supabase SQL editor to create the required table

CREATE TABLE IF NOT EXISTS videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    youtube_id VARCHAR(255) UNIQUE NOT NULL,
    b2_url TEXT,
    title TEXT,
    description TEXT,
    duration INTEGER,
    uploader VARCHAR(255),
    upload_date VARCHAR(20),
    view_count BIGINT,
    like_count BIGINT,
    thumbnail TEXT,
    file_size BIGINT,
    file_name TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_videos_youtube_id ON videos(youtube_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC);

-- Create a trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Optional: Row Level Security (RLS)
-- Uncomment and modify based on your security requirements
-- ALTER TABLE videos ENABLE ROW LEVEL SECURITY;

-- Example RLS policy for authenticated users to read all videos
-- CREATE POLICY "Allow authenticated users to read videos" ON videos
--     FOR SELECT
--     TO authenticated
--     USING (true);

-- Example RLS policy for service role to manage videos
-- CREATE POLICY "Allow service role full access" ON videos
--     FOR ALL
--     TO service_role
--     USING (true);