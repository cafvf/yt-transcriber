"""Pipeline (Chain of Responsibility) com cancelamento e progresso.

Cada ``PipelineStep`` recebe o ``PipelineContext`` e pode mutá-lo; pode
também sinalizar que NÃO é aplicável (devolvendo ``False`` em ``should_run``)
para ser pulado, ou pode lançar exceções que abortam o pipeline.
"""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

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
    ) -> PipelineContext:
        for step in self._steps:
            self._check_canceled()
            if not step.should_run(ctx):
                ctx.add_diagnostic(f"step {step.name} skipped")
                if progress:
                    progress(step.name, "Etapa pulada (não aplicável).")
                continue
            if progress:
                progress(step.name, f"Iniciando {step.name}...")
            logger.info("step %s starting", step.name)
            step.execute(ctx)
            logger.info("step %s done", step.name)
            if progress:
                progress(step.name, f"{step.name} concluida.")
        return ctx

    def _check_canceled(self) -> None:
        if self._cancel_event.is_set():
            raise PipelineCanceledError("Pipeline cancelado pelo usuario")
