"""Testes do retry com backoff exponencial."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.infrastructure.telegram.retry import (
    TelegramSendError,
    send_with_retry,
)


class FakeSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@pytest.mark.asyncio
async def test_returns_on_first_success() -> None:
    sleeper = FakeSleeper()
    calls = 0

    async def op() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await send_with_retry(op, sleeper=sleeper)
    assert result == "ok"
    assert calls == 1
    assert sleeper.delays == []


@pytest.mark.asyncio
async def test_retries_on_failure_then_succeeds() -> None:
    sleeper = FakeSleeper()
    counter = {"n": 0}

    async def op() -> str:
        counter["n"] += 1
        if counter["n"] < 3:
            raise RuntimeError("net error")
        return "ok"

    result = await send_with_retry(
        op, max_attempts=5, initial_delay_s=1.0, backoff_factor=2.0, sleeper=sleeper
    )
    assert result == "ok"
    assert counter["n"] == 3
    assert sleeper.delays == [1.0, 2.0]  # 2 falhas, delays exponenciais


@pytest.mark.asyncio
async def test_raises_after_max_attempts() -> None:
    sleeper = FakeSleeper()

    async def op() -> str:
        raise RuntimeError("permanent")

    with pytest.raises(TelegramSendError, match="5 tentativas"):
        await send_with_retry(
            op, max_attempts=5, initial_delay_s=1.0, backoff_factor=2.0, sleeper=sleeper
        )
    # 5 tentativas → 4 esperas (não dorme após a última)
    assert sleeper.delays == [1.0, 2.0, 4.0, 8.0]


@pytest.mark.asyncio
async def test_invalid_max_attempts() -> None:
    async def op() -> str:
        return "ok"

    with pytest.raises(ValueError, match="max_attempts"):
        await send_with_retry(op, max_attempts=0)


@pytest.mark.asyncio
async def test_chain_exception_as_cause() -> None:
    sleeper = FakeSleeper()
    original = RuntimeError("net dead")

    async def op() -> str:
        raise original

    with pytest.raises(TelegramSendError) as exc_info:
        await send_with_retry(op, max_attempts=2, sleeper=sleeper)
    assert exc_info.value.__cause__ is original
