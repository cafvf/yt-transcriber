"""Fila sequencial application-owned para execução portátil de jobs."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from yt_transcriber_bot.application.cancellation import (
    CancellationToken,
    new_cancellation_token,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class QueuedItem(Generic[T]):
    """Item enfileirado com um único token cooperativo de cancelamento."""

    payload: T
    item_id: str
    enqueued_position: int = 0
    cancel_event: CancellationToken = field(default_factory=new_cancellation_token)

    def is_canceled(self) -> bool:
        return self.cancel_event.is_set()


class SequentialJobQueue(Generic[T]):
    """Fila assíncrona com um único consumidor.

    A fila é application-owned e não conhece Telegram, Bot API, persistência
    concreta nem tipos de payload de transporte.
    """

    def __init__(self, worker: Callable[[QueuedItem[T]], Awaitable[None]]) -> None:
        self._worker = worker
        self._queue: asyncio.Queue[QueuedItem[T]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._current: QueuedItem[T] | None = None
        self._pending: list[QueuedItem[T]] = []
        self._lock = asyncio.Lock()

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

    async def enqueue(self, payload: T, item_id: str) -> QueuedItem[T]:
        async with self._lock:
            position = (1 if self._current is not None else 0) + len(self._pending) + 1
            item = QueuedItem(payload=payload, item_id=item_id, enqueued_position=position)
            self._pending.append(item)
        await self._queue.put(item)
        return item

    async def cancel_current(self) -> bool:
        async with self._lock:
            current = self._current
        if current is None:
            return False
        current.cancel_event.set()
        return True

    async def clear_pending(self) -> int:
        async with self._lock:
            pending = list(self._pending)
            self._pending.clear()
        for item in pending:
            item.cancel_event.set()
        return len(pending)

    async def cancel_all(self) -> tuple[bool, int]:
        current_cancelled = await self.cancel_current()
        pending_cancelled = await self.clear_pending()
        return current_cancelled, pending_cancelled

    async def cancel_by_id(self, item_id: str) -> bool:
        async with self._lock:
            if self._current is not None and self._current.item_id == item_id:
                self._current.cancel_event.set()
                return True
            for item in self._pending:
                if item.item_id == item_id:
                    item.cancel_event.set()
                    return True
        return False

    def snapshot(self) -> tuple[QueuedItem[T] | None, tuple[QueuedItem[T], ...]]:
        return self._current, tuple(self._pending)

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            try:
                async with self._lock:
                    with contextlib.suppress(ValueError):
                        self._pending.remove(item)
                    if item.is_canceled():
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
