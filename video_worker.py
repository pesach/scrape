#!/usr/bin/env python3
"""
Video Processing Worker with status tracking for distributed processing.
"""

import os
import asyncio
import logging
from database import db
from models import VideoStatus

logging.basicConfig(level="INFO")
logger = logging.getLogger("video_worker")

class VideoWorker:
    def __init__(self):
        self.batch_size = 5
        self.sleep_empty = 30
        
    async def process_video(self, video):
        """Process a single video with status tracking"""
        video_id = video.id
        
        # Mark as fetching (atomic update)
        updated = await db.mark_video_as_fetching(video_id)
        if not updated:
            return False
        
        # Process video here...
        # Mark as done when complete
        await db.update_video_status(video_id, VideoStatus.DONE)
        return True
    
    async def run(self):
        """Main worker loop"""
        while True:
            videos = await db.get_pending_videos(self.batch_size)
            if not videos:
                await asyncio.sleep(self.sleep_empty)
                continue
            
            for video in videos:
                await self.process_video(video)
                await asyncio.sleep(2)

if __name__ == "__main__":
    worker = VideoWorker()
    asyncio.run(worker.run())
