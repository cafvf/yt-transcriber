from __future__ import annotations

from email.message import Message

from yt_transcriber_bot.infrastructure.youtube.yt_dlp_real_factory import (
    real_subtitle_fetcher,
)


class _FakeResponse:
    def __init__(self, payload: bytes, *, charset: str | None = None) -> None:
        self._payload = payload
        self.headers = Message()
        if charset is not None:
            self.headers.add_header("Content-Type", f"text/vtt; charset={charset}")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_real_subtitle_fetcher_uses_declared_charset(monkeypatch) -> None:
    payload = "Ol\u00e1 mundo".encode("iso-8859-1")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=30: _FakeResponse(payload, charset="iso-8859-1"),
    )

    assert real_subtitle_fetcher("https://example.com/x.vtt", "vtt") == "Olá mundo"
