from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeError
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import YtDlpDownloader


class _FakeYDL:
    def __init__(self, params: dict[str, Any]) -> None:
        self.params = params

    def __enter__(self) -> _FakeYDL:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        return {
            "title": "fixture",
            "uploader": "fixture",
            "duration": 1,
            "ext": "m4a",
        }


def test_youtube_adapter_enables_supported_js_runtimes() -> None:
    captured: list[_FakeYDL] = []

    def factory(params: dict[str, Any]) -> _FakeYDL:
        ydl = _FakeYDL(params)
        captured.append(ydl)
        return ydl

    downloader = YtDlpDownloader(
        ydl_factory=factory,
        subtitle_fetcher=lambda url, ext: "",
    )
    downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    assert captured
    assert captured[0].params["js_runtimes"] == {"deno": {}, "node": {}}


def test_youtube_adapter_keeps_cookie_browser_with_js_runtimes() -> None:
    captured: list[_FakeYDL] = []

    def factory(params: dict[str, Any]) -> _FakeYDL:
        ydl = _FakeYDL(params)
        captured.append(ydl)
        return ydl

    downloader = YtDlpDownloader(
        ydl_factory=factory,
        subtitle_fetcher=lambda url, ext: "",
        cookies_browser="firefox",
    )
    downloader.fetch_metadata(VideoId(value="dQw4w9WgXcQ"))

    params = captured[0].params
    assert params["cookiesfrombrowser"] == ("firefox",)
    assert params["js_runtimes"] == {"deno": {}, "node": {}}


def _multi_audio_listing() -> dict[str, Any]:
    return {
        "title": "fixture",
        "uploader": "fixture",
        "duration": 10,
        "language": "en",
        "formats": [
            {
                "format_id": "18",
                "ext": "mp4",
                "acodec": "mp4a.40.2",
                "vcodec": "avc1.42001E",
            },
            {
                "format_id": "140-3",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "abr": 128,
                "language": "es-US",
                "format_note": "Spanish auto-dubbed",
            },
            {
                "format_id": "140-drc",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "abr": 129,
                "language": "en-US",
                "format_note": "English original (default), DRC",
            },
            {
                "format_id": "140-20",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "abr": 128,
                "language": "en-US",
                "format_note": "English original (default)",
            },
        ],
    }


class _MultiAudioYDL:
    def __init__(self, params: dict[str, Any], calls: list[dict[str, Any]]) -> None:
        self.params = params
        self._calls = calls

    def __enter__(self) -> _MultiAudioYDL:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        self._calls.append(dict(self.params))
        listing = _multi_audio_listing()
        if self.params.get("listformats"):
            return listing
        if self.params.get("format") != "140-20":
            raise AssertionError(
                f"unexpected non-original download selector: {self.params.get('format')}"
            )
        outtmpl = str(self.params["outtmpl"])
        path = Path(outtmpl.replace("%(ext)s", "m4a"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        return {
            **listing,
            "ext": "m4a",
            "format_id": "140-20",
            "language": "en-US",
            "format_note": "English original (default)",
            "requested_downloads": [{"filepath": str(path)}],
        }


def test_youtube_original_marker_supports_regional_language_codes() -> None:
    listing = _multi_audio_listing()
    language = YtDlpDownloader._infer_original_language(listing)
    alternates, has_alternates = YtDlpDownloader._collect_alternate_languages(listing)

    assert language is not None
    assert language.code == "en"
    assert has_alternates is True
    assert {item.code for item in alternates} == {"es"}
    assert YtDlpDownloader._select_original_audio_candidate_format_ids(listing)[:2] == (
        "140-20",
        "140-drc",
    )


def test_download_audio_uses_explicit_original_before_generic_selector(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def factory(params: dict[str, Any]) -> _MultiAudioYDL:
        return _MultiAudioYDL(params, calls)

    downloader = YtDlpDownloader(
        ydl_factory=factory,
        subtitle_fetcher=lambda url, ext: "",
    )
    result = downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)

    download_formats = [
        str(call.get("format")) for call in calls if call.get("skip_download") is False
    ]
    assert download_formats == ["140-20"]
    assert result.metadata.original_language is not None
    assert result.metadata.original_language.code == "en"
    assert result.used_alternate_track is True


def test_explicit_original_failure_never_silently_falls_back_to_auto_dub(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    class _FailingOriginalYDL(_MultiAudioYDL):
        def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
            self._calls.append(dict(self.params))
            if self.params.get("listformats"):
                return _multi_audio_listing()
            raise RuntimeError("HTTP Error 403: Forbidden")

    def factory(params: dict[str, Any]) -> _FailingOriginalYDL:
        return _FailingOriginalYDL(params, calls)

    downloader = YtDlpDownloader(
        ydl_factory=factory,
        subtitle_fetcher=lambda url, ext: "",
    )

    with pytest.raises(YouTubeError, match="faixa de áudio original"):
        downloader.download_audio(VideoId(value="dQw4w9WgXcQ"), tmp_path)

    download_formats = [
        str(call.get("format")) for call in calls if call.get("skip_download") is False
    ]
    assert download_formats == ["140-20", "140-drc"]
