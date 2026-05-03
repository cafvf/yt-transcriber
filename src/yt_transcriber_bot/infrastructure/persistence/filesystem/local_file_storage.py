"""Implementação do ``FileStorage`` baseada em ``pathlib``."""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.file_storage import FileStorage


class LocalFileStorage(FileStorage):
    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def exists(self, path: Path) -> bool:
        return path.exists()

    def delete(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def list_files_oldest_first(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        files = [p for p in directory.iterdir() if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime)
        return files
