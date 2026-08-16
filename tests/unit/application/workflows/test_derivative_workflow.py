from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.derived_artifacts import GeneratedDerivativeFile
from yt_transcriber_bot.application.services.rename_speakers import RenameResult
from yt_transcriber_bot.application.workflows.derivatives import TranscriptDerivativeWorkflow
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class Repo:
    def __init__(self, job: Job) -> None:
        self.job = job
        self.saved = 0

    def get_by_id(self, job_id: str) -> Job | None:
        return self.job if job_id == self.job.job_id else None

    def save(self, job: Job) -> None:
        assert job is self.job
        self.saved += 1


class History:
    def __init__(self, job: Job) -> None:
        self.job = job

    def select(self, user_id: int, *, index: int) -> Job | None:
        return self.job if user_id == 7 and index == 1 else None


class Rename:
    def list_speakers(self, reference: str) -> tuple[str, ...]:
        assert reference == "canonical"
        return ("SPEAKER_00",)

    def rename(self, reference: str, aliases: dict[str, str], md_path: Path) -> RenameResult:
        assert reference == "canonical"
        assert aliases == {"SPEAKER_00": "Pessoa"}
        return RenameResult(md_path, 1)


class Gateway:
    def export_text(self, **kwargs: object) -> GeneratedDerivativeFile:
        assert kwargs["canonical_transcript_ref"] == "canonical"
        return GeneratedDerivativeFile(Path("derived.txt"), "txt")

    def export_transcript(self, **kwargs: object) -> GeneratedDerivativeFile:
        return GeneratedDerivativeFile(Path("derived.srt"), str(kwargs["format"]))

    def export_video(self, **kwargs: object) -> GeneratedDerivativeFile:
        return GeneratedDerivativeFile(Path("derived.mp4"), "mp4", 123)


class Indexer:
    def __init__(self) -> None:
        self.calls: list[Job] = []

    def refresh(self, job: Job) -> None:
        self.calls.append(job)


def _completed() -> Job:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.COMPLETED,
    ):
        job.transition_to(status)
    job.canonical_transcript_ref = "canonical"
    job.md_path = "/tmp/canonical.md"
    return job


def test_derivative_workflow_associates_export_with_canonical_job() -> None:
    job = _completed()
    workflow = TranscriptDerivativeWorkflow(
        repository=Repo(job),  # type: ignore[arg-type]
        history=History(job),  # type: ignore[arg-type]
        rename_service=Rename(),  # type: ignore[arg-type]
        gateway=Gateway(),  # type: ignore[arg-type]
        indexer=Indexer(),  # type: ignore[arg-type]
        transcripts_dir=Path("transcripts"),
    )
    result = workflow.export_text(user_id=7, index=1)
    assert result.association.job_id == job.job_id
    assert result.association.canonical_transcript_ref == "canonical"
    assert result.association.artifact_class is ArtifactClass.DERIVED_EXPORT


def test_rename_persists_aliases_and_explicitly_refreshes_search_index() -> None:
    job = _completed()
    repo = Repo(job)
    indexer = Indexer()
    workflow = TranscriptDerivativeWorkflow(
        repository=repo,  # type: ignore[arg-type]
        history=History(job),  # type: ignore[arg-type]
        rename_service=Rename(),  # type: ignore[arg-type]
        gateway=Gateway(),  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
        transcripts_dir=Path("transcripts"),
    )
    workflow.rename(job_id=job.job_id, aliases={"SPEAKER_00": "Pessoa"})
    assert job.speaker_renames == {"SPEAKER_00": "Pessoa"}
    assert repo.saved == 1
    assert indexer.calls == [job]
