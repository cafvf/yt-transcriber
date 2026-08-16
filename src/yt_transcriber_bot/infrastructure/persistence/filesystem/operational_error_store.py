from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from yt_transcriber_bot.application.ports.operational_error import (
    OperationalErrorRecord,
    OperationalErrorStore,
)
from yt_transcriber_bot.infrastructure.filesystem_safety import (
    ensure_private_directory,
    ensure_private_file,
)


class JsonlOperationalErrorStore(OperationalErrorStore):
    def __init__(
        self,
        path: Path,
        *,
        max_records: int = 500,
        max_bytes: int = 2_000_000,
        max_scan_bytes: int = 2_000_000,
    ) -> None:
        self._path = path
        self._max_records = max(1, max_records)
        self._max_bytes = max(4096, max_bytes)
        self._max_scan_bytes = max(4096, max_scan_bytes)

    def append(self, record: OperationalErrorRecord) -> None:
        ensure_private_directory(self._path.parent)
        payload = {
            "user_id": record.user_id,
            "operation": record.operation,
            "message": record.message,
            "occurred_at": record.occurred_at.isoformat(),
            "context": record.context,
            "error_type": record.error_type,
            "stage": record.stage,
            "severity": record.severity,
            "traceback_tail": record.traceback_tail,
        }
        with self._path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        ensure_private_file(self._path)
        if self._path.stat().st_size > self._max_bytes:
            self._compact()

    def latest_for_user(self, user_id: int, *, limit: int) -> OperationalErrorRecord | None:
        matches: list[OperationalErrorRecord] = []
        for line in reversed(self._tail_lines(max(self._max_records, limit * 4))):
            record = _parse(line)
            if record is not None and record.user_id == user_id:
                matches.append(record)
                if len(matches) >= limit:
                    break
        return max(matches, key=lambda item: item.occurred_at) if matches else None

    def recent_count(self) -> int:
        return len([line for line in self._tail_lines(self._max_records) if line.strip()])

    def _tail_lines(self, max_lines: int) -> list[str]:
        if not self._path.is_file():
            return []
        try:
            with self._path.open("rb") as stream:
                stream.seek(0, 2)
                size = stream.tell()
                start = max(0, size - self._max_scan_bytes)
                stream.seek(start)
                raw = stream.read(self._max_scan_bytes)
        except OSError:
            return []
        text = raw.decode("utf-8", errors="replace")
        if start:
            text = text.split("\n", 1)[-1]
        return text.splitlines()[-max_lines:]

    def _compact(self) -> None:
        lines = self._tail_lines(self._max_records)
        temp = self._path.with_suffix(self._path.suffix + ".tmp")
        temp.write_text(("\n".join(lines).rstrip() + "\n") if lines else "", encoding="utf-8")
        temp.replace(self._path)
        ensure_private_file(self._path)


def _parse(line: str) -> OperationalErrorRecord | None:
    if not line.strip():
        return None
    try:
        payload: dict[str, Any] = json.loads(line)
        when = datetime.fromisoformat(str(payload.get("occurred_at", "")))
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        raw_context = payload.get("context", {})
        context = (
            {str(key): str(value) for key, value in raw_context.items()}
            if isinstance(raw_context, dict)
            else {}
        )
        return OperationalErrorRecord(
            user_id=int(payload.get("user_id", 0)),
            operation=str(payload.get("operation", "unknown")),
            message=str(payload.get("message", "")),
            occurred_at=when,
            context=context,
            error_type=str(payload.get("error_type", "")),
            stage=str(payload.get("stage", "")),
            severity=str(payload.get("severity", "error")),
            traceback_tail=str(payload.get("traceback_tail", "")),
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
