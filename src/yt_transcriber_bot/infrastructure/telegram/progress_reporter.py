"""Reporter de progresso que edita uma única mensagem do Telegram.

Decisões consolidadas:
- Bot verboso (Dúvida 4) → 5 marcos fixos: 10/25/50/75/90% (Dúvida 21).
- Edição de mensagem (Dúvida 40) com debounce mínimo configurável
  (telegram_message_edit_min_interval_s) para não bater em rate-limit.
- Etapas de alto nível: METADADOS, ÁUDIO, CONVERSÃO, TRANSCRIÇÃO,
  DIARIZAÇÃO, RENDER. Mensagens em português (Dúvida 44).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Marcos fixos de progresso em fração [0, 1].
# Não representam percentual real de processamento: são marcos de etapa.
FIXED_MILESTONES = (0.10, 0.25, 0.50, 0.75, 0.90)
TRANSCRIPTION_MILESTONES = FIXED_MILESTONES  # compatibilidade interna

EDITOR_FN = Callable[[str], Awaitable[None]]


@dataclass
class ProgressState:
    """Estado interno do reporter."""

    title: str = "(sem título)"
    stage: str = "Iniciando…"
    transcription_percent: int = 0
    diagnostic: str = ""
    last_emitted_text: str = ""
    last_emitted_at: float = 0.0
    next_milestone_idx: int = 0
    terminal: bool = False
    diagnostics: list[str] = field(default_factory=list)


class ProgressReporter:
    """Reporta progresso editando uma mensagem do Telegram."""

    def __init__(
        self,
        editor: EDITOR_FN,
        *,
        clock: Callable[[], float] | None = None,
        min_interval_s: float = 2.0,
    ) -> None:
        self._editor = editor
        self._clock = clock or asyncio.get_event_loop().time
        self._min_interval_s = min_interval_s
        self._state = ProgressState()

    # ------------------------------------------------------------------
    # API pública usada pelos handlers/use case
    # ------------------------------------------------------------------

    async def set_title(self, title: str) -> None:
        if self._state.terminal:
            return
        self._state.title = title
        await self._render(force=True)

    async def stage(self, stage_text: str) -> None:
        if self._state.terminal:
            return
        self._state.stage = stage_text
        await self._render(force=True)

    async def fixed_progress(self, fraction: float) -> None:
        if self._state.terminal:
            return
        # Emite uma mensagem para CADA marco cruzado nesta chamada.
        while self._state.next_milestone_idx < len(FIXED_MILESTONES):
            next_target = FIXED_MILESTONES[self._state.next_milestone_idx]
            if fraction + 1e-9 < next_target:
                break
            self._state.transcription_percent = max(
                self._state.transcription_percent, round(next_target * 100)
            )
            self._state.next_milestone_idx += 1
            await self._render(force=True)

    async def transcription_progress(self, fraction: float) -> None:
        # Nome legado: agora serve para qualquer etapa longa.
        await self.fixed_progress(fraction)

    async def diagnostic(self, message: str) -> None:
        if self._state.terminal:
            return
        self._state.diagnostics.append(message)
        # Mantém só os 3 últimos diagnósticos no painel.
        self._state.diagnostics = self._state.diagnostics[-3:]
        await self._render(force=False)

    async def finish(self, summary: str) -> None:
        self._state.stage = summary
        self._state.transcription_percent = 100
        self._state.next_milestone_idx = len(FIXED_MILESTONES)
        self._state.terminal = True
        await self._render(force=True)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _build_text(self) -> str:
        lines = [f"*{_escape_markdown(self._state.title)}*", ""]
        if self._state.transcription_percent > 0:
            lines.append(f"{self._state.stage} {self._state.transcription_percent}%")
        else:
            lines.append(self._state.stage)
        if self._state.diagnostics:
            lines.append("")
            for d in self._state.diagnostics:
                lines.append(f"• {_escape_markdown(d)}")
        return "\n".join(lines)

    async def _render(self, *, force: bool) -> None:
        text = self._build_text()
        if text == self._state.last_emitted_text:
            return
        now = self._clock()
        if not force and (now - self._state.last_emitted_at) < self._min_interval_s:
            return
        try:
            await self._editor(text)
        except Exception as exc:
            logger.warning("Falha editando mensagem de progresso: %s", exc)
            return
        self._state.last_emitted_text = text
        self._state.last_emitted_at = now


def _escape_markdown(text: str) -> str:
    """Escape mínimo para MarkdownV2 (apenas asteriscos e underlines)."""
    return text.replace("*", "").replace("_", " ")
