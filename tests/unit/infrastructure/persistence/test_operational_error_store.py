from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.operational_error import OperationalErrorRecord
from yt_transcriber_bot.infrastructure.operational.bounded_log_reader import BoundedTextLogReader
from yt_transcriber_bot.infrastructure.persistence.filesystem.operational_error_store import (
    JsonlOperationalErrorStore,
)


def test_operational_error_store_compacts_and_reads_bounded_recent_window(tmp_path: Path) -> None:
    path = tmp_path / "errors.jsonl"
    store = JsonlOperationalErrorStore(path, max_records=3, max_bytes=300, max_scan_bytes=4096)
    for index in range(8):
        store.append(OperationalErrorRecord(user_id=7, operation="test", message=f"event {index}"))
    assert store.recent_count() <= 3
    latest = store.latest_for_user(7, limit=2)
    assert latest is not None
    assert latest.message == "event 7"


def test_bounded_log_reader_returns_tail(tmp_path: Path) -> None:
    path = tmp_path / "job.log"
    path.write_text("\n".join(f"line {i}" for i in range(100)), encoding="utf-8")
    tail = BoundedTextLogReader(max_scan_bytes=256).tail(path, max_lines=3, max_chars=100)
    assert "line 99" in tail
    assert "line 0" not in tail
