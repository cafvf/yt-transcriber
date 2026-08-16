from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.sanitization import sanitize_value
from yt_transcriber_bot.infrastructure.filesystem_safety import (
    ensure_private_directory,
    ensure_private_file,
)


class ExecutionAuditLogger:
    def __init__(
        self,
        path: Path,
        settings: AppSettings | None = None,
        *,
        max_bytes: int = 2_000_000,
        backup_count: int = 2,
    ) -> None:
        self._path = path
        self._settings = settings
        self._max_bytes = max(4096, max_bytes)
        self._backup_count = max(1, backup_count)
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
        line = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n"
        ensure_private_directory(self._path.parent)
        with self._lock:
            self._rotate_if_needed(len(line.encode("utf-8")))
            with self._path.open("a", encoding="utf-8") as stream:
                stream.write(line)
            ensure_private_file(self._path)

    def _rotate_if_needed(self, incoming: int) -> None:
        current = self._path.stat().st_size if self._path.is_file() else 0
        if current + incoming <= self._max_bytes:
            return
        self._path.with_name(f"{self._path.name}.{self._backup_count}").unlink(missing_ok=True)
        for index in range(self._backup_count - 1, 0, -1):
            source = self._path.with_name(f"{self._path.name}.{index}")
            if source.exists():
                source.replace(self._path.with_name(f"{self._path.name}.{index + 1}"))
        if self._path.exists():
            self._path.replace(self._path.with_name(f"{self._path.name}.1"))
