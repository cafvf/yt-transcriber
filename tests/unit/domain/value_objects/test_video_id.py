"""Testes do value object ``VideoId``."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.domain.value_objects.video_id import (
    InvalidYouTubeUrlError,
    VideoId,
)


class TestVideoIdConstruction:
    def test_construction_with_valid_id_succeeds(self) -> None:
        video_id = VideoId(value="dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_construction_with_short_id_raises(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId(value="abc")

    def test_construction_with_long_id_raises(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId(value="a" * 12)

    def test_construction_with_invalid_chars_raises(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId(value="abc!def@ghi")  # 11 chars com símbolos inválidos

    def test_video_id_is_immutable(self) -> None:
        video_id = VideoId(value="dQw4w9WgXcQ")
        with pytest.raises(Exception):  # noqa: B017,PT011
            video_id.value = "other"  # type: ignore[misc]


class TestVideoIdFromUrl:
    def test_extracts_from_watch_url(self) -> None:
        video_id = VideoId.from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_short_url(self) -> None:
        video_id = VideoId.from_url("https://youtu.be/dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_shorts(self) -> None:
        video_id = VideoId.from_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_embed(self) -> None:
        video_id = VideoId.from_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_v_legacy(self) -> None:
        video_id = VideoId.from_url("https://www.youtube.com/v/dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_mobile_subdomain(self) -> None:
        video_id = VideoId.from_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_music_subdomain(self) -> None:
        video_id = VideoId.from_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id.value == "dQw4w9WgXcQ"

    def test_normalizes_with_extra_query_params(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxx&index=3&t=42s"
        video_id = VideoId.from_url(url)
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_text_with_url_in_middle(self) -> None:
        text = "Olha esse vídeo https://www.youtube.com/watch?v=dQw4w9WgXcQ ele é ótimo!"
        video_id = VideoId.from_url(text)
        assert video_id.value == "dQw4w9WgXcQ"

    def test_extracts_from_text_with_short_url_at_end(self) -> None:
        text = "veja https://youtu.be/dQw4w9WgXcQ"
        video_id = VideoId.from_url(text)
        assert video_id.value == "dQw4w9WgXcQ"

    def test_rejects_non_youtube_domain(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId.from_url("https://www.vimeo.com/watch?v=dQw4w9WgXcQ")

    def test_rejects_invalid_url(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId.from_url("not a url at all")

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId.from_url("")

    def test_rejects_unsupported_scheme(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId.from_url("ftp://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_rejects_watch_without_v_param(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId.from_url("https://www.youtube.com/watch")

    def test_rejects_unsupported_path(self) -> None:
        with pytest.raises(InvalidYouTubeUrlError):
            VideoId.from_url("https://www.youtube.com/channel/UCxxxxx")


class TestVideoIdMethods:
    def test_canonical_url(self) -> None:
        video_id = VideoId(value="dQw4w9WgXcQ")
        assert video_id.canonical_url() == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_str_returns_value(self) -> None:
        video_id = VideoId(value="dQw4w9WgXcQ")
        assert str(video_id) == "dQw4w9WgXcQ"

    def test_equality_by_value(self) -> None:
        a = VideoId(value="dQw4w9WgXcQ")
        b = VideoId(value="dQw4w9WgXcQ")
        c = VideoId(value="j2p8p7cg0q8")
        assert a == b
        assert a != c

    def test_hashable_for_use_in_sets(self) -> None:
        a = VideoId(value="dQw4w9WgXcQ")
        b = VideoId(value="dQw4w9WgXcQ")
        assert {a, b} == {a}
