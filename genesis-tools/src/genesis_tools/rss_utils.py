import asyncio
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import feedparser

from .base import BaseTool
from .schema import ToolResult


def fetch_single_rss(url: str, since_days: int = 1) -> list[dict[str, Any]]:
    """Blocking function to fetch and parse a single RSS feed.
    """
    all_entries = []
    cutoff_date = datetime.now(UTC) - timedelta(days=since_days)

    # feedparser.parse is a blocking network call
    feed_data: Any = feedparser.parse(url)
    feed_info = feed_data.get("feed", {})
    feed_title = feed_info.get("title", "Unknown Feed")
    entries = feed_data.get("entries", [])

    for entry in entries:
        published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published_dt: datetime | None = None

        if published_parsed:
            timestamp = time.mktime(published_parsed)
            published_dt = datetime.fromtimestamp(timestamp, tz=UTC)

        # Include if it's within the time window OR if it has no date (to be safe)
        if (published_dt and published_dt >= cutoff_date) or not published_parsed:
            all_entries.append(
                {
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": published_dt.isoformat() if published_dt else "Unknown",
                    "feed_title": feed_title,
                },
            )

    return all_entries


class RssFetchTool(BaseTool):
    name = "fetch_rss_feed"
    description = (
        "Fetch and parse recent entries from a specific RSS feed URL. "
        "The results are added to your clipboard for easy browsing."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The full URL of the RSS feed."},
            "since_days": {
                "type": "integer",
                "default": 1,
                "description": "Only fetch entries from the last X days.",
            },
        },
        "required": ["url"],
    }

    async def run(
        self,
        working_directory: Path,
        url: str,
        since_days: int = 1,
        **kwargs: Any,
    ) -> ToolResult:
        # Since this involves a blocking network call, we run it in a separate thread
        try:
            entries = await asyncio.to_thread(fetch_single_rss, url=url, since_days=since_days)
        except Exception as e:
            return ToolResult(
                status="error", tool_response=f"Failed to fetch RSS feed from {url}: {e!s}",
            )

        if not entries:
            return ToolResult(
                status="success",
                tool_response=f"Connected to {url}, but no new entries were found for the last {since_days} day(s).",
            )

        # Format the feed entries for the clipboard
        formatted_entries = []
        for entry in entries:
            item_text = (
                f"Source: {entry.get('feed_title')}\n"
                f"Title: {entry.get('title')}\n"
                f"Published: {entry.get('published')}\n"
                f"Link: {entry.get('link')}\n"
                f"Summary: {entry.get('summary')}\n"
                "---"
            )
            formatted_entries.append(item_text)

        return ToolResult(
            status="success",
            tool_response=(
                f"Successfully fetched {len(entries)} entries from the feed. "
                "The headlines and summaries have been added to your clipboard."
            ),
            results_to_add_to_clipboard=formatted_entries,
        )
