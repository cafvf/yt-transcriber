"""Conformance checks for TASK-P04-003 completed-history ownership."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_HISTORY = ROOT / "src/yt_transcriber_bot/application/workflows/history.py"
TELEGRAM_HISTORY = ROOT / "src/yt_transcriber_bot/infrastructure/telegram/history.py"
BOT = ROOT / "src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py"


def test_completed_history_policy_is_application_owned() -> None:
    app = APP_HISTORY.read_text(encoding="utf-8")
    telegram = TELEGRAM_HISTORY.read_text(encoding="utf-8")

    assert "class CompletedHistoryWorkflow" in app
    assert "def list_completed" in app
    assert "def select_from_completed" in app
    assert "def resolve_markdown" in app
    assert "def completed_jobs_for_user" not in telegram
    assert "def select_completed_job" not in telegram
    assert "def select_from_completed_jobs" not in telegram


def test_application_history_has_no_telegram_search_or_direct_filesystem_probe() -> None:
    source = APP_HISTORY.read_text(encoding="utf-8")

    assert "infrastructure.telegram" not in source
    assert "history_search" not in source
    assert "HistorySearch" not in source
    assert ".is_file()" not in source


def test_telegram_delegates_completed_history_policy() -> None:
    source = BOT.read_text(encoding="utf-8")

    assert "CompletedHistoryWorkflow" in source
    assert "self._completed_history.list_completed" in source
    assert "self._completed_history.select_from_completed" in source
    assert "self._completed_history.resolve_markdown" in source


def test_telegram_keeps_presentation_and_command_parsing() -> None:
    source = TELEGRAM_HISTORY.read_text(encoding="utf-8")

    assert "class HistoryPresentation" in source
    assert "def format_job" in source
    assert "def prefetch_titles" in source
    assert "def parse_history_index" in source
