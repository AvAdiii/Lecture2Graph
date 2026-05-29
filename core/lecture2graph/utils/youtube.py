"""YouTube URL helpers."""

from __future__ import annotations

import re


VIDEO_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})")


def get_video_id(url: str) -> str:
    match = VIDEO_ID_PATTERN.search(url)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url.strip()):
        return url.strip()
    raise ValueError(f"Could not parse a YouTube video ID from: {url}")


def watch_url(video_id: str, seconds: float | int | None = None) -> str:
    base = f"https://www.youtube.com/watch?v={video_id}"
    if seconds is None:
        return base
    return f"{base}&t={int(seconds)}s"


def normalize_url(url: str) -> str:
    return watch_url(get_video_id(url))

