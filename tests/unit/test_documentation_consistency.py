"""Regression checks for repository-facing documentation consistency."""

from __future__ import annotations

from pathlib import Path


def test_architecture_doc_uses_current_module_names() -> None:
    doc = Path("docs/02-arquitetura.md").read_text(encoding="utf-8")

    stale_names = (
        "bootstrap.py",
        "process_video.py",
        "VideoSource",
        "SubtitleSource",
        "ArtifactStore",
        "MessageGateway",
        "QueueRepository",
        "SpeakerMapRepository",
    )
    for name in stale_names:
        assert name not in doc

    current_paths = (
        "composition_root.py",
        "application/config.py",
        "application/use_cases/transcribe_video.py",
        "application/ports/youtube_downloader.py",
        "infrastructure/telegram/bot_adapter.py",
        "infrastructure/logging/execution_audit.py",
    )
    for path in current_paths:
        assert path in doc


def test_readme_and_manual_distinguish_inflight_dedup_from_redo() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    manual = Path("docs/03-manual-de-uso.md").read_text(encoding="utf-8")

    for doc in (readme, manual):
        assert "em processamento ou na fila" in doc
        assert "/redo <link>" in doc
        assert "concluído" in doc or "concluída" in doc
