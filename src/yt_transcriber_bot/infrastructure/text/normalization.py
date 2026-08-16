"""Compatibility import for the application-owned text integrity policy."""

from yt_transcriber_bot.application.services.text_integrity import (
    normalize_artifact_text,
    text_has_unresolved_corruption,
    unresolved_text_corruption_score,
)

__all__ = [
    "normalize_artifact_text",
    "text_has_unresolved_corruption",
    "unresolved_text_corruption_score",
]
