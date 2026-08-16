from __future__ import annotations

import pytest

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.incoming_media import IncomingMedia, IncomingMediaKind
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.workflows.admission import (
    AdmissionRejection,
    AdmissionRejectionCode,
    MediaAdmission,
    PreparedMediaAdmission,
    QueueAdmissionState,
    QueuedSubmission,
    YoutubeAdmission,
    admit_youtube_submission,
    commit_media_submission,
    prepare_validated_media_submission,
    validate_media_submission,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class FakeJobRepository(JobRepository):
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.contexts: dict[str, JobRequestContext] = {}

    def save(self, job: Job) -> None:
        self.jobs[job.job_id] = job

    def get_by_id(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        matches = [job for job in self.jobs.values() if job.video_id == video_id]
        return matches[-1] if matches else None

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        matches = [
            job
            for job in self.jobs.values()
            if job.requested_by_user_id == user_id and job.status is JobStatus.COMPLETED
        ]
        return matches[-1] if matches else None

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        matches = [job for job in self.jobs.values() if job.requested_by_user_id == user_id]
        return matches[:limit]

    def list_completed_oldest_first(self) -> list[Job]:
        return sorted(
            (job for job in self.jobs.values() if job.status is JobStatus.COMPLETED),
            key=lambda job: job.updated_at,
        )

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        return sorted(
            (job for job in self.jobs.values() if job.status in statuses),
            key=lambda job: job.requested_at,
        )

    def delete(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)
        self.contexts.pop(job_id, None)

    def save_request_context(self, context: JobRequestContext) -> None:
        self.contexts[context.job_id] = context

    def get_request_context(self, job_id: str) -> JobRequestContext | None:
        return self.contexts.get(job_id)


def _queue(*items: QueuedSubmission, capacity: int = 5) -> QueueAdmissionState:
    return QueueAdmissionState(items=items, capacity=capacity)


def _media(**overrides: object) -> IncomingMedia:
    values: dict[str, object] = {
        "file_id": "private-file-id",
        "file_name": "voice.ogg",
        "mime_type": "audio/ogg",
        "size_bytes": 1000,
        "duration_seconds": 10,
        "kind": IncomingMediaKind.AUDIO,
    }
    values.update(overrides)
    return IncomingMedia(**values)  # type: ignore[arg-type]


def test_invalid_youtube_source_is_rejected_before_persistence() -> None:
    repository = FakeJobRepository()

    result = admit_youtube_submission(
        repository=repository,
        queue_state=_queue(),
        url="not-a-youtube-url",
        user_id=7,
        delivery_chat_id=11,
        requested_language=None,
        reprocess=False,
        config_signature="sig",
    )

    assert isinstance(result, AdmissionRejection)
    assert result.code is AdmissionRejectionCode.INVALID_SOURCE
    assert repository.jobs == {}


def test_duplicate_is_decided_from_transport_neutral_queue_state() -> None:
    repository = FakeJobRepository()
    video_id = VideoId.from_url("https://youtu.be/dQw4w9WgXcQ")

    result = admit_youtube_submission(
        repository=repository,
        queue_state=_queue(QueuedSubmission(video_id, "pt")),
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        user_id=7,
        delivery_chat_id=11,
        requested_language="pt",
        reprocess=False,
        config_signature="sig",
    )

    assert isinstance(result, AdmissionRejection)
    assert result.code is AdmissionRejectionCode.DUPLICATE
    assert repository.jobs == {}


def test_same_video_with_different_language_remains_admissible() -> None:
    repository = FakeJobRepository()
    video_id = VideoId.from_url("https://youtu.be/dQw4w9WgXcQ")

    result = admit_youtube_submission(
        repository=repository,
        queue_state=_queue(QueuedSubmission(video_id, "en")),
        url="https://youtu.be/dQw4w9WgXcQ",
        user_id=7,
        delivery_chat_id=11,
        requested_language="pt",
        reprocess=False,
        config_signature="sig",
    )

    assert isinstance(result, YoutubeAdmission)
    assert result.job.job_id in repository.jobs


def test_queue_capacity_is_application_admission_policy() -> None:
    repository = FakeJobRepository()

    result = admit_youtube_submission(
        repository=repository,
        queue_state=_queue(QueuedSubmission(None, None), capacity=1),
        url="https://youtu.be/dQw4w9WgXcQ",
        user_id=7,
        delivery_chat_id=11,
        requested_language=None,
        reprocess=False,
        config_signature="sig",
    )

    assert isinstance(result, AdmissionRejection)
    assert result.code is AdmissionRejectionCode.QUEUE_FULL


def test_reprocess_creates_a_fresh_job_instead_of_reusing_history() -> None:
    repository = FakeJobRepository()
    kwargs = {
        "repository": repository,
        "queue_state": _queue(),
        "url": "https://youtu.be/dQw4w9WgXcQ",
        "user_id": 7,
        "delivery_chat_id": 11,
        "requested_language": "pt",
        "config_signature": "sig",
    }

    first = admit_youtube_submission(**kwargs, reprocess=False)
    redo = admit_youtube_submission(**kwargs, reprocess=True)

    assert isinstance(first, YoutubeAdmission)
    assert isinstance(redo, YoutubeAdmission)
    assert redo.is_reprocess is True
    assert first.job.job_id != redo.job.job_id
    assert len(repository.jobs) == 2


@pytest.mark.parametrize(
    ("media", "expected"),
    [
        (_media(file_id=""), AdmissionRejectionCode.INVALID_MEDIA_FILE),
        (_media(mime_type="application/pdf"), AdmissionRejectionCode.UNSUPPORTED_MEDIA),
        (
            _media(kind=IncomingMediaKind.DOCUMENT, file_name=None),
            AdmissionRejectionCode.MISSING_MEDIA_FILENAME,
        ),
        (_media(file_name="sample.exe"), AdmissionRejectionCode.UNSUPPORTED_MEDIA_EXTENSION),
        (_media(size_bytes=0), AdmissionRejectionCode.INVALID_MEDIA_SIZE),
        (_media(size_bytes=2001), AdmissionRejectionCode.MEDIA_TOO_LARGE),
        (_media(duration_seconds=61), AdmissionRejectionCode.MEDIA_TOO_LONG),
    ],
)
def test_media_metadata_rules_are_application_owned(
    media: IncomingMedia, expected: AdmissionRejectionCode
) -> None:
    result = validate_media_submission(
        media,
        max_media_size_bytes=2000,
        max_duration_seconds=60,
    )

    assert isinstance(result, AdmissionRejection)
    assert result.code is expected


def test_private_media_is_prepared_then_committed_after_duration_resolution() -> None:
    repository = FakeJobRepository()
    media = _media(duration_seconds=None)

    prepared = prepare_validated_media_submission(
        queue_state=_queue(),
        media=media,
        user_id=7,
        config_signature="sig-private",
    )
    assert isinstance(prepared, PreparedMediaAdmission)
    assert repository.jobs == {}

    committed = commit_media_submission(
        repository=repository,
        prepared=prepared,
        delivery_chat_id=11,
        source_locator="/private/staging/audio.ogg",
        source_title="voice",
        duration_seconds=42,
        max_duration_seconds=60,
    )

    assert isinstance(committed, MediaAdmission)
    assert committed.job.source_duration_seconds == 42
    assert committed.job.source_title == "voice"
    assert repository.jobs[committed.job.job_id] is committed.job
    assert repository.contexts[committed.job.job_id].source_locator == "/private/staging/audio.ogg"


def test_invalid_resolved_duration_never_persists_private_media() -> None:
    repository = FakeJobRepository()
    prepared = prepare_validated_media_submission(
        queue_state=_queue(),
        media=_media(duration_seconds=None),
        user_id=7,
        config_signature="sig-private",
    )
    assert isinstance(prepared, PreparedMediaAdmission)

    result = commit_media_submission(
        repository=repository,
        prepared=prepared,
        delivery_chat_id=11,
        source_locator="/private/staging/audio.ogg",
        source_title="voice",
        duration_seconds=0,
        max_duration_seconds=60,
    )

    assert isinstance(result, AdmissionRejection)
    assert result.code is AdmissionRejectionCode.INVALID_MEDIA_DURATION
    assert repository.jobs == {}
