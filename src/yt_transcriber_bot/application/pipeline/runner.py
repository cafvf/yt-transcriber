"""Pipeline (Chain of Responsibility) com cancelamento e progresso."""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.operational_errors import classify_operational_error
from yt_transcriber_bot.application.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class PipelineCanceledError(Exception):
    """Lançada quando o pipeline é cancelado externamente."""


class PipelineStep(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    def should_run(self, ctx: PipelineContext) -> bool:
        return True

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> None: ...


ProgressFn = Callable[[str, str], None]
AuditFn = Callable[[str, dict[str, object]], None]


class PipelineRunner:
    def __init__(
        self,
        steps: Sequence[PipelineStep],
        cancel_event: threading.Event | None = None,
    ) -> None:
        if not steps:
            raise ValueError("PipelineRunner requer ao menos um step")
        self._steps = tuple(steps)
        self._cancel_event = cancel_event or threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(
        self,
        ctx: PipelineContext,
        progress: ProgressFn | None = None,
        audit: AuditFn | None = None,
    ) -> PipelineContext:
        ctx.cancel_event = self._cancel_event
        for step in self._steps:
            self._check_canceled()
            if not step.should_run(ctx):
                ctx.add_diagnostic(f"step {step.name} skipped")
                if progress:
                    progress(step.name, "Etapa pulada (não aplicável).")
                _audit_step(audit, "step_skipped", ctx, step.name)
                continue
            if progress:
                progress(step.name, f"Iniciando {step.name}...")
            logger.info("step %s starting", step.name)
            started = time.perf_counter()
            _audit_step(audit, "step_started", ctx, step.name)
            try:
                step.execute(ctx)
            except OperationCanceledError as exc:
                error = classify_operational_error(exc)
                _audit_step(
                    audit,
                    "step_failed",
                    ctx,
                    step.name,
                    duration_ms=_elapsed_ms(started),
                    error_code=error.code.value,
                    error_category=error.category.value,
                    error_retryable=error.retryable,
                    safe_message=error.safe_message,
                )
                raise PipelineCanceledError(error.safe_message) from exc
            except Exception as exc:
                error = classify_operational_error(exc)
                _audit_step(
                    audit,
                    "step_failed",
                    ctx,
                    step.name,
                    duration_ms=_elapsed_ms(started),
                    error_code=error.code.value,
                    error_category=error.category.value,
                    error_retryable=error.retryable,
                    safe_message=error.safe_message,
                )
                raise
            logger.info("step %s done", step.name)
            _audit_step(
                audit,
                "step_completed",
                ctx,
                step.name,
                duration_ms=_elapsed_ms(started),
            )
            if progress:
                progress(step.name, f"{step.name} concluida.")
        return ctx

    def _check_canceled(self) -> None:
        if self._cancel_event.is_set():
            raise PipelineCanceledError("Operação cancelada pelo usuário.")


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def _audit_step(
    audit: AuditFn | None,
    event: str,
    ctx: PipelineContext,
    step_name: str,
    **extra: object,
) -> None:
    if audit is None:
        return
    payload: dict[str, object] = {
        "job_id": ctx.job.job_id,
        "video_id": ctx.job.video_id.value if ctx.job.video_id is not None else None,
        "step_name": step_name,
        "job_status": ctx.job.status.value,
    }
    payload.update(extra)
    audit(event, payload)
