# clean_tables.py
import asyncio
from dotenv import load_dotenv
import os
from dotenv import load_dotenv
import pathlib

env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
print(os.getenv("SUPABASE_URL"))
print(os.getenv("SUPABASE_KEY"))

from database import db  # your Database class wrapper

async def clean_table(table_name: str):
    """Delete all records from a given table."""
    result = db.supabase.table(table_name).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print(f"Deleted {len(result.data or [])} rows from {table_name}")

async def main():
    # List of tables to wipe
    tables = [
        "youtube_urls",
        "videos",
        "scraping_jobs",
        "url_videos",
    ]

    for table in tables:
        await clean_table(table)

if __name__ == "__main__":
    asyncio.run(main())
