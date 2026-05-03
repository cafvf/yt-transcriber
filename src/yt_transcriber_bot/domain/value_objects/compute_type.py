"""Value object ``ComputeType`` — precisão numérica usada pelo CTranslate2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ComputeKind(StrEnum):
    AUTO = "auto"
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    INT8_FLOAT16 = "int8_float16"
    INT8 = "int8"


@dataclass(frozen=True, slots=True)
class ComputeType:
    kind: ComputeKind

    @classmethod
    def from_string(cls, raw: str) -> ComputeType:
        try:
            return cls(kind=ComputeKind(raw))
        except ValueError as exc:
            raise ValueError(
                f"ComputeType inválido: '{raw}' (use auto, float32, float16, int8_float16 ou int8)"
            ) from exc

    @classmethod
    def auto(cls) -> ComputeType:
        return cls(kind=ComputeKind.AUTO)

    def __str__(self) -> str:
        return self.kind.value
