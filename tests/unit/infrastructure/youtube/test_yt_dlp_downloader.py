"""Testes do ``YtDlpDownloader`` com mocks da factory do yt-dlp."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

import pytest

from yt_transcriber_bot.application.ports.youtube_downloader import (
    AgeRestrictedError,
    MembersOnlyError,
    NoAudioStreamError,
    SubtitleTrack,
    VideoUnavailableError,
    YouTubeError,
)
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import YtDlpDownloader


class _FakeYDL:
    def __init__(self, params: dict[str, Any], info_or_exc: Any) -> None:
        self.params = params
        self._info_or_exc = info_or_exc
        self.received_url: str | None = None
        self.received_download: bool | None = None

    def __enter__(self) -> _FakeYDL:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        self.received_url = url
        self.received_download = download
        if isinstance(self._info_or_exc, Exception):
            raise self._info_or_exc
        if download and isinstance(self._info_or_exc, dict):
            # Simular escrita do arquivo se um path foi fornecido.
            outtmpl = self.params.get("outtmpl")
            if isinstance(outtmpl, str):
                ext = self._info_or_exc.get("ext", "m4a")
                resolved = outtmpl.replace("%(ext)s", ext)
                Path(resolved).parent.mkdir(parents=True, exist_ok=True)
                Path(resolved).write_bytes(b"\x00\x01\x02")
                self._info_or_exc.setdefault("requested_downloads", [{"filepath": resolved}])
        return self._info_or_exc


def _factory_returning(info_or_exc: Any) -> Any:
    captured: list[_FakeYDL] = []

    def factory(params: dict[str, Any]) -> _FakeYDL:
        ydl = _FakeYDL(params, info_or_exc)
        captured.append(ydl)
        return ydl

    factory.captured = captured  # type: ignore[attr-defined]
    return factory


def _make(
    info_or_exc: Any,
    *,
    subtitle_payload: str = "",
    cookies_file: str | None = None,
    cookies_browser: str | None = None,
) -> YtDlpDownloader:
    return YtDlpDownloader(
        ydl_factory=_factory_returning(info_or_exc),
        subtitle_fetcher=lambda url, ext: subtitle_payload,
        cookies_file=cookies_file,
        cookies_browser=cookies_browser,
    )


# ----------------------------------------------------------------------
# fetch_metadata
# ----------------------------------------------------------------------


class TestFetchMetadata:
    def test_returns_complete_metadata(self) -> None:
        info = {
            "title": "How to remember EVERYTHING",
            "uploader": "Eduardo Filho",
            "duration": 305,
            "upload_date": "20240315",
            "language": "en",
        }
        downloader = _make(info)
        meta = downloader.fetch_metadata(VideoId(value="j2p8p7cg0q8"))
        assert meta.title == "How to remember EVERYTHING"
        assert meta.channel == "Eduardo Filho"
        assert meta.duration.seconds == 305
        assert meta.upload_date == date(2024, 3, 15)
        assert meta.original_language == Language.en()

    def test_falls_back_to_channel_field(self) -> None:
        info = {
            "title": "x",
            "channel": "BackupChannel",
            "duration": 10,
            "upload_date": "20240101",
        }
        meta = _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        assert meta.channel == "BackupChannel"

    def test_handles_missing_upload_date(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        meta = _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        assert meta.upload_date is None

    def test_missing_title_raises(self) -> None:
        info = {"title": "", "uploader": "x", "duration": 1}
        with pytest.raises(YouTubeError, match="título"):
            _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    def test_missing_channel_raises(self) -> None:
        info = {"title": "x", "uploader": "", "duration": 1}
        with pytest.raises(YouTubeError, match="canal"):
            _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    def test_canonical_url_passed_to_ydl(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        downloader = _make(info)
        downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

        captured = downloader._ydl_factory.captured  # type: ignore[attr-defined]
        assert captured[0].received_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_metadata_extraction_uses_permissive_format_params(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        downloader = _make(info)
        downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

        captured = downloader._ydl_factory.captured  # type: ignore[attr-defined]
        params = captured[0].params
        assert params["format"] == "bestaudio/best[acodec!=none]/best/worst"
        assert params["ignore_no_formats_error"] is True
        assert params["ignoreconfig"] is True


class TestErrorMapping:
    def test_members_only_mapped(self) -> None:
        downloader = _make(RuntimeError("Join this channel to get access (members-only)"))
        with pytest.raises(MembersOnlyError):
            downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    def test_age_restricted_mapped(self) -> None:
        downloader = _make(RuntimeError("Sign in to confirm your age. Age-restricted"))
        with pytest.raises(AgeRestrictedError):
            downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    def test_unavailable_mapped(self) -> None:
        downloader = _make(RuntimeError("Private video"))
        with pytest.raises(VideoUnavailableError):
            downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    def test_geo_mapped_to_unavailable(self) -> None:
        downloader = _make(RuntimeError("Video unavailable in your country (geo)"))
        with pytest.raises(VideoUnavailableError):
            downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    def test_generic_mapped_to_youtube_error(self) -> None:
        downloader = _make(RuntimeError("something else"))
        with pytest.raises(YouTubeError):
            downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    def test_format_unavailable_on_metadata_retries_with_widest_selector(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        calls: list[_FakeYDL] = []

        def factory(params: dict[str, Any]) -> _FakeYDL:
            payload: Any = RuntimeError("Requested format is not available") if not calls else info
            ydl = _FakeYDL(params, payload)
            calls.append(ydl)
            return ydl

        downloader = YtDlpDownloader(
            ydl_factory=factory,
            subtitle_fetcher=lambda url, ext: "",
        )

        meta = downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

        assert meta.title == "x"
        assert len(calls) == 2
        assert calls[1].params["format"] == "best/worst"
        assert calls[1].params["ignore_no_formats_error"] is True


# ----------------------------------------------------------------------
# auto-dub detection
# ----------------------------------------------------------------------


class TestAutoDubDetection:
    def test_detects_original_language_via_orig_suffix(self) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "formats": [
                {"language": "en-orig", "ext": "m4a"},
                {"language": "pt", "ext": "m4a"},
                {"language": "es", "ext": "m4a"},
            ],
        }
        meta = _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        assert meta.original_language == Language.en()
        assert meta.has_alternate_audio_tracks is True
        assert {lang.code for lang in meta.alternate_languages} == {"pt", "es"}

    def test_no_dub_when_only_original(self) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "formats": [{"language": "en-orig", "ext": "m4a"}],
        }
        meta = _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        assert meta.has_alternate_audio_tracks is False
        assert meta.alternate_languages == ()

    def test_no_dub_when_no_orig_marker(self) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "formats": [{"language": "en", "ext": "m4a"}],
            "language": "en",
        }
        meta = _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        assert meta.has_alternate_audio_tracks is False

    def test_falls_back_to_en_when_no_language(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        meta = _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        assert meta.original_language == Language.en()

    def test_uses_top_level_language_when_formats_unmarked(self) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "language": "pt",
            "formats": [],
        }
        meta = _make(info).fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        assert meta.original_language == Language.pt()


# ----------------------------------------------------------------------
# Subtitles
# ----------------------------------------------------------------------


class TestListSubtitles:
    def test_returns_manual_and_auto_tracks(self) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "subtitles": {
                "en": [{"ext": "vtt", "url": "https://example.com/en.vtt"}],
                "pt": [{"ext": "vtt", "url": "https://example.com/pt.vtt"}],
            },
            "automatic_captions": {
                "en": [{"ext": "vtt", "url": "https://example.com/en.auto.vtt"}],
            },
        }
        tracks = _make(info).list_subtitles(VideoId(value="dQw4w9WgXcQ"))
        assert any(t.language == Language.en() and not t.is_auto_generated for t in tracks)
        assert any(t.language == Language.en() and t.is_auto_generated for t in tracks)
        assert any(t.language == Language.pt() for t in tracks)

    def test_filters_translated_variants(self) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "automatic_captions": {
                "en": [{"ext": "vtt", "url": "https://example.com/en.vtt"}],
                "pt-en": [{"ext": "vtt", "url": "https://example.com/pt-en.vtt"}],
            },
        }
        tracks = _make(info).list_subtitles(VideoId(value="dQw4w9WgXcQ"))
        # ``pt-en`` é tradução; deve ser marcado como is_translated=True
        translated = [t for t in tracks if t.is_translated]
        assert len(translated) == 1
        assert translated[0].language == Language.pt()

    def test_prefers_vtt_over_other_formats(self) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "subtitles": {
                "en": [
                    {"ext": "ttml", "url": "https://example.com/x.ttml"},
                    {"ext": "vtt", "url": "https://example.com/x.vtt"},
                ],
            },
        }
        tracks = _make(info).list_subtitles(VideoId(value="dQw4w9WgXcQ"))
        assert tracks[0].ext == "vtt"

    def test_empty_returns_empty_tuple(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        tracks = _make(info).list_subtitles(VideoId(value="dQw4w9WgXcQ"))
        assert tracks == ()

    def test_subtitle_listing_uses_permissive_format_params(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        downloader = _make(info)
        downloader.list_subtitles(VideoId(value="dQw4w9WgXcQ"))

        captured = downloader._ydl_factory.captured  # type: ignore[attr-defined]
        params = captured[0].params
        assert params["format"] == "bestaudio/best[acodec!=none]/best/worst"
        assert params["ignore_no_formats_error"] is True


class TestFetchSubtitle:
    def test_parses_vtt_simple(self) -> None:
        vtt = """WEBVTT

1
00:00:00.000 --> 00:00:05.000
Hello world

2
00:00:05.000 --> 00:00:10.500
Second segment
"""
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload=vtt,
        )
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=False,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        assert result.language == Language.en()
        assert len(result.segments) == 2
        s0, e0, t0 = result.segments[0]
        assert s0 == pytest.approx(0.0)
        assert e0 == pytest.approx(5.0)
        assert t0 == "Hello world"
        _s1, e1, t1 = result.segments[1]
        assert e1 == pytest.approx(10.5)
        assert t1 == "Second segment"

    def test_parses_srt_with_comma(self) -> None:
        srt = """1
00:00:00,000 --> 00:00:02,000
Olá mundo

2
00:00:02,000 --> 00:00:04,000
Segunda linha
"""
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload=srt,
        )
        track = SubtitleTrack(
            language=Language.pt(),
            is_auto_generated=False,
            is_translated=False,
            url="https://example.com/x.srt",
            ext="srt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        assert len(result.segments) == 2
        assert result.segments[0][2] == "Olá mundo"

    def test_strips_inline_tags(self) -> None:
        vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
<c.colorred>Hello</c> world
"""
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload=vtt,
        )
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=True,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        assert result.segments[0][2] == "Hello world"

    def test_decodes_html_entities_and_nbsp(self) -> None:
        vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Ol&aacute;&nbsp;mundo &amp;#39;teste&amp;#39;
"""
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload=vtt,
        )
        track = SubtitleTrack(
            language=Language.pt(),
            is_auto_generated=True,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        assert result.segments[0][2] == "Olá mundo 'teste'"

    def test_discards_zero_duration_cues(self) -> None:
        vtt = """WEBVTT

00:00:00.000 --> 00:00:00.000
Ghost

00:00:00.000 --> 00:00:02.000
Hello world
"""
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload=vtt,
        )
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=True,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        assert result.segments == ((0.0, 2.0, "Hello world"),)

    def test_empty_payload_returns_no_segments(self) -> None:
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload="",
        )
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=False,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        assert result.segments == ()

    def test_retries_transient_http_429_before_succeeding(self) -> None:
        calls = 0
        sleeps: list[float] = []
        vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Hello world
"""

        def fetcher(url: str, ext: str) -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
            return vtt

        downloader = YtDlpDownloader(
            ydl_factory=_factory_returning({"title": "x", "uploader": "y", "duration": 10}),
            subtitle_fetcher=fetcher,
            sleep_fn=sleeps.append,
        )
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=False,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )

        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)

        assert calls == 3
        assert sleeps == [0.5, 1.0]
        assert result.segments == ((0.0, 2.0, "Hello world"),)

    def test_exhausts_transient_retries_and_reraises(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def fetcher(url: str, ext: str) -> str:
            nonlocal calls
            calls += 1
            raise URLError("temporary DNS failure")

        downloader = YtDlpDownloader(
            ydl_factory=_factory_returning({"title": "x", "uploader": "y", "duration": 10}),
            subtitle_fetcher=fetcher,
            sleep_fn=sleeps.append,
        )
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=False,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )

        with pytest.raises(URLError, match="temporary DNS failure"):
            downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)

        assert calls == 3
        assert sleeps == [0.5, 1.0]

    def test_non_transient_http_error_does_not_retry(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def fetcher(url: str, ext: str) -> str:
            nonlocal calls
            calls += 1
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

        downloader = YtDlpDownloader(
            ydl_factory=_factory_returning({"title": "x", "uploader": "y", "duration": 10}),
            subtitle_fetcher=fetcher,
            sleep_fn=sleeps.append,
        )
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=False,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )

        with pytest.raises(HTTPError, match="Not Found"):
            downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)

        assert calls == 1
        assert sleeps == []

    def test_track_without_url_raises(self) -> None:
        downloader = _make({"title": "x", "uploader": "y", "duration": 10})
        track = SubtitleTrack(
            language=Language.en(),
            is_auto_generated=False,
            is_translated=False,
            url=None,
            ext="vtt",
        )
        with pytest.raises(YouTubeError, match="URL"):
            downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)


# ----------------------------------------------------------------------
# Audio download
# ----------------------------------------------------------------------


class TestDownloadAudio:
    def test_downloads_to_dest_dir(self, tmp_path: Path) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "ext": "m4a",
            "language": "en-orig",
        }
        downloader = _make(info)
        result = downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)
        assert result.audio_path.exists()
        assert result.audio_path.parent == tmp_path
        assert result.container == "m4a"

    def test_download_uses_audio_format_with_muxed_fallbacks(self, tmp_path: Path) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10, "ext": "m4a"}
        downloader = _make(info)
        downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)

        captured = downloader._ydl_factory.captured  # type: ignore[attr-defined]
        assert captured[0].params["format"] == (
            "18/22/"
            "best[ext=mp4][acodec!=none][vcodec!=none]/"
            "worst[acodec!=none][vcodec!=none]/"
            "best[acodec!=none][vcodec!=none]/"
            "bestaudio/"
            "best[acodec!=none]/"
            "best/"
            "worst"
        )

    def test_format_unavailable_download_falls_back_to_discovered_progressive_format(
        self, tmp_path: Path
    ) -> None:
        listing_info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "formats": [
                {
                    "format_id": "140",
                    "ext": "m4a",
                    "acodec": "mp4a.40.2",
                    "vcodec": "none",
                    "abr": 128,
                },
                {
                    "format_id": "18",
                    "ext": "mp4",
                    "acodec": "mp4a.40.2",
                    "vcodec": "avc1.42001E",
                    "height": 360,
                    "filesize_approx": 1_000_000,
                },
            ],
        }
        final_info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "ext": "mp4",
            "format_id": "18",
            "formats": listing_info["formats"],
        }
        calls: list[_FakeYDL] = []

        def factory(params: dict[str, Any]) -> _FakeYDL:
            fmt = params.get("format")
            download = params.get("skip_download") is False
            if not calls and download:
                payload: Any = RuntimeError("Requested format is not available")
            elif not download:
                payload = listing_info
            elif fmt == "140":
                payload = RuntimeError("HTTP Error 403: Forbidden")
            elif fmt == "18":
                payload = final_info
            else:
                payload = RuntimeError(f"unexpected format: {fmt}")
            ydl = _FakeYDL(params, payload)
            calls.append(ydl)
            return ydl

        downloader = YtDlpDownloader(ydl_factory=factory, subtitle_fetcher=lambda url, ext: "")

        result = downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)

        assert result.audio_path.exists()
        assert result.container == "mp4"
        assert [call.params.get("format") for call in calls] == [
            "18/22/"
            "best[ext=mp4][acodec!=none][vcodec!=none]/"
            "worst[acodec!=none][vcodec!=none]/"
            "best[acodec!=none][vcodec!=none]/"
            "bestaudio/"
            "best[acodec!=none]/"
            "best/"
            "worst",
            None,
            "140",
            "18",
        ]
        assert calls[1].params["listformats"] is True
        assert calls[1].params["simulate"] is True

    def test_discovered_formats_failure_reports_diagnostic_without_default_selector(
        self, tmp_path: Path
    ) -> None:
        calls: list[_FakeYDL] = []

        def factory(params: dict[str, Any]) -> _FakeYDL:
            fmt = params.get("format")
            download = params.get("skip_download") is False
            if not calls and download:
                payload: Any = RuntimeError("Requested format is not available")
            elif not download:
                payload = {"title": "x", "uploader": "y", "duration": 10, "formats": []}
            else:
                payload = RuntimeError(f"format {fmt} also unavailable")
            ydl = _FakeYDL(params, payload)
            calls.append(ydl)
            return ydl

        downloader = YtDlpDownloader(ydl_factory=factory, subtitle_fetcher=lambda url, ext: "")

        with pytest.raises(YouTubeError, match="formatos_listados=0"):
            downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)

        # Não deve haver tentativa final com format=None em modo download; isso
        # apenas repete o seletor padrão problemático do yt-dlp.
        download_formats = [
            c.params.get("format") for c in calls if c.params.get("skip_download") is False
        ]
        assert download_formats == [
            "18/22/"
            "best[ext=mp4][acodec!=none][vcodec!=none]/"
            "worst[acodec!=none][vcodec!=none]/"
            "best[acodec!=none][vcodec!=none]/"
            "bestaudio/"
            "best[acodec!=none]/"
            "best/"
            "worst",
            "18",
            "22",
            "140",
            "139",
            "251",
            "250",
            "249",
        ]

    def test_marks_used_alternate_track_when_orig_present(self, tmp_path: Path) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "ext": "m4a",
            "language": "en-orig",
            "formats": [
                {"language": "en-orig", "ext": "m4a"},
                {"language": "pt", "ext": "m4a"},
            ],
        }
        result = _make(info).download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)
        assert result.used_alternate_track is True

    def test_no_orig_does_not_set_used_alternate(self, tmp_path: Path) -> None:
        info = {
            "title": "x",
            "uploader": "y",
            "duration": 10,
            "ext": "m4a",
            "language": "en",
        }
        result = _make(info).download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)
        assert result.used_alternate_track is False

    def test_creates_dest_dir_if_missing(self, tmp_path: Path) -> None:
        sub = tmp_path / "deep" / "path"
        info = {"title": "x", "uploader": "y", "duration": 10, "ext": "webm"}
        downloader = _make(info)
        result = downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), sub)
        assert sub.exists()
        assert result.audio_path.exists()

    def test_empty_file_raises_no_audio_stream(self, tmp_path: Path) -> None:
        # Forçar arquivo vazio: não escrever bytes.
        class _EmptyYDL(_FakeYDL):
            def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
                outtmpl = self.params.get("outtmpl", "")
                resolved = outtmpl.replace("%(ext)s", "m4a")
                Path(resolved).parent.mkdir(parents=True, exist_ok=True)
                Path(resolved).touch()  # 0 bytes
                return {
                    "title": "x",
                    "uploader": "y",
                    "duration": 10,
                    "ext": "m4a",
                    "requested_downloads": [{"filepath": resolved}],
                }

        def factory(params: dict[str, Any]) -> _EmptyYDL:
            return _EmptyYDL(params, {})

        downloader = YtDlpDownloader(
            ydl_factory=factory,
            subtitle_fetcher=lambda url, ext: "",
        )
        with pytest.raises(NoAudioStreamError):
            downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)


class TestCookiesPropagation:
    def test_cookies_file_added_to_params(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        downloader = _make(info, cookies_file="/tmp/cookies.txt")
        downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        captured = downloader._ydl_factory.captured  # type: ignore[attr-defined]
        assert captured[0].params.get("cookiefile") == "/tmp/cookies.txt"

    def test_cookies_browser_added_to_params(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        downloader = _make(info, cookies_browser="firefox")
        downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        captured = downloader._ydl_factory.captured  # type: ignore[attr-defined]
        assert captured[0].params.get("cookiesfrombrowser") == ("firefox",)

    def test_no_cookies_when_none(self) -> None:
        info = {"title": "x", "uploader": "y", "duration": 10}
        downloader = _make(info)
        downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))
        captured = downloader._ydl_factory.captured  # type: ignore[attr-defined]
        assert "cookiefile" not in captured[0].params
        assert "cookiesfrombrowser" not in captured[0].params

    def test_deduplicates_youtube_rolling_auto_captions(self) -> None:
        vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Eu venho usando agentes no meu dia

00:00:02.000 --> 00:00:04.000
Eu venho usando agentes no meu dia a dia há muito tempo

00:00:04.000 --> 00:00:06.000
a dia há muito tempo, Claude Code, Cursor e Copilot
"""
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload=vtt,
        )
        track = SubtitleTrack(
            language=Language.pt(),
            is_auto_generated=True,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        text = " ".join(seg[2] for seg in result.segments)
        assert text == (
            "Eu venho usando agentes no meu dia a dia há muito tempo Claude Code, Cursor e Copilot"
        )

    def test_collapses_repeated_phrase_inside_single_cue(self) -> None:
        vtt = """WEBVTT

00:00:00.000 --> 00:00:02.000
Spec Driven Development Spec Driven Development ajuda a organizar contexto
"""
        downloader = _make(
            {"title": "x", "uploader": "y", "duration": 10},
            subtitle_payload=vtt,
        )
        track = SubtitleTrack(
            language=Language.pt(),
            is_auto_generated=True,
            is_translated=False,
            url="https://example.com/x.vtt",
            ext="vtt",
        )
        result = downloader.fetch_subtitle(VideoId(value="dQw4w9WgXcQ"), track)
        assert result.segments[0][2] == "Spec Driven Development ajuda a organizar contexto"
