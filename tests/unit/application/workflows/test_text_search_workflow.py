from __future__ import annotations

from datetime import UTC, datetime

from yt_transcriber_bot.application.ports.text_search import HistorySearchHit, TextSearchQuery
from yt_transcriber_bot.application.workflows.text_search import TextSearchWorkflow
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class History:
    def __init__(self, job: Job) -> None:
        self._job = job

    def list_completed(self, user_id: int, *, limit: int) -> list[Job]:
        _ = (user_id, limit)
        return [self._job]


class Query(TextSearchQuery):
    def search_completed_for_user(
        self, *, user_id: int, query: str, limit: int
    ) -> list[HistorySearchHit]:
        _ = (user_id, query, limit)
        return [
            HistorySearchHit(
                job_id="job",
                title="Título",
                video_id="dQw4w9WgXcQ",
                source_label="YouTube",
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
                snippet="conteúdo",
            )
        ]


class Indexer:
    def __init__(self) -> None:
        self.calls: list[Job] = []

    def refresh(self, job: Job) -> None:
        self.calls.append(job)


def test_search_workflow_owns_rebuild_and_current_history_index() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    object.__setattr__(job, "job_id", "job")
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
    indexer = Indexer()
    workflow = TextSearchWorkflow(
        history=History(job),  # type: ignore[arg-type]
        query=Query(),
        indexer=indexer,  # type: ignore[arg-type]
    )
    results = workflow.search(user_id=7, query="  conteúdo  ")
    assert [result.history_index for result in results] == [1]
    assert indexer.calls == [job]
