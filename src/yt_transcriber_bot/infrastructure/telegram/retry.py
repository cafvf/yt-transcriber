"""Retry com backoff exponencial para operações de rede do Telegram.

Decisão Dúvida 11 (correção): falha de envio para Telegram → retentar 5x
com backoff exponencial; após esgotar, registrar log e abandonar.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_INITIAL_DELAY = 1.0  # segundos
DEFAULT_BACKOFF_FACTOR = 2.0


class TelegramSendError(RuntimeError):
    """Falha de envio após esgotar todas as retentativas."""


async def send_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    initial_delay_s: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Executa ``operation`` retentando em caso de exceção.

    Levanta ``TelegramSendError`` quando todas as tentativas falharem,
    encadeando a última exceção como ``__cause__``.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts deve ser >= 1")
    delay = initial_delay_s
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            last_exc = exc
            if attempt == max_attempts:
                logger.error("Telegram send falhou após %d tentativas: %s", max_attempts, exc)
                raise TelegramSendError(f"Falha após {max_attempts} tentativas: {exc}") from exc
            logger.warning(
                "Telegram send falhou (tentativa %d/%d): %s. Aguardando %.2fs",
                attempt,
                max_attempts,
                exc,
                delay,
            )
            await sleeper(delay)
            delay *= backoff_factor
    # Inalcançável (raise dentro do loop), mas ajuda o type checker:
    raise TelegramSendError(str(last_exc))
