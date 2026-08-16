from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.derived_artifacts import (
    StoredSummaryArtifact,
)
from yt_transcriber_bot.application.services.transcript_summary import SummaryResult
from yt_transcriber_bot.application.workflows.summary import SummaryWorkflow
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class History:
    def __init__(self, job: Job) -> None:
        self.job = job

    def select(self, user_id: int, *, index: int) -> Job | None:
        return self.job if user_id == 7 and index == 1 else None


class Policy:
    def summarize(self, **kwargs: object) -> SummaryResult:
        assert kwargs["slug"] == "canonical"
        return SummaryResult("# resumo", 2, "model")


class Store:
    def __init__(self) -> None:
        self.saved = None

    def save(self, association: object, content: str) -> StoredSummaryArtifact:
        self.saved = (association, content)
        return StoredSummaryArtifact(association, Path("summary.md"), content)  # type: ignore[arg-type]


class Indexer:
    def __init__(self) -> None:
        self.calls: list[Job] = []

    def refresh(self, job: Job) -> None:
        self.calls.append(job)


def _job() -> Job:
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
    return job


def test_summary_workflow_persists_associated_summary_then_refreshes_index() -> None:
    job = _job()
    store = Store()
    indexer = Indexer()
    workflow = SummaryWorkflow(
        history=History(job),  # type: ignore[arg-type]
        summary_policy=Policy(),  # type: ignore[arg-type]
        store=store,  # type: ignore[arg-type]
        indexer=indexer,  # type: ignore[arg-type]
    )
    result = workflow.summarize(user_id=7, index=1)
    assert result.association.job_id == job.job_id
    assert result.association.canonical_transcript_ref == "canonical"
    assert result.association.artifact_class is ArtifactClass.DERIVED_SUMMARY
    assert result.path == Path("summary.md")
    assert store.saved is not None
    assert indexer.calls == [job]
