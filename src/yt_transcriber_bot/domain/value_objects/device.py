"""Value object ``Device`` — alvo de inferência (``cpu`` ou ``cuda``)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeviceKind(StrEnum):
    AUTO = "auto"
    CPU = "cpu"
    CUDA = "cuda"


@dataclass(frozen=True, slots=True)
class Device:
    kind: DeviceKind

    @classmethod
    def auto(cls) -> Device:
        return cls(kind=DeviceKind.AUTO)

    @classmethod
    def cpu(cls) -> Device:
        return cls(kind=DeviceKind.CPU)

    @classmethod
    def cuda(cls) -> Device:
        return cls(kind=DeviceKind.CUDA)

    @classmethod
    def from_string(cls, raw: str) -> Device:
        try:
            return cls(kind=DeviceKind(raw))
        except ValueError as exc:
            raise ValueError(f"Device inválido: '{raw}' (use auto, cpu ou cuda)") from exc

    def is_auto(self) -> bool:
        return self.kind is DeviceKind.AUTO

    def is_cpu(self) -> bool:
        return self.kind is DeviceKind.CPU

    def is_cuda(self) -> bool:
        return self.kind is DeviceKind.CUDA

    def __str__(self) -> str:
        return self.kind.value
