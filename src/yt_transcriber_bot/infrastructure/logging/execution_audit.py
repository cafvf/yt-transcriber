"""Structured execution audit log for local, privacy-aware operations."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.filesystem_safety import (
    ensure_private_directory,
    ensure_private_file,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_value


class ExecutionAuditLogger:
    """Append-only JSONL audit logger using the shared sanitization policy.

    Sanitized audit data remains private. The local parent directory and file
    are therefore kept at 0700 and 0600 respectively on POSIX systems.
    """

    def __init__(self, path: Path, settings: AppSettings | None = None) -> None:
        self._path = path
        self._settings = settings
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record(self, event: str, **fields: object) -> None:
        row: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "event": event,
        }
        row.update(
            {key: sanitize_value(key, value, self._settings) for key, value in fields.items()}
        )
        ensure_private_directory(self._path.parent)
        line = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
        with self._lock, self._path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
        ensure_private_file(self._path)
