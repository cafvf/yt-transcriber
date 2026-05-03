"""Testes do extrator de URL do YouTube em mensagens de texto."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.infrastructure.telegram.url_extractor import (
    extract_first_youtube_url,
)


class TestExtractor:
    def test_empty_text_returns_none(self) -> None:
        assert extract_first_youtube_url("") is None

    def test_no_url_returns_none(self) -> None:
        assert extract_first_youtube_url("apenas texto") is None

    def test_simple_watch_url(self) -> None:
        url = extract_first_youtube_url("Olha esse https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_short_youtu_be_url(self) -> None:
        url = extract_first_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert url == "https://youtu.be/dQw4w9WgXcQ"

    def test_mobile_subdomain(self) -> None:
        url = extract_first_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert url == "https://m.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_music_subdomain(self) -> None:
        url = extract_first_youtube_url("ouve https://music.youtube.com/watch?v=dQw4w9WgXcQ")
        assert url == "https://music.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_shorts(self) -> None:
        url = extract_first_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        assert url == "https://www.youtube.com/shorts/dQw4w9WgXcQ"

    def test_extra_query_params(self) -> None:
        url = extract_first_youtube_url(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&feature=share"
        )
        assert "v=dQw4w9WgXcQ" in (url or "")

    def test_url_at_start(self) -> None:
        url = extract_first_youtube_url("https://youtu.be/dQw4w9WgXcQ pode ver?")
        assert url == "https://youtu.be/dQw4w9WgXcQ"

    def test_url_at_end_with_punctuation(self) -> None:
        # Pontuação trailing deve ser removida.
        url = extract_first_youtube_url("Veja https://youtu.be/dQw4w9WgXcQ.")
        assert url == "https://youtu.be/dQw4w9WgXcQ"

    def test_url_at_end_with_paren(self) -> None:
        url = extract_first_youtube_url("(https://youtu.be/dQw4w9WgXcQ)")
        assert url == "https://youtu.be/dQw4w9WgXcQ"

    def test_first_url_wins(self) -> None:
        text = "https://youtu.be/aaaaaaaaaaa e tambem https://youtu.be/bbbbbbbbbbb"
        url = extract_first_youtube_url(text)
        assert url == "https://youtu.be/aaaaaaaaaaa"

    def test_case_insensitive(self) -> None:
        url = extract_first_youtube_url("HTTPS://YOUTU.BE/dQw4w9WgXcQ")
        assert url == "HTTPS://YOUTU.BE/dQw4w9WgXcQ"

    @pytest.mark.parametrize(
        "noise",
        [
            "vídeo do https://example.com/foo",
            "https://twitter.com/x",
            "https://google.com/search?q=youtube.com",
        ],
    )
    def test_unrelated_urls_are_ignored(self, noise: str) -> None:
        assert extract_first_youtube_url(noise) is None
