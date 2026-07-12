"""Fila sequencial em memória de jobs (Dúvida 9: um vídeo por vez).

Implementa o producer-consumer com asyncio.Queue. Como há um único usuário
autorizado, garantimos processamento serializado simples — próximas
solicitações ficam aguardando até a anterior terminar. O bot notifica a
posição na fila ao adicionar e suporta cancelamento da tarefa em andamento.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class QueuedItem(Generic[T]):
    """Item enfileirado: payload + handle para feedback ao usuário."""

    payload: T
    item_id: str
    enqueued_position: int = 0
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    def is_canceled(self) -> bool:
        return self.cancel_event.is_set()


class SequentialJobQueue(Generic[T]):
    """Fila assíncrona com **um** consumidor (worker único)."""

    def __init__(self, worker: Callable[[QueuedItem[T]], Awaitable[None]]) -> None:
        self._worker = worker
        self._queue: asyncio.Queue[QueuedItem[T]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._current: QueuedItem[T] | None = None
        self._pending: list[QueuedItem[T]] = []  # cópia do que está aguardando
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def enqueue(self, payload: T, item_id: str) -> QueuedItem[T]:
        """Adiciona ``payload`` à fila e devolve o item criado.

        ``enqueued_position`` indica a posição (1 = está sendo processado já,
        2 = um na frente, etc.). É calculado no momento do enqueue.
        """
        async with self._lock:
            position = (1 if self._current is not None else 0) + len(self._pending) + 1
            item = QueuedItem(payload=payload, item_id=item_id, enqueued_position=position)
            self._pending.append(item)
        await self._queue.put(item)
        return item

    async def cancel_current(self) -> bool:
        """Cancela o job em execução (se houver). Retorna True se algo foi cancelado."""
        async with self._lock:
            current = self._current
        if current is None:
            return False
        current.cancel_event.set()
        return True

    async def clear_pending(self) -> int:
        """Cancela e remove a visão local dos itens pendentes.

        Os itens ainda podem estar dentro do ``asyncio.Queue`` interno, mas
        ficam marcados como cancelados e serão descartados pelo worker ao serem
        retirados. Retorna a quantidade de itens pendentes sinalizados.
        """
        async with self._lock:
            pending = list(self._pending)
            self._pending.clear()
        for item in pending:
            item.cancel_event.set()
        return len(pending)

    async def cancel_all(self) -> tuple[bool, int]:
        """Cancela o job atual e todos os pendentes.

        Retorna ``(havia_atual, quantidade_pendentes_cancelados)``.
        """
        current_cancelled = await self.cancel_current()
        pending_cancelled = await self.clear_pending()
        return current_cancelled, pending_cancelled

    async def cancel_by_id(self, item_id: str) -> bool:
        """Cancela um job pendente OU o atual pelo ``item_id``.

        Se o item já estiver em execução, sinaliza cancelamento via evento.
        Se ainda estiver pendente, marca para ser descartado quando chegar
        ao worker.
        """
        async with self._lock:
            if self._current is not None and self._current.item_id == item_id:
                self._current.cancel_event.set()
                return True
            for it in self._pending:
                if it.item_id == item_id:
                    it.cancel_event.set()
                    return True
        return False

    def snapshot(self) -> tuple[QueuedItem[T] | None, tuple[QueuedItem[T], ...]]:
        """Retorna (item_em_execucao, tupla_pendentes) sem bloqueio.

        Para uso em comandos como ``/status`` — não exige lock pois é
        leitura de referência.
        """
        return self._current, tuple(self._pending)

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                async with self._lock:
                    # Tira da lista de pendentes (se ainda estiver lá).
                    with contextlib.suppress(ValueError):
                        self._pending.remove(item)
                    if item.is_canceled():
                        # Cancelado antes mesmo de começar.
                        continue
                    self._current = item
                await self._worker(item)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Worker falhou processando item %s", item.item_id)
            finally:
                async with self._lock:
                    self._current = None
                self._queue.task_done()
