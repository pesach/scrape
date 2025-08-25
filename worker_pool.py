# worker_poll.py
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
import httpx
import pathlib


# --- Load .env early ---
# Absolute path to your project .env
env_path = pathlib.Path(__file__).parent / ".env"
if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

# --- Logging setup ---
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("worker_poll")

# --- Config object ---
class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    B2_APPLICATION_KEY_ID = os.getenv("B2_APPLICATION_KEY_ID")
    B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
    B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
    SLEEP_EMPTY = int(os.getenv("WORKER_SLEEP_EMPTY", "10"))
    SLEEP_BETWEEN_JOBS = float(os.getenv("WORKER_SLEEP_BETWEEN_JOBS", "1"))

# --- Debug env check ---
def mask(secret: str | None, keep: int = 4) -> str:
    if not secret:
        return "<MISSING>"
    return secret[:keep] + "..." + secret[-keep:]

logger.info("Loaded env vars:")
logger.info(" SUPABASE_URL=%s", Config.SUPABASE_URL or "<MISSING>")
logger.info(" SUPABASE_KEY=%s", mask(Config.SUPABASE_KEY))
logger.info(" B2_APPLICATION_KEY_ID=%s", mask(Config.B2_APPLICATION_KEY_ID))
logger.info(" B2_BUCKET_NAME=%s", Config.B2_BUCKET_NAME or "<MISSING>")

# --- Imports after env setup ---
from database import db
from scraper import scraper
from models import JobStatus, URLType


async def fetch_youtube_url_by_id(youtube_url_id: str) -> str | None:
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        logger.error("SUPABASE_URL or SUPABASE_KEY missing; cannot fetch youtube_url by id.")
        return None

    endpoint = Config.SUPABASE_URL.rstrip("/") + "/rest/v1/youtube_urls"
    params = {"select": "url", "id": f"eq.{youtube_url_id}"}
    headers = {
        "apikey": Config.SUPABASE_KEY,
        "Authorization": f"Bearer {Config.SUPABASE_KEY}",
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(endpoint, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data and "url" in data[0]:
                return data[0]["url"]
            logger.warning("No url found in youtube_urls for id=%s (resp: %s)", youtube_url_id, data)
            return None
    except Exception as e:
        logger.exception("Failed to fetch youtube_url by id %s: %s", youtube_url_id, e)
        return None


async def process_job(job):
    job_id = getattr(job, "id", None)
    logger.info(f"[{job_id}] raw job object fields: {getattr(job, '__dict__', 'no __dict__')}")

    try:
        await db.update_scraping_job(job_id, {
            "status": JobStatus.PROCESSING.value,
            "started_at": datetime.utcnow().isoformat()
        })

        # --- URL RESOLUTION ---
        url = getattr(job, "url", None)

        if not url:
            try:
                job_map = (
                    job.dict() if hasattr(job, "dict")
                    else job.model_dump() if hasattr(job, "model_dump")
                    else dict(job.__dict__)
                )
                for key in ("url", "link", "source", "video_url", "youtube_url"):
                    if key in job_map and job_map[key]:
                        url = job_map[key]
                        break
                if not url and job_map.get("youtube_url_id"):
                    logger.info(f"[{job_id}] url missing; fetching from youtube_urls using id {job_map['youtube_url_id']}")
                    url = await fetch_youtube_url_by_id(job_map["youtube_url_id"])
            except Exception as e:
                logger.exception(f"[{job_id}] error while extracting url from job object: {e}")

        if not url:
            raise ValueError("Could not resolve URL for job. job fields logged above.")

        logger.info(f"[{job_id}] Resolved url: {url}")

        # --- URL TYPE RESOLUTION ---
        url_type_enum = None
        if hasattr(job, "url_type"):
            try:
                url_type_enum = URLType(job.url_type)
            except Exception:
                url_type_enum = None

        if url and "watch?v=" in url and url_type_enum != URLType.VIDEO:
            logger.warning(f"[{job_id}] Overriding url_type={url_type_enum} → VIDEO")
            url_type_enum = URLType.VIDEO

        # --- SCRAPER CALL ---
        success, message, videos_processed = await scraper.scrape_url(
            url, url_type_enum, getattr(job, "youtube_url_id", None)
        )

        if success:
            await db.update_scraping_job(job_id, {
                "status": JobStatus.COMPLETED.value,
                "progress_percent": 100,
                "videos_processed": videos_processed,
                "completed_at": datetime.utcnow().isoformat()
            })
            logger.info(f"[{job_id}] Completed: {message}")
        else:
            await db.update_scraping_job(job_id, {
                "status": "failed",
                "error_message": message,
                "completed_at": datetime.utcnow().isoformat()
            })
            logger.error(f"[{job_id}] Failed: {message}")

    except Exception as e:
        logger.exception(f"[{job_id}] Unexpected error while processing job: {e}")
        try:
            await db.update_scraping_job(job_id, {
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.utcnow().isoformat()
            })
        except Exception:
            pass


async def poll_loop():
    logger.info("Worker poll loop starting...")
    while True:
        try:
            pending_jobs = await db.get_pending_jobs()
            if not pending_jobs:
                await asyncio.sleep(Config.SLEEP_EMPTY)
                continue

            for job in pending_jobs:
                logger.debug("Fetched job: %s", job)
                await process_job(job)
                await asyncio.sleep(Config.SLEEP_BETWEEN_JOBS)
        except Exception as e:
            logger.exception("Error in poll loop: %s", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(poll_loop())
