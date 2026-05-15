"""Patch notes devem ficar em docs/patches, não na raiz."""

from __future__ import annotations

from pathlib import Path


def test_no_patch_notes_in_repository_root() -> None:
    root_notes = sorted(Path(".").glob("PATCH_NOTES*.md"))
    assert root_notes == []


def test_no_duplicate_patch_notes_outside_docs_patches() -> None:
    misplaced = sorted(
        str(path)
        for folder in (Path("docs"), Path("deploy"))
        for path in folder.glob("PATCH_NOTES*.md")
        if path.is_file()
    )
    assert misplaced == []


def test_patch_notes_directory_exists() -> None:
    assert Path("docs/patches").is_dir()
