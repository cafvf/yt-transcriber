"""Patch notes devem ficar em docs/patches, não na raiz."""

from __future__ import annotations

from pathlib import Path


def test_no_patch_notes_in_repository_root() -> None:
    root_notes = sorted(Path(".").glob("PATCH_NOTES*.md"))
    assert root_notes == []


def test_patch_notes_directory_exists() -> None:
    assert Path("docs/patches").is_dir()
