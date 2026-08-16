# Pure model identity. Provider syntax, filesystem discovery, model-size
# policy and hardware-fit decisions belong outside the domain layer.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelName:
    name: str

    def __post_init__(self) -> None:
        cleaned = self.name.strip()
        object.__setattr__(self, "name", cleaned)
        if not cleaned or any(ch.isspace() for ch in cleaned):
            raise ValueError("Modelo inválido: use um identificador não vazio sem espaços.")

    def __str__(self) -> str:
        return self.name
