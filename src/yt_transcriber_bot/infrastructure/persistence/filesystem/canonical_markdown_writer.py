from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.canonical_markdown import CanonicalMarkdownWriter


class FilesystemCanonicalMarkdownWriter(CanonicalMarkdownWriter):
    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
