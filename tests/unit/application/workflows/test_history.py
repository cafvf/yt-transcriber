"""Tests for application-owned completed-history behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.workflows.history import (
    CompletedHistoryWorkflow,
    MarkdownRetrievalState,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class FakeRepo:
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs = jobs

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        return [job for job in reversed(self.jobs) if job.requested_by_user_id == user_id][:limit]


def _completed_job(
    *,
    user_id: int,
    updated_at: datetime,
    video_id: str,
    md_path: str | None = None,
) -> Job:
    job = Job.new(VideoId(video_id), user_id)
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
    job.updated_at = updated_at
    job.md_path = md_path
    return job


def test_list_completed_is_user_scoped_completed_only_and_newest_first() -> None:
    old = _completed_job(
        user_id=42,
        updated_at=datetime(2026, 5, 1, 10, tzinfo=UTC),
        video_id="aaaaaaaaaaa",
    )
    newest = _completed_job(
        user_id=42,
        updated_at=datetime(2026, 5, 1, 12, tzinfo=UTC),
        video_id="bbbbbbbbbbb",
    )
    other_user = _completed_job(
        user_id=7,
        updated_at=datetime(2026, 5, 1, 13, tzinfo=UTC),
        video_id="ccccccccccc",
    )
    pending = Job.new(VideoId("ddddddddddd"), 42)
    pending.updated_at = datetime(2026, 5, 1, 14, tzinfo=UTC)

    workflow = CompletedHistoryWorkflow(
        FakeRepo([old, newest, other_user, pending])  # type: ignore[arg-type]
    )

    assert workflow.list_completed(42, limit=10) == [newest, old]


def test_list_completed_applies_limit_after_filtering_and_sorting() -> None:
    jobs = [
        _completed_job(
            user_id=42,
            updated_at=datetime(2026, 5, 1, hour, tzinfo=UTC),
            video_id=f"{hour:011d}",
        )
        for hour in (8, 9, 10)
    ]
    workflow = CompletedHistoryWorkflow(FakeRepo(jobs))  # type: ignore[arg-type]

    assert workflow.list_completed(42, limit=2) == [jobs[2], jobs[1]]


def test_select_from_completed_uses_one_based_position() -> None:
    old = _completed_job(
        user_id=42,
        updated_at=datetime(2026, 5, 1, 10, tzinfo=UTC),
        video_id="aaaaaaaaaaa",
    )
    newest = _completed_job(
        user_id=42,
        updated_at=datetime(2026, 5, 1, 11, tzinfo=UTC),
        video_id="bbbbbbbbbbb",
    )
    workflow = CompletedHistoryWorkflow(FakeRepo([old, newest]))  # type: ignore[arg-type]
    jobs = workflow.list_completed(42, limit=10)

    assert workflow.select_from_completed(jobs, index=1) is newest
    assert workflow.select_from_completed(jobs, index=2) is old
    assert workflow.select_from_completed(jobs, index=0) is None
    assert workflow.select_from_completed(jobs, index=3) is None


def test_resolve_markdown_uses_injected_availability_probe(tmp_path: Path) -> None:
    md = tmp_path / "transcript.md"
    job = _completed_job(
        user_id=42,
        updated_at=datetime(2026, 5, 1, 10, tzinfo=UTC),
        video_id="aaaaaaaaaaa",
        md_path=str(md),
    )
    seen: list[Path] = []

    def available(path: Path) -> bool:
        seen.append(path)
        return True

    workflow = CompletedHistoryWorkflow(
        FakeRepo([job]),  # type: ignore[arg-type]
        markdown_available=available,
    )

    selected = workflow.resolve_markdown(job)

    assert selected.markdown_path == md
    assert selected.markdown_state is MarkdownRetrievalState.AVAILABLE
    assert seen == [md]


def test_resolve_markdown_distinguishes_missing_reference_and_file(
    tmp_path: Path,
) -> None:
    no_reference = _completed_job(
        user_id=42,
        updated_at=datetime(2026, 5, 1, 10, tzinfo=UTC),
        video_id="aaaaaaaaaaa",
    )
    missing_file = _completed_job(
        user_id=42,
        updated_at=datetime(2026, 5, 1, 11, tzinfo=UTC),
        video_id="bbbbbbbbbbb",
        md_path=str(tmp_path / "gone.md"),
    )
    workflow = CompletedHistoryWorkflow(
        FakeRepo([no_reference, missing_file]),  # type: ignore[arg-type]
        markdown_available=lambda _path: False,
    )

    assert (
        workflow.resolve_markdown(missing_file).markdown_state
        is MarkdownRetrievalState.MISSING_FILE
    )
    assert (
        workflow.resolve_markdown(no_reference).markdown_state
        is MarkdownRetrievalState.MISSING_REFERENCE
    )
