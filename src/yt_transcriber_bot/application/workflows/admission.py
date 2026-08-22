"""Application-owned submission/admission workflow."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.incoming_media import (
    IncomingMedia,
    IncomingMediaKind,
)
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource
from yt_transcriber_bot.domain.value_objects.video_id import (
    InvalidYouTubeUrlError,
    VideoId,
)

RequestContextSaver = Callable[[JobRequestContext], None]


class AdmissionRejectionCode(StrEnum):
    INVALID_SOURCE = "invalid_source"
    PERSISTENCE_UNAVAILABLE = "persistence_unavailable"
    DUPLICATE = "duplicate"
    QUEUE_FULL = "queue_full"
    INVALID_MEDIA_FILE = "invalid_media_file"
    UNSUPPORTED_MEDIA = "unsupported_media"
    MISSING_MEDIA_FILENAME = "missing_media_filename"
    UNSUPPORTED_MEDIA_EXTENSION = "unsupported_media_extension"
    INVALID_MEDIA_SIZE = "invalid_media_size"
    MEDIA_TOO_LARGE = "media_too_large"
    MEDIA_TOO_LONG = "media_too_long"
    INVALID_MEDIA_DURATION = "invalid_media_duration"


@dataclass(frozen=True, slots=True)
class AdmissionRejection:
    code: AdmissionRejectionCode
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class QueuedSubmission:
    video_id: VideoId | None
    requested_language: Language | None


@dataclass(frozen=True, slots=True)
class QueueAdmissionState:
    items: tuple[QueuedSubmission, ...]
    capacity: int

    @property
    def size(self) -> int:
        return len(self.items)

    def is_full(self) -> bool:
        return self.size >= self.capacity


@dataclass(frozen=True, slots=True)
class YoutubeAdmission:
    job: Job
    video_id: VideoId
    is_reprocess: bool


@dataclass(frozen=True, slots=True)
class PreparedMediaAdmission:
    job: Job
    media: IncomingMedia


@dataclass(frozen=True, slots=True)
class MediaAdmission:
    job: Job


def admit_youtube_submission(
    *,
    repository: JobRepository | None,
    queue_state: QueueAdmissionState,
    url: str,
    user_id: int,
    delivery_chat_id: int,
    requested_language: Language | None,
    reprocess: bool,
    processing_fingerprint: str,
    request_context_saver: RequestContextSaver | None = None,
) -> YoutubeAdmission | AdmissionRejection:
    try:
        video_id = VideoId.from_url(url)
    except (InvalidYouTubeUrlError, ValueError) as exc:
        return AdmissionRejection(
            AdmissionRejectionCode.INVALID_SOURCE,
            str(exc),
        )

    if repository is None:
        return AdmissionRejection(AdmissionRejectionCode.PERSISTENCE_UNAVAILABLE)

    if any(
        item.video_id == video_id and item.requested_language == requested_language
        for item in queue_state.items
    ):
        return AdmissionRejection(AdmissionRejectionCode.DUPLICATE)

    if queue_state.is_full():
        return AdmissionRejection(AdmissionRejectionCode.QUEUE_FULL)

    job = Job.new(
        video_id=video_id,
        user_id=user_id,
        processing_fingerprint=processing_fingerprint,
        requested_language=requested_language,
    )
    repository.save(job)
    context = JobRequestContext(
        job_id=job.job_id,
        delivery_chat_id=delivery_chat_id,
        source_locator=url,
    )
    if request_context_saver is not None:
        request_context_saver(context)
    else:
        repository.save_request_context(context)
    return YoutubeAdmission(
        job=job,
        video_id=video_id,
        is_reprocess=reprocess,
    )


def validate_media_submission(
    media: IncomingMedia,
    *,
    max_media_size_bytes: int,
    max_duration_seconds: int,
) -> AdmissionRejection | None:
    allowed_extensions = {
        ".mp3",
        ".m4a",
        ".ogg",
        ".opus",
        ".wav",
        ".flac",
        ".webm",
    }
    allowed_mimes = {
        "audio/mpeg",
        "audio/mp4",
        "audio/ogg",
        "audio/opus",
        "audio/wav",
        "audio/x-wav",
        "audio/flac",
        "audio/webm",
    }
    if not media.file_id:
        return AdmissionRejection(AdmissionRejectionCode.INVALID_MEDIA_FILE)
    if media.mime_type and media.mime_type.lower() not in allowed_mimes:
        return AdmissionRejection(AdmissionRejectionCode.UNSUPPORTED_MEDIA)
    if media.kind is IncomingMediaKind.DOCUMENT and not media.file_name:
        return AdmissionRejection(AdmissionRejectionCode.MISSING_MEDIA_FILENAME)
    if media.file_name and Path(media.file_name).suffix.lower() not in allowed_extensions:
        return AdmissionRejection(AdmissionRejectionCode.UNSUPPORTED_MEDIA_EXTENSION)
    if media.size_bytes is None or media.size_bytes <= 0:
        return AdmissionRejection(AdmissionRejectionCode.INVALID_MEDIA_SIZE)
    if media.size_bytes > max_media_size_bytes:
        return AdmissionRejection(AdmissionRejectionCode.MEDIA_TOO_LARGE)
    if media.duration_seconds is not None and media.duration_seconds > max_duration_seconds:
        return AdmissionRejection(AdmissionRejectionCode.MEDIA_TOO_LONG)
    return None


def prepare_validated_media_submission(
    *,
    queue_state: QueueAdmissionState,
    media: IncomingMedia,
    user_id: int,
    processing_fingerprint: str,
) -> PreparedMediaAdmission | AdmissionRejection:
    if queue_state.is_full():
        return AdmissionRejection(AdmissionRejectionCode.QUEUE_FULL)
    job = Job.new(
        video_id=None,
        user_id=user_id,
        processing_fingerprint=processing_fingerprint,
        media_source=MediaSource.telegram_audio(media.file_id),
    )
    return PreparedMediaAdmission(job=job, media=media)


def commit_media_submission(
    *,
    repository: JobRepository,
    prepared: PreparedMediaAdmission,
    delivery_chat_id: int,
    source_locator: str,
    source_title: str,
    duration_seconds: int | None,
    max_duration_seconds: int,
    request_context_saver: RequestContextSaver | None = None,
) -> MediaAdmission | AdmissionRejection:
    if duration_seconds is None or duration_seconds <= 0:
        return AdmissionRejection(AdmissionRejectionCode.INVALID_MEDIA_DURATION)
    if duration_seconds > max_duration_seconds:
        return AdmissionRejection(AdmissionRejectionCode.MEDIA_TOO_LONG)

    job = prepared.job
    job.source_title = source_title
    job.source_duration_seconds = duration_seconds
    try:
        repository.save(job)
        context = JobRequestContext(
            job_id=job.job_id,
            delivery_chat_id=delivery_chat_id,
            source_locator=source_locator,
        )
        if request_context_saver is not None:
            request_context_saver(context)
        else:
            repository.save_request_context(context)
    except Exception:
        with suppress(Exception):
            repository.delete(job.job_id)
        raise
    return MediaAdmission(job=job)
