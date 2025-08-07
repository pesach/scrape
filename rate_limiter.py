import time
import asyncio
from typing import Dict, Optional
from fastapi import HTTPException
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter to prevent system overload"""
    
    def __init__(self):
        # Track requests per IP/user
        self.request_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Rate limits (requests per time window)
        self.limits = {
            'submit_url': {'count': 10, 'window': 60},      # 10 URLs per minute
            'validate_url': {'count': 30, 'window': 60},    # 30 validations per minute
            'dashboard': {'count': 60, 'window': 60},       # 60 dashboard requests per minute
        }
    
    async def check_rate_limit(self, client_ip: str, endpoint: str) -> bool:
        """Check if request is within rate limits"""
        if endpoint not in self.limits:
            return True  # No limit for this endpoint
        
        limit_config = self.limits[endpoint]
        current_time = time.time()
        
        # Get request history for this IP and endpoint
        key = f"{client_ip}:{endpoint}"
        history = self.request_history[key]
        
        # Remove old requests outside the time window
        cutoff_time = current_time - limit_config['window']
        while history and history[0] < cutoff_time:
            history.popleft()
        
        # Check if limit exceeded
        if len(history) >= limit_config['count']:
            logger.warning(f"Rate limit exceeded for {client_ip} on {endpoint}")
            return False
        
        # Add current request
        history.append(current_time)
        return True
    
    def get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

class SystemLoadMonitor:
    """Monitor system load and queue status"""
    
    def __init__(self):
        self.max_queue_size = 1000
        self.max_concurrent_jobs = 5
        self.current_jobs = 0
    
    async def check_system_capacity(self) -> tuple[bool, str]:
        """Check if system can handle new requests"""
        
        # Check Redis queue size (if available)
        try:
            import redis
            import os
            redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            queue_size = redis_client.llen("celery")
            
            if queue_size > self.max_queue_size:
                return False, f"Queue full ({queue_size} jobs pending)"
        except Exception as e:
            logger.warning(f"Could not check queue size: {e}")
        
        # Check database connections (simplified)
        try:
            from database import db
            await db.get_youtube_urls(limit=1)
        except Exception as e:
            return False, f"Database unavailable: {str(e)}"
        
        return True, "System ready"

# Global instances
rate_limiter = RateLimiter()
load_monitor = SystemLoadMonitor()

# Middleware function
async def check_request_limits(request, endpoint: str):
    """Check both rate limits and system capacity"""
    
    # Check rate limits
    client_ip = rate_limiter.get_client_ip(request)
    if not await rate_limiter.check_rate_limit(client_ip, endpoint):
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please wait before trying again.",
                "retry_after": 60
            }
        )
    
    # Check system capacity for resource-intensive operations
    if endpoint in ['submit_url']:
        can_handle, message = await load_monitor.check_system_capacity()
        if not can_handle:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "System overloaded", 
                    "message": message,
                    "retry_after": 300
                }
            )

class QueueManager:
    """Manage job priorities and queue health"""
    
    def __init__(self):
        self.priority_queues = {
            'high': 'priority_high',    # Single videos
            'normal': 'scraping',       # Playlists/channels
            'low': 'cleanup'            # Maintenance tasks
        }
    
    def get_queue_for_url_type(self, url_type: str) -> str:
        """Determine appropriate queue based on URL type"""
        if url_type == 'video':
            return self.priority_queues['high']  # Single videos process faster
        else:
            return self.priority_queues['normal']  # Playlists/channels take longer
    
    async def get_queue_stats(self) -> dict:
        """Get statistics about queue health"""
        try:
            import redis
            import os
            redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            
            stats = {}
            for name, queue in self.priority_queues.items():
                stats[name] = redis_client.llen(queue)
            
            return {
                "queues": stats,
                "total_pending": sum(stats.values()),
                "status": "healthy" if sum(stats.values()) < 500 else "overloaded"
            }
        except Exception as e:
            return {"error": str(e), "status": "unknown"}

# Global queue manager
queue_manager = QueueManager()