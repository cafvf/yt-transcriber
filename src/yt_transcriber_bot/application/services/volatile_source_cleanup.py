from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.ports.artifact_cleanup import (
    ArtifactCleanupRefusedError,
    OwnedArtifactCleanup,
)
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType


@dataclass(frozen=True, slots=True)
class SourceCleanupResult:
    source_reference_cleared: bool
    file_removed: bool


class VolatileSourceCleanupService:
    """Clean private staged source media without exposing filesystem mechanics upward."""

    def __init__(self, repository: JobRepository, cleanup: OwnedArtifactCleanup) -> None:
        self._repository = repository
        self._cleanup = cleanup

    def cleanup(self, job: Job) -> SourceCleanupResult:
        if (
            job.media_source is None
            or job.media_source.source_type is not MediaSourceType.TELEGRAM_AUDIO
        ):
            return SourceCleanupResult(False, False)
        context = self._repository.get_request_context(job.job_id)
        if context is None or not context.source_locator:
            return SourceCleanupResult(False, False)

        path = Path(context.source_locator)
        removed = False
        try:
            removed = self._cleanup.remove_file(path)
            self._cleanup.remove_empty_directory(path.parent)
        except (ArtifactCleanupRefusedError, OSError):
            # Cleanup is best effort; durable context must stop advertising a private
            # staging locator even if the host mechanism cannot remove it now.
            pass
        self._repository.save_request_context(
            JobRequestContext(
                job_id=context.job_id,
                delivery_chat_id=context.delivery_chat_id,
                source_locator=None,
            )
        )
        return SourceCleanupResult(True, removed)
