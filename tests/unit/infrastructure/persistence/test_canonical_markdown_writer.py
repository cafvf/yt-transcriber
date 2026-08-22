from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.infrastructure.persistence.filesystem.canonical_markdown_writer import (
    FilesystemCanonicalMarkdownWriter,
)


def test_write_new_never_overwrites_existing_markdown(tmp_path: Path) -> None:
    writer = FilesystemCanonicalMarkdownWriter()
    preferred = tmp_path / "video.md"
    preferred.write_text("old", encoding="utf-8")

    created = writer.write_new(preferred, "new", collision_key="job-1")

    assert preferred.read_text(encoding="utf-8") == "old"
    assert created == tmp_path / "video-2.md"
    assert created.read_text(encoding="utf-8") == "new"
    assert not list(tmp_path.glob(".*.tmp"))


def test_write_atomically_replaces_known_markdown_path(tmp_path: Path) -> None:
    writer = FilesystemCanonicalMarkdownWriter()
    path = tmp_path / "video.md"
    path.write_text("old", encoding="utf-8")

    writer.write(path, "replacement")

    assert path.read_text(encoding="utf-8") == "replacement"
    assert not list(tmp_path.glob(".*.tmp"))
