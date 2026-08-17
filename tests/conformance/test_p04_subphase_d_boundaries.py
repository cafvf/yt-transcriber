from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src/yt_transcriber_bot"
ADAPTER = SRC / "infrastructure/telegram/bot_adapter.py"
COMPOSITION = SRC / "composition_root.py"


def test_telegram_adapter_has_no_parallel_concrete_service_graph() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    forbidden = (
        "RenameSpeakersService",
        "TranscriptExportService",
        "PlainTextTranscriptExportService",
        "TranscriptSummaryService",
        "VideoSoftSubtitleExportService",
        "HistorySearchService",
        "HealthCheckService",
        "LastErrorService",
        "RetentionPolicy",
        "_rename_service",
        "_export_service",
        "_summary_service",
        "_history_search_service",
        "_healthcheck_service",
        "_lasterror_service",
        "_retention_policy",
    )
    for token in forbidden:
        assert token not in source


def test_telegram_adapter_delegates_only_to_application_workflow_capabilities() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TelegramBotAdapter"
    )
    ctor = next(
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    params = {arg.arg for arg in [*ctor.args.args, *ctor.args.kwonlyargs]}
    assert {
        "history_workflow",
        "execution_lifecycle",
        "startup_recovery_service",
        "source_cleanup_service",
        "staging_cleanup",
        "text_search_workflow",
        "derivative_workflow",
        "summary_workflow",
        "operational_workflow",
    } <= params
    assert "history_presentation" in params
    assert "search_indexing_service" not in params


def test_telegram_adapter_contains_no_direct_cache_or_staging_filesystem_cleanup() -> None:
    source = ADAPTER.read_text(encoding="utf-8")
    for token in ("Path.is_file", ".rglob(", ".glob(", ".unlink(", ".rmdir("):
        assert token not in source


def test_composition_exposes_cohesive_application_runtime_graph() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    for token in (
        "history_presentation=core.history_presentation",
        "history_workflow=core.history_workflow",
        "execution_lifecycle=core.execution_lifecycle",
        "startup_recovery_service=core.startup_recovery_service",
        "source_cleanup_service=core.source_cleanup_service",
        "staging_cleanup=core.staging_cleanup",
        "text_search_workflow=core.text_search_workflow",
        "derivative_workflow=core.derivative_workflow",
        "summary_workflow=core.summary_workflow",
        "operational_workflow=core.operational_workflow",
    ):
        assert token in source
    for legacy in (
        "history_search_service:",
        "rename_service:",
        "export_service:",
        "plain_text_export_service:",
        "video_subtitle_export_service:",
        "healthcheck_service:",
        "lasterror_service:",
        "retention_policy:",
    ):
        assert legacy not in source


def test_obsolete_compatibility_and_empty_speculative_surfaces_are_removed() -> None:
    assert not (SRC / "application/ports/history_search.py").exists()
    assert not (SRC / "application/services/history_search.py").exists()
    assert not (SRC / "infrastructure/telegram/job_queue.py").exists()
    assert not (SRC / "domain/events/__init__.py").exists()
    assert not (SRC / "domain/pipeline/__init__.py").exists()
    assert not any(path.name == "file_storage.py" for path in SRC.rglob("*.py"))
