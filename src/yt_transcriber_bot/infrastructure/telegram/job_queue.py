"""Compatibilidade temporária: a implementação da fila pertence a Application."""

from yt_transcriber_bot.application.workflows.execution_queue import (
    QueuedItem,
    SequentialJobQueue,
)

__all__ = ["QueuedItem", "SequentialJobQueue"]
