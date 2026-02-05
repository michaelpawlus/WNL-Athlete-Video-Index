#!/usr/bin/env python3
"""CLI script to process a YouTube video and extract athlete appearances."""
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import SessionLocal
from src.processing.pipeline import ProcessingPipeline, PipelineError


def parse_date(date_str: str) -> datetime:
    """Parse a date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(
        description="Process a YouTube video to extract athlete appearances"
    )
    parser.add_argument(
        "url",
        help="YouTube video URL or ID",
    )
    parser.add_argument(
        "--title", "-t",
        help="Video title",
    )
    parser.add_argument(
        "--event", "-e",
        help="Event name",
    )
    parser.add_argument(
        "--date", "-d",
        help="Event date (YYYY-MM-DD format)",
        type=parse_date,
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force reprocessing even if already done",
    )

    args = parser.parse_args()

    print(f"Processing video: {args.url}")

    db = SessionLocal()
    try:
        pipeline = ProcessingPipeline(db)
        result = pipeline.process_video(
            url_or_id=args.url,
            title=args.title,
            event_name=args.event,
            event_date=args.date,
            force_reprocess=args.force,
        )

        if result.already_processed:
            print(f"\nVideo already processed (use --force to reprocess)")
            print(f"  Video ID: {result.video_id}")
            print(f"  YouTube ID: {result.youtube_id}")
            print(f"  Athletes: {result.athletes_found}")
            print(f"  Appearances: {result.appearances_created}")
        else:
            print(f"\nProcessing complete!")
            print(f"  Video ID: {result.video_id}")
            print(f"  YouTube ID: {result.youtube_id}")
            print(f"  Title: {result.title or 'N/A'}")
            print(f"  Athletes found: {result.athletes_found}")
            print(f"  Appearances created: {result.appearances_created}")

    except PipelineError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
