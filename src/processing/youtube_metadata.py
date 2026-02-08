"""Fetch video metadata from YouTube without an API key."""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx


@dataclass
class YouTubeMetadata:
    """Metadata fetched from YouTube for a video."""

    video_id: str
    title: Optional[str] = None
    channel_name: Optional[str] = None
    upload_date: Optional[datetime] = None
    thumbnail_url: Optional[str] = None


OEMBED_URL = "https://www.youtube.com/oembed"
UPLOAD_DATE_RE = re.compile(r'"uploadDate"\s*:\s*"(\d{4}-\d{2}-\d{2})')


def parse_event_name_from_title(title: str) -> Optional[str]:
    """Extract venue/event name from titles like 'Sinai Sports - 12/21/25 - Tier 2 - ...'."""
    if not title:
        return None
    parts = title.split(" - ")
    if len(parts) >= 2:
        return parts[0].strip() or None
    return None


class YouTubeMetadataFetcher:
    """Fetch YouTube video metadata via oEmbed API and page scraping."""

    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout

    def fetch(self, video_id: str) -> YouTubeMetadata:
        """Fetch metadata for a YouTube video. Never raises -- returns partial data on failure."""
        meta = YouTubeMetadata(video_id=video_id)

        # oEmbed for title, channel, thumbnail
        try:
            resp = httpx.get(
                OEMBED_URL,
                params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            meta.title = data.get("title")
            meta.channel_name = data.get("author_name")
            meta.thumbnail_url = data.get("thumbnail_url")
        except Exception:
            pass

        # Scrape watch page for upload date
        try:
            resp = httpx.get(
                f"https://www.youtube.com/watch?v={video_id}",
                timeout=self._timeout,
                headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            resp.raise_for_status()
            match = UPLOAD_DATE_RE.search(resp.text)
            if match:
                meta.upload_date = datetime.strptime(match.group(1), "%Y-%m-%d")
        except Exception:
            pass

        return meta
