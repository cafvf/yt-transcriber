"""Porta ``GpuDetector`` — abstrai a detecção de hardware compatível."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareProfile:
    """Descrição da capacidade computacional disponível."""

    has_cuda: bool
    cuda_compute_capability: tuple[int, int] | None  # (major, minor) ou None
    vram_total_gb: float
    gpu_name: str

    def is_cuda_compatible(self, *, min_compute_capability: tuple[int, int] = (6, 0)) -> bool:
        if not self.has_cuda or self.cuda_compute_capability is None:
            return False
        return self.cuda_compute_capability >= min_compute_capability

    def can_fit_model(self, required_vram_gb: float) -> bool:
        return self.vram_total_gb >= required_vram_gb


class GpuDetector(ABC):
    """Detecta a capacidade de hardware na inicialização."""

    @abstractmethod
    def detect(self) -> HardwareProfile: ...
