from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from yt_transcriber_bot.application.ports.canonical_markdown import CanonicalMarkdownWriter


class FilesystemCanonicalMarkdownWriter(CanonicalMarkdownWriter):
    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._write_temp(path, content, collision_key="replace")
        try:
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def write_new(self, preferred_path: Path, content: str, *, collision_key: str) -> Path:
        preferred_path.parent.mkdir(parents=True, exist_ok=True)
        for index in range(1, 10_001):
            candidate = self._candidate(preferred_path, index)
            temp = self._write_temp(candidate, content, collision_key=collision_key)
            try:
                try:
                    os.link(temp, candidate)
                except FileExistsError:
                    continue
                return candidate
            finally:
                temp.unlink(missing_ok=True)
        raise OSError("não foi possível reservar um nome único para o Markdown canônico")

    @staticmethod
    def _candidate(preferred_path: Path, index: int) -> Path:
        if index == 1:
            return preferred_path
        return preferred_path.with_name(f"{preferred_path.stem}-{index}{preferred_path.suffix}")

    @staticmethod
    def _write_temp(candidate: Path, content: str, *, collision_key: str) -> Path:
        safe_collision_key = (
            "".join(ch for ch in collision_key if ch.isalnum() or ch in {"-", "_"}) or "write"
        )
        temp = candidate.with_name(f".{candidate.name}.{safe_collision_key}.{uuid4().hex}.tmp")
        try:
            with temp.open("x", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            temp.unlink(missing_ok=True)
            raise
        return temp
