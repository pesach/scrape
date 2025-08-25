-- Migration: Add status tracking to videos table
-- This enables distributed processing of videos across multiple workers

BEGIN;

-- Create video_status enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE video_status AS ENUM ('pending', 'fetching', 'done', 'failed');
EXCEPTION
    WHEN duplicate_object THEN 
        RAISE NOTICE 'video_status enum already exists, skipping';
END $$;

-- Add status column to videos table
ALTER TABLE videos 
ADD COLUMN IF NOT EXISTS status video_status DEFAULT 'pending';

-- Create index for efficient status queries
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);

-- Update existing videos to have appropriate status
-- Videos with b2_file_url are considered done
UPDATE videos 
SET status = 'done' 
WHERE b2_file_url IS NOT NULL AND status = 'pending';

-- Videos without b2_file_url are pending
UPDATE videos 
SET status = 'pending' 
WHERE b2_file_url IS NULL AND status IS NULL;

COMMIT;

-- Verify the migration
SELECT 
    status, 
    COUNT(*) as count 
FROM videos 
GROUP BY status 
ORDER BY status;
