"""Gate A1: classificação de faixa no adaptador yt-dlp."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from yt_transcriber_bot.application.ports.youtube_downloader import YouTubeError
from yt_transcriber_bot.domain.value_objects.audio_track import AudioTrackSelection
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import YtDlpDownloader


class _ScenarioYDL:
    def __init__(
        self,
        params: dict[str, Any],
        calls: list[dict[str, Any]],
        listing: dict[str, Any],
        downloads: dict[str, dict[str, Any] | Exception],
    ) -> None:
        self.params = params
        self._calls = calls
        self._listing = listing
        self._downloads = downloads

    def __enter__(self) -> _ScenarioYDL:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def extract_info(self, url: str, download: bool = True) -> dict[str, Any]:
        self._calls.append(dict(self.params))
        if self.params.get("listformats"):
            return self._listing

        selector = str(self.params.get("format") or "*")
        payload = self._downloads.get(selector, self._downloads.get("*"))
        if payload is None:
            raise AssertionError(f"unexpected download selector: {selector}")
        if isinstance(payload, Exception):
            raise payload

        result = dict(payload)
        outtmpl = str(self.params["outtmpl"])
        ext = str(result.get("ext") or "m4a")
        path = Path(outtmpl.replace("%(ext)s", ext))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        result.setdefault("requested_downloads", [{"filepath": str(path)}])
        return result


def _downloader(
    listing: dict[str, Any],
    downloads: dict[str, dict[str, Any] | Exception],
    calls: list[dict[str, Any]],
) -> YtDlpDownloader:
    def factory(params: dict[str, Any]) -> _ScenarioYDL:
        return _ScenarioYDL(params, calls, listing, downloads)

    return YtDlpDownloader(
        ydl_factory=factory,
        subtitle_fetcher=lambda url, ext: "",
    )


def test_generic_ordinary_path_is_default_not_alternate(tmp_path: Path) -> None:
    listing = {
        "title": "fixture",
        "uploader": "fixture",
        "duration": 10,
        "language": "en",
        "formats": [
            {
                "format_id": "140",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "language": "en",
            }
        ],
    }
    downloaded = {
        **listing,
        "ext": "m4a",
        "format_id": "140",
    }
    calls: list[dict[str, Any]] = []
    result = _downloader(listing, {"*": downloaded}, calls).download_audio(
        VideoId("dQw4w9WgXcQ"),
        tmp_path,
    )

    assert result.track_selection is AudioTrackSelection.DEFAULT
    assert result.metadata.has_alternate_audio_tracks is False


def test_first_original_candidate_may_fail_then_second_original_succeeds(
    tmp_path: Path,
) -> None:
    listing = {
        "title": "fixture",
        "uploader": "fixture",
        "duration": 10,
        "formats": [
            {
                "format_id": "140-main",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "language": "en-US",
                "format_note": "English original (default)",
                "abr": 129,
            },
            {
                "format_id": "140-drc",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "language": "en-US",
                "format_note": "English original DRC",
                "abr": 128,
            },
            {
                "format_id": "140-es",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "language": "es-US",
                "format_note": "Spanish auto-dubbed",
            },
        ],
    }
    second = {
        **listing,
        "ext": "m4a",
        "format_id": "140-drc",
        "language": "en-US",
        "format_note": "English original DRC",
    }
    calls: list[dict[str, Any]] = []
    result = _downloader(
        listing,
        {
            "140-main": RuntimeError("temporary original failure"),
            "140-drc": second,
        },
        calls,
    ).download_audio(VideoId("dQw4w9WgXcQ"), tmp_path)

    download_formats = [
        str(call.get("format")) for call in calls if call.get("skip_download") is False
    ]
    assert download_formats == ["140-main", "140-drc"]
    assert result.track_selection is AudioTrackSelection.ORIGINAL
    assert result.metadata.has_alternate_audio_tracks is True


def test_known_alternates_without_selectable_original_fail_closed(
    tmp_path: Path,
) -> None:
    listing = {
        "title": "fixture",
        "uploader": "fixture",
        "duration": 10,
        "formats": [
            {
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "language": "en-US",
                "format_note": "English original (default)",
            },
            {
                "format_id": "140-es",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "vcodec": "none",
                "language": "es-US",
                "format_note": "Spanish auto-dubbed",
            },
        ],
    }
    calls: list[dict[str, Any]] = []

    with pytest.raises(YouTubeError, match="não pôde ser identificada com segurança"):
        _downloader(listing, {}, calls).download_audio(
            VideoId("dQw4w9WgXcQ"),
            tmp_path,
        )

    assert len(calls) == 1
    assert calls[0]["listformats"] is True
