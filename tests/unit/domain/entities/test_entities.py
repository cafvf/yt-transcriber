"""Testes das entidades de domínio."""

from __future__ import annotations

from datetime import date

import pytest

from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.transcript import (
    Transcript,
    TranscriptSegment,
)
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId

# ----------------------------------------------------------------------
# VideoMetadata
# ----------------------------------------------------------------------


class TestVideoMetadata:
    def _make(self, **overrides: object) -> VideoMetadata:
        defaults: dict[str, object] = {
            "video_id": VideoId(value="dQw4w9WgXcQ"),
            "title": "Sample Title",
            "channel": "Sample Channel",
            "duration": Duration.from_minutes(5),
            "upload_date": date(2024, 3, 15),
            "original_language": Language.en(),
        }
        defaults.update(overrides)
        return VideoMetadata(**defaults)  # type: ignore[arg-type]

    def test_construction_with_all_fields(self) -> None:
        meta = self._make()
        assert meta.title == "Sample Title"
        assert meta.canonical_url() == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_empty_title_raises(self) -> None:
        with pytest.raises(ValueError, match="title"):
            self._make(title="")

    def test_empty_channel_raises(self) -> None:
        with pytest.raises(ValueError, match="channel"):
            self._make(channel="")

    def test_optional_upload_date_can_be_none(self) -> None:
        meta = self._make(upload_date=None)
        assert meta.upload_date is None

    def test_alternate_languages_default_empty(self) -> None:
        meta = self._make()
        assert meta.alternate_languages == ()

    def test_immutable(self) -> None:
        meta = self._make()
        with pytest.raises(Exception):  # noqa: B017,PT011
            meta.title = "Other"  # type: ignore[misc]


# ----------------------------------------------------------------------
# Transcript
# ----------------------------------------------------------------------


def _seg(start: float, end: float, label: str, text: str = "lorem") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, speaker_label=label, text=text)


class TestTranscriptSegment:
    def test_construction_succeeds(self) -> None:
        seg = _seg(0.0, 1.0, "SPEAKER_00")
        assert seg.text == "lorem"

    def test_negative_start_raises(self) -> None:
        with pytest.raises(ValueError, match="start_seconds"):
            TranscriptSegment(start_seconds=-1, end_seconds=1, speaker_label="A", text="x")

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end_seconds"):
            TranscriptSegment(start_seconds=5, end_seconds=2, speaker_label="A", text="x")

    def test_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="text"):
            TranscriptSegment(start_seconds=0, end_seconds=1, speaker_label="A", text="")

    def test_empty_label_raises(self) -> None:
        with pytest.raises(ValueError, match="speaker_label"):
            TranscriptSegment(start_seconds=0, end_seconds=1, speaker_label="", text="x")


class TestTranscript:
    def test_construction_with_segments(self) -> None:
        t = Transcript(
            segments=(_seg(0, 1, "S0", "hello"),),
            language=Language.en(),
            language_confidence=0.95,
        )
        assert t.language_confidence == 0.95

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="language_confidence"):
            Transcript(
                segments=(_seg(0, 1, "S0"),),
                language=Language.pt(),
                language_confidence=1.5,
            )

    def test_invalid_source_raises(self) -> None:
        with pytest.raises(ValueError, match="source"):
            Transcript(
                segments=(_seg(0, 1, "S0"),),
                language=Language.pt(),
                source="invalid",
            )

    def test_to_speaker_turns_groups_consecutive_segments(self) -> None:
        segments = (
            _seg(0, 1, "S0", "a"),
            _seg(1, 2, "S0", "b"),
            _seg(2, 3, "S1", "c"),
            _seg(3, 4, "S1", "d"),
            _seg(4, 5, "S0", "e"),
        )
        t = Transcript(segments=segments, language=Language.en())
        turns = t.to_speaker_turns()
        assert len(turns) == 3
        assert turns[0].speaker_label == "S0"
        assert turns[0].text == "a b"
        assert turns[1].speaker_label == "S1"
        assert turns[1].text == "c d"
        assert turns[2].speaker_label == "S0"

    def test_to_speaker_turns_with_empty_returns_empty(self) -> None:
        t = Transcript(segments=(), language=Language.pt())
        assert t.to_speaker_turns() == ()

    def test_speaker_labels_in_order(self) -> None:
        segments = (
            _seg(0, 1, "S2"),
            _seg(1, 2, "S0"),
            _seg(2, 3, "S2"),
            _seg(3, 4, "S1"),
        )
        t = Transcript(segments=segments, language=Language.en())
        assert t.speaker_labels() == ("S2", "S0", "S1")

    def test_speaker_speaking_time(self) -> None:
        segments = (
            _seg(0, 10, "S0"),
            _seg(10, 25, "S1"),
            _seg(25, 30, "S0"),
        )
        t = Transcript(segments=segments, language=Language.en())
        totals = t.speaker_speaking_time()
        assert totals["S0"].seconds == 15
        assert totals["S1"].seconds == 15

    def test_speaker_speaking_time_ignores_zero_duration_segments(self) -> None:
        segments = (
            _seg(0, 0, "UNKNOWN"),
            _seg(0, 3, "S0"),
        )
        t = Transcript(segments=segments, language=Language.en())
        totals = t.speaker_speaking_time()
        assert "UNKNOWN" not in totals
        assert totals["S0"].seconds == 3

    def test_turn_duration_property(self) -> None:
        t = Transcript(segments=(_seg(10, 25, "S0"),), language=Language.en())
        turns = t.to_speaker_turns()
        assert turns[0].duration.seconds == 15


# ----------------------------------------------------------------------
# Job
# ----------------------------------------------------------------------


class TestJob:
    def test_new_starts_pending(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=42)
        assert job.status is JobStatus.PENDING
        assert job.requested_by_user_id == 42
        assert job.error_message is None
        assert not job.is_terminal()

    def test_unique_job_ids(self) -> None:
        j1 = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        j2 = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        assert j1.job_id != j2.job_id

    def test_transition_updates_status_and_timestamp(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        before = job.updated_at
        job.transition_to(JobStatus.DOWNLOADING)
        assert job.status is JobStatus.DOWNLOADING
        assert job.updated_at >= before

    def test_transition_to_failed_records_error(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        job.transition_to(JobStatus.FAILED, error="boom")
        assert job.error_message == "boom"
        assert job.is_terminal()

    def test_transition_after_completed_blocked(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        job.transition_to(JobStatus.COMPLETED)
        with pytest.raises(ValueError, match="terminal"):
            job.transition_to(JobStatus.PENDING)

    def test_transition_idempotent_on_same_terminal(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        job.transition_to(JobStatus.COMPLETED)
        # mesmo terminal → não levanta
        job.transition_to(JobStatus.COMPLETED)

    def test_apply_rename_records_mapping(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        job.apply_rename("SPEAKER_00", "Eduardo")
        assert job.speaker_renames == {"SPEAKER_00": "Eduardo"}

    def test_apply_rename_strips_whitespace(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        job.apply_rename("SPEAKER_00", "  Eduardo  ")
        assert job.speaker_renames == {"SPEAKER_00": "Eduardo"}

    def test_apply_rename_empty_label_raises(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        with pytest.raises(ValueError, match="original_label"):
            job.apply_rename("", "Eduardo")

    def test_apply_rename_empty_name_raises(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        with pytest.raises(ValueError, match="new_name"):
            job.apply_rename("SPEAKER_00", "  ")

    def test_reset_renames(self) -> None:
        job = Job.new(VideoId(value="dQw4w9WgXcQ"), user_id=1)
        job.apply_rename("SPEAKER_00", "Eduardo")
        job.reset_renames()
        assert job.speaker_renames == {}
