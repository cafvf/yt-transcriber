from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.operational_error import JobLogReader


class BoundedTextLogReader(JobLogReader):
    def __init__(self, max_scan_bytes: int = 256_000) -> None:
        self._max_scan_bytes = max(4096, max_scan_bytes)

    def tail(self, path: Path, *, max_lines: int, max_chars: int) -> str:
        if not path.is_file():
            return "log indisponível"
        try:
            with path.open("rb") as stream:
                stream.seek(0, 2)
                size = stream.tell()
                start = max(0, size - self._max_scan_bytes)
                stream.seek(start)
                raw = stream.read(self._max_scan_bytes)
        except OSError as exc:
            return f"não consegui ler o log ({type(exc).__name__})"
        text = raw.decode("utf-8", errors="replace")
        if start:
            text = text.split("\n", 1)[-1]
        tail = "\n".join(text.splitlines()[-max_lines:])
        return "[...]\n" + tail[-max_chars:] if len(tail) > max_chars else tail
