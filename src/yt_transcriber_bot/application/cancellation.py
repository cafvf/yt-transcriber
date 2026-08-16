from __future__ import annotations

import threading
import time

CancellationToken = threading.Event


def new_cancellation_token() -> CancellationToken:
    """Cria o token cooperativo único usado pela fila e pelo pipeline."""
    return threading.Event()


class OperationCanceledError(Exception):
    """Operação abortada por cancelamento externo."""


def raise_if_cancelled(cancel_event: CancellationToken | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise OperationCanceledError("Operação cancelada pelo usuário")


def sleep_with_cancel(
    delay_s: float,
    *,
    cancel_event: CancellationToken | None,
    poll_interval_s: float = 0.05,
) -> None:
    if delay_s <= 0:
        raise_if_cancelled(cancel_event)
        return
    deadline = time.monotonic() + delay_s
    while True:
        raise_if_cancelled(cancel_event)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(poll_interval_s, remaining))
