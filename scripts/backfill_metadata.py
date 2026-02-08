#!/usr/bin/env python3
"""Backfill YouTube metadata (title, channel, upload date) for existing videos."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import inspect, text
from src.database.connection import engine, SessionLocal
from src.database.models import Video
from src.processing.youtube_metadata import YouTubeMetadataFetcher, parse_event_name_from_title


def ensure_channel_name_column():
    """Add channel_name column if it doesn't exist (SQLite migration)."""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("videos")]
    if "channel_name" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE videos ADD COLUMN channel_name VARCHAR(255)"))
            conn.commit()
        print("Added channel_name column to videos table.")
    else:
        print("channel_name column already exists.")


def backfill():
    """Fetch and store YouTube metadata for videos missing it."""
    db = SessionLocal()
    fetcher = YouTubeMetadataFetcher()

    try:
        videos = db.query(Video).all()
        print(f"Found {len(videos)} video(s) to check.\n")

        updated = 0
        for video in videos:
            needs_update = not video.title or not video.event_date or not video.channel_name
            if not needs_update:
                print(f"  [{video.youtube_id}] already has metadata, skipping.")
                continue

            print(f"  [{video.youtube_id}] fetching metadata...")
            meta = fetcher.fetch(video.youtube_id)

            if not video.title and meta.title:
                video.title = meta.title
                print(f"    title: {meta.title}")
            if not video.event_name and meta.title:
                parsed = parse_event_name_from_title(meta.title)
                if parsed:
                    video.event_name = parsed
                    print(f"    event_name: {parsed}")
            if not video.event_date and meta.upload_date:
                video.event_date = meta.upload_date
                print(f"    event_date: {meta.upload_date.date()}")
            if not video.channel_name and meta.channel_name:
                video.channel_name = meta.channel_name
                print(f"    channel_name: {meta.channel_name}")

            updated += 1

        db.commit()
        print(f"\nDone. Updated {updated} video(s).")
    finally:
        db.close()


if __name__ == "__main__":
    ensure_channel_name_column()
    backfill()
