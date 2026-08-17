from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.job_request_context import JobRequestContext
from yt_transcriber_bot.application.services.volatile_source_cleanup import (
    VolatileSourceCleanupService,
)
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.media_source import MediaSource


class Repo:
    def __init__(self, context: JobRequestContext) -> None:
        self.context = context

    def get_request_context(self, _job_id: str) -> JobRequestContext | None:
        return self.context

    def save_request_context(self, context: JobRequestContext) -> None:
        self.context = context


class Cleanup:
    def __init__(self) -> None:
        self.files: list[Path] = []
        self.dirs: list[Path] = []

    def remove_file(self, path: Path) -> bool:
        self.files.append(path)
        return True

    def remove_empty_directory(self, path: Path) -> bool:
        self.dirs.append(path)
        return True


def test_private_telegram_source_cleanup_uses_owned_capability_and_clears_locator() -> None:
    job = Job.new(
        None,
        7,
        media_source=MediaSource.telegram_audio("private-id"),
        source_title="Áudio",
        source_duration_seconds=10,
    )
    context = JobRequestContext(job.job_id, 55, "/owned/staging/file.ogg")
    repo = Repo(context)
    cleanup = Cleanup()

    result = VolatileSourceCleanupService(repo, cleanup).cleanup(job)  # type: ignore[arg-type]

    assert result.file_removed is True
    assert cleanup.files == [Path("/owned/staging/file.ogg")]
    assert cleanup.dirs == [Path("/owned/staging")]
    assert repo.context.source_locator is None
    assert repo.context.delivery_chat_id == 55
