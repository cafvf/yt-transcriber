"""Gate A2: comportamento canônico de MediaMetadata."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


def test_youtube_metadata_requires_video_id() -> None:
    with pytest.raises(ValueError, match="video_id é obrigatório para YouTube"):
        MediaMetadata(
            video_id=None,
            title="YouTube item",
            channel="Channel",
            duration=None,
            upload_date=None,
            original_language=None,
        )


def test_source_neutral_metadata_does_not_fabricate_youtube_identity() -> None:
    metadata = MediaMetadata(
        video_id=None,
        title="Telegram audio",
        channel="Telegram",
        duration=Duration.from_seconds(12),
        upload_date=None,
        original_language=None,
        source_label="Telegram",
        source_reference="telegram-media://private-file-id",
    )

    assert metadata.video_id is None
    assert metadata.canonical_url() == "telegram-media://private-file-id"


def test_explicit_source_reference_wins_over_youtube_video_id() -> None:
    metadata = MediaMetadata(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Known",
        channel="Channel",
        duration=None,
        upload_date=None,
        original_language=Language.en(),
        source_reference="https://example.invalid/canonical/source",
    )

    assert metadata.canonical_url() == "https://example.invalid/canonical/source"


def test_youtube_video_id_is_canonical_reference_fallback() -> None:
    video_id = VideoId("dQw4w9WgXcQ")
    metadata = MediaMetadata(
        video_id=video_id,
        title="Known",
        channel="Channel",
        duration=None,
        upload_date=None,
        original_language=None,
    )

    assert metadata.canonical_url() == video_id.canonical_url()


def test_missing_reference_remains_an_explicit_error() -> None:
    metadata = MediaMetadata(
        video_id=None,
        title="Local media",
        channel="Local",
        duration=None,
        upload_date=None,
        original_language=None,
        source_label="Local",
        source_reference=None,
    )

    with pytest.raises(ValueError, match="sem URL canônica"):
        metadata.canonical_url()


def test_unknown_optional_facts_remain_unknown() -> None:
    metadata = MediaMetadata(
        video_id=VideoId("dQw4w9WgXcQ"),
        title="Unknown facts",
        channel="Channel",
        duration=None,
        upload_date=None,
        original_language=None,
    )

    assert metadata.duration is None
    assert metadata.upload_date is None
    assert metadata.original_language is None
    assert metadata.alternate_languages == ()
