"""Testes do PipelineRunner (Chain of Responsibility)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

import pytest

from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.pipeline.runner import (
    PipelineCanceledError,
    PipelineRunner,
    PipelineStep,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


def _make_job() -> Job:
    return Job(
        job_id="j1",
        video_id=VideoId(value="dQw4w9WgXcQ"),
        status=JobStatus.PENDING,
        requested_by_user_id=42,
        requested_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class _CountingStep(PipelineStep):
    def __init__(
        self,
        name_: str,
        *,
        run: bool = True,
        raise_exc: Exception | None = None,
    ) -> None:
        self._name = name_
        self._should_run = run
        self._exc = raise_exc
        self.executed = 0

    @property
    def name(self) -> str:
        return self._name

    def should_run(self, ctx: PipelineContext) -> bool:
        return self._should_run

    def execute(self, ctx: PipelineContext) -> None:
        self.executed += 1
        if self._exc is not None:
            raise self._exc


class TestPipelineRunner:
    def test_empty_steps_raises(self) -> None:
        with pytest.raises(ValueError, match="ao menos um"):
            PipelineRunner(steps=())

    def test_runs_all_steps_in_order(self) -> None:
        s1, s2, s3 = (
            _CountingStep("a"),
            _CountingStep("b"),
            _CountingStep("c"),
        )
        runner = PipelineRunner(steps=(s1, s2, s3))
        ctx = PipelineContext(job=_make_job())
        runner.run(ctx)
        assert (s1.executed, s2.executed, s3.executed) == (1, 1, 1)

    def test_skips_steps_with_should_run_false(self) -> None:
        s1, s2, s3 = (
            _CountingStep("a"),
            _CountingStep("b", run=False),
            _CountingStep("c"),
        )
        runner = PipelineRunner(steps=(s1, s2, s3))
        ctx = PipelineContext(job=_make_job())
        runner.run(ctx)
        assert s1.executed == 1
        assert s2.executed == 0
        assert s3.executed == 1
        assert any("step b skipped" in d for d in ctx.diagnostics)

    def test_progress_callback_invoked_per_step(self) -> None:
        events: list[tuple[str, str]] = []
        runner = PipelineRunner(
            steps=(_CountingStep("a"), _CountingStep("b", run=False), _CountingStep("c"))
        )
        ctx = PipelineContext(job=_make_job())
        runner.run(ctx, progress=lambda step, msg: events.append((step, msg)))
        # 'a' deve gerar 'iniciando' e 'concluida'; 'b' apenas 'pulada'; 'c' iniciando + concluida
        assert any(e[0] == "a" and "Iniciando" in e[1] for e in events)
        assert any(e[0] == "b" and "pulada" in e[1] for e in events)
        assert any(e[0] == "c" and "concluida" in e[1].lower() for e in events)

    def test_exception_propagates_and_stops_chain(self) -> None:
        s1 = _CountingStep("a", raise_exc=ValueError("boom"))
        s2 = _CountingStep("b")
        runner = PipelineRunner(steps=(s1, s2))
        ctx = PipelineContext(job=_make_job())
        with pytest.raises(ValueError, match="boom"):
            runner.run(ctx)
        assert s2.executed == 0  # nao avancou

    def test_cancel_before_run_raises_immediately(self) -> None:
        s1 = _CountingStep("a")
        ev = threading.Event()
        runner = PipelineRunner(steps=(s1,), cancel_event=ev)
        ev.set()
        ctx = PipelineContext(job=_make_job())
        with pytest.raises(PipelineCanceledError):
            runner.run(ctx)
        assert s1.executed == 0

    def test_cancel_method_sets_event(self) -> None:
        runner = PipelineRunner(steps=(_CountingStep("a"),))
        runner.cancel()
        ctx = PipelineContext(job=_make_job())
        with pytest.raises(PipelineCanceledError):
            runner.run(ctx)

    def test_cancel_between_steps(self) -> None:
        ev = threading.Event()

        class CancellingStep(PipelineStep):
            @property
            def name(self) -> str:
                return "cancel"

            def execute(self, ctx: PipelineContext) -> None:
                ev.set()

        s1 = CancellingStep()
        s2 = _CountingStep("b")
        runner = PipelineRunner(steps=(s1, s2), cancel_event=ev)
        ctx = PipelineContext(job=_make_job())
        with pytest.raises(PipelineCanceledError):
            runner.run(ctx)
        assert s2.executed == 0
