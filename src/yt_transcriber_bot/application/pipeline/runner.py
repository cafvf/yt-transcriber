"""Pipeline (Chain of Responsibility) com cancelamento e progresso.

Cada ``PipelineStep`` recebe o ``PipelineContext`` e pode mutá-lo; pode
também sinalizar que NÃO é aplicável (devolvendo ``False`` em ``should_run``)
para ser pulado, ou pode lançar exceções que abortam o pipeline.
"""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)


class PipelineCanceledError(Exception):
    """Lançada quando o pipeline é cancelado externamente."""


class PipelineStep(ABC):
    """Etapa do pipeline."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    def should_run(self, ctx: PipelineContext) -> bool:
        """Default: sempre executa. Subclasses podem sobrescrever."""
        return True

    @abstractmethod
    def execute(self, ctx: PipelineContext) -> None: ...


ProgressFn = Callable[[str, str], None]
"""``(step_name, message)`` para feedback ao usuário."""

AuditFn = Callable[[str, dict[str, object]], None]
"""``(event_name, payload)`` para trilha local de auditoria estruturada."""


class PipelineRunner:
    """Executa os steps em ordem, gerencia cancelamento e progresso."""

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
                _audit_step(
                    audit,
                    "step_failed",
                    ctx,
                    step.name,
                    duration_ms=_elapsed_ms(started),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                raise PipelineCanceledError(str(exc)) from exc
            except Exception as exc:
                _audit_step(
                    audit,
                    "step_failed",
                    ctx,
                    step.name,
                    duration_ms=_elapsed_ms(started),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
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
            raise PipelineCanceledError("Pipeline cancelado pelo usuario")


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
