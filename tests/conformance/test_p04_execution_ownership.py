"""Conformance checks for TASK-P04-002 / REQ-ARC-003."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_QUEUE = ROOT / "src/yt_transcriber_bot/application/workflows/execution_queue.py"
LEGACY_QUEUE = ROOT / "src/yt_transcriber_bot/infrastructure/telegram/job_queue.py"
BOT = ROOT / "src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py"
RECOVERY = ROOT / "src/yt_transcriber_bot/application/services/startup_recovery.py"


def test_sequential_queue_implementation_is_application_owned() -> None:
    app_source = APP_QUEUE.read_text(encoding="utf-8")
    bot_source = BOT.read_text(encoding="utf-8")

    assert "class SequentialJobQueue" in app_source
    assert not LEGACY_QUEUE.exists()
    assert "application.workflows.execution_queue" in bot_source
    assert "infrastructure.telegram.job_queue import" not in bot_source


def test_cancellation_token_is_not_owned_by_telegram_payload() -> None:
    bot_source = BOT.read_text(encoding="utf-8")

    assert "cancel_event: threading.Event" not in bot_source
    assert "cancel_event=payload.cancel_event" not in bot_source
    assert "cancel_event=item.cancel_event" in bot_source


def test_primary_delivery_lifecycle_is_delegated_to_application() -> None:
    bot_source = BOT.read_text(encoding="utf-8")

    assert "ExecutionLifecycleService" in bot_source
    assert "_execution_lifecycle.begin_primary_delivery" in bot_source
    assert "_execution_lifecycle.finish_primary_delivery" in bot_source
    assert "def _mark_job_delivering" not in bot_source
    assert "def _mark_job_completed_after_delivery" not in bot_source


def test_recovery_result_carries_application_request_context() -> None:
    recovery_source = RECOVERY.read_text(encoding="utf-8")

    assert "class RecoveredPendingJob" in recovery_source
    assert "request_context: JobRequestContext" in recovery_source
