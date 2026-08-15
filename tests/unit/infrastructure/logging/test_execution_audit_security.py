"""Security regressions for the shared execution-audit disclosure policy."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.infrastructure.logging.execution_audit import ExecutionAuditLogger


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="configured-telegram-secret-123",
        telegram_allowed_user_id=42,
        hf_token="configured-hf-secret-123",
        summary_api_key="configured-summary-secret-123",
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
    )


def test_audit_uses_shared_policy_for_configured_secrets_payloads_and_paths(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "execution_audit.jsonl"
    logger = ExecutionAuditLogger(path, settings=_settings(tmp_path))

    logger.record(
        "failed",
        detail="configured-summary-secret-123",
        transcript="private transcript",
        artifact_path=tmp_path / "private.md",
        user_id=42,
    )

    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["detail"] == "[REDACTED]"
    assert row["transcript"] == "[OMITTED]"
    assert row["artifact_path"] == "[PRIVATE PATH]"
    assert row["user_id"] == "[PRIVATE IDENTIFIER]"


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission contract")
def test_audit_file_and_directory_are_private(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "execution_audit.jsonl"
    logger = ExecutionAuditLogger(path)

    logger.record("started", job_id="job-1")

    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o600
