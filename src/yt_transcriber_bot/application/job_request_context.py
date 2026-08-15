"""Contexto de aquisição/entrega fora do agregado de domínio ``Job``."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JobRequestContext:
    job_id: str
    delivery_chat_id: int | None = None
    source_locator: str | None = None
