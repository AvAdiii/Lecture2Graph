"""Time-format helpers."""

from __future__ import annotations


def format_seconds(value: float) -> str:
    seconds = int(value)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

