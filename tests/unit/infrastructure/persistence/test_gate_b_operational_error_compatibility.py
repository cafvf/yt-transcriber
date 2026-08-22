from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.operational_errors import (
    OperationalErrorCategory,
    OperationalErrorCode,
)
from yt_transcriber_bot.application.ports.operational_error import OperationalErrorRecord
from yt_transcriber_bot.infrastructure.persistence.filesystem.operational_error_store import (
    JsonlOperationalErrorStore,
)


def test_new_operational_error_jsonl_uses_only_canonical_semantics(tmp_path: Path) -> None:
    path = tmp_path / "errors.jsonl"
    store = JsonlOperationalErrorStore(path)
    store.append(
        OperationalErrorRecord(
            user_id=7,
            operation="transcribe",
            code=OperationalErrorCode.YOUTUBE_VIDEO_UNAVAILABLE,
            category=OperationalErrorCategory.ACCESS,
            retryable=False,
            safe_message="O vídeo não está disponível para processamento.",
            technical_context={"detail": "sanitized"},
        )
    )

    payload = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["code"] == "youtube.video_unavailable"
    assert payload["category"] == "access"
    assert payload["retryable"] is False
    assert payload["safe_message"]
    assert payload["technical_context"] == {"detail": "sanitized"}
    assert "message" not in payload
    assert "context" not in payload
    assert "error_type" not in payload


def test_legacy_operational_error_jsonl_is_translated_only_on_read(tmp_path: Path) -> None:
    path = tmp_path / "errors.jsonl"
    legacy = {
        "user_id": 7,
        "operation": "summary",
        "message": "legacy safe text",
        "occurred_at": datetime(2026, 8, 1, tzinfo=UTC).isoformat(),
        "context": {"model": "old"},
        "error_type": "TimeoutError",
        "stage": "llm",
        "severity": "error",
        "traceback_tail": "",
    }
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    store = JsonlOperationalErrorStore(path)

    record = store.latest_for_user(7, limit=1)

    assert record is not None
    assert record.code is OperationalErrorCode.LEGACY_UNCLASSIFIED
    assert record.category is OperationalErrorCategory.INTERNAL
    assert record.retryable is False
    assert record.safe_message == "legacy safe text"
    assert record.technical_context == {
        "model": "old",
        "legacy_exception_type": "TimeoutError",
    }
