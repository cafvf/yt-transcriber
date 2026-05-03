"""Testes da fila sequencial."""

from __future__ import annotations

import asyncio

import pytest

from yt_transcriber_bot.infrastructure.telegram.job_queue import (
    QueuedItem,
    SequentialJobQueue,
)


class TestSequential:
    @pytest.mark.asyncio
    async def test_processes_in_order(self) -> None:
        processed: list[str] = []

        async def worker(item: QueuedItem[str]) -> None:
            processed.append(item.payload)

        q: SequentialJobQueue[str] = SequentialJobQueue(worker)
        await q.start()
        try:
            await q.enqueue("a", "id-a")
            await q.enqueue("b", "id-b")
            await q.enqueue("c", "id-c")
            # Espera a fila esvaziar.
            await asyncio.sleep(0.05)
            assert processed == ["a", "b", "c"]
        finally:
            await q.stop()

    @pytest.mark.asyncio
    async def test_position_reflects_queue(self) -> None:
        gate = asyncio.Event()

        async def worker(item: QueuedItem[str]) -> None:
            await gate.wait()

        q: SequentialJobQueue[str] = SequentialJobQueue(worker)
        await q.start()
        try:
            i1 = await q.enqueue("a", "id-a")
            await asyncio.sleep(0.01)
            i2 = await q.enqueue("b", "id-b")
            i3 = await q.enqueue("c", "id-c")
            assert i1.enqueued_position == 1
            assert i2.enqueued_position == 2
            assert i3.enqueued_position == 3
        finally:
            gate.set()
            await q.stop()

    @pytest.mark.asyncio
    async def test_cancel_current(self) -> None:
        canceled_signal_received: list[bool] = []

        async def worker(item: QueuedItem[str]) -> None:
            for _ in range(50):
                if item.is_canceled():
                    canceled_signal_received.append(True)
                    return
                await asyncio.sleep(0.01)

        q: SequentialJobQueue[str] = SequentialJobQueue(worker)
        await q.start()
        try:
            await q.enqueue("a", "id-a")
            await asyncio.sleep(0.02)  # garante que worker começou
            assert await q.cancel_current() is True
            await asyncio.sleep(0.05)
            assert canceled_signal_received == [True]
        finally:
            await q.stop()

    @pytest.mark.asyncio
    async def test_cancel_pending_skips_execution(self) -> None:
        processed: list[str] = []
        gate = asyncio.Event()

        async def worker(item: QueuedItem[str]) -> None:
            if not gate.is_set():
                await gate.wait()
            processed.append(item.payload)

        q: SequentialJobQueue[str] = SequentialJobQueue(worker)
        await q.start()
        try:
            await q.enqueue("a", "id-a")
            await q.enqueue("b", "id-b")
            await q.enqueue("c", "id-c")
            # Cancela o "b" antes de "a" terminar.
            assert await q.cancel_by_id("id-b") is True
            gate.set()
            await asyncio.sleep(0.05)
            assert processed == ["a", "c"]
        finally:
            await q.stop()

    @pytest.mark.asyncio
    async def test_cancel_unknown_id_returns_false(self) -> None:
        async def worker(item: QueuedItem[str]) -> None:
            return

        q: SequentialJobQueue[str] = SequentialJobQueue(worker)
        await q.start()
        try:
            assert await q.cancel_by_id("nope") is False
        finally:
            await q.stop()

    @pytest.mark.asyncio
    async def test_worker_exception_does_not_kill_queue(self) -> None:
        processed: list[str] = []

        async def worker(item: QueuedItem[str]) -> None:
            if item.payload == "boom":
                raise RuntimeError("kaboom")
            processed.append(item.payload)

        q: SequentialJobQueue[str] = SequentialJobQueue(worker)
        await q.start()
        try:
            await q.enqueue("a", "id-a")
            await q.enqueue("boom", "id-boom")
            await q.enqueue("c", "id-c")
            await asyncio.sleep(0.05)
            assert processed == ["a", "c"]
        finally:
            await q.stop()

    @pytest.mark.asyncio
    async def test_snapshot(self) -> None:
        gate = asyncio.Event()

        async def worker(item: QueuedItem[str]) -> None:
            await gate.wait()

        q: SequentialJobQueue[str] = SequentialJobQueue(worker)
        await q.start()
        try:
            await q.enqueue("a", "id-a")
            await asyncio.sleep(0.01)
            await q.enqueue("b", "id-b")
            current, pending = q.snapshot()
            assert current is not None
            assert current.payload == "a"
            # Quando "a" entrou em execução, foi removido de _pending; só "b" restou
            assert tuple(p.payload for p in pending) == ("b",)
        finally:
            gate.set()
            await q.stop()
