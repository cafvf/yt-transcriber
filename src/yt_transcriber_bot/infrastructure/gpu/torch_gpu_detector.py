"""Implementação de ``GpuDetector`` baseada em PyTorch.

A introspecção do PyTorch é abstraída via uma interface ``TorchProbe``
para permitir testes determinísticos sem depender da presença real de CUDA.
"""

from __future__ import annotations

from typing import Protocol

from yt_transcriber_bot.application.ports.gpu_detector import (
    GpuDetector,
    HardwareProfile,
)


class TorchProbe(Protocol):
    def is_available(self) -> bool: ...

    def device_count(self) -> int: ...

    def device_name(self, index: int) -> str: ...

    def compute_capability(self, index: int) -> tuple[int, int]: ...

    def total_memory_bytes(self, index: int) -> int: ...


class RealTorchProbe:
    """Implementação real de ``TorchProbe`` usando ``torch.cuda``."""

    def is_available(self) -> bool:
        try:
            import torch
        except ImportError:
            return False
        return bool(torch.cuda.is_available())

    def device_count(self) -> int:
        import torch

        return int(torch.cuda.device_count())

    def device_name(self, index: int) -> str:
        import torch

        return str(torch.cuda.get_device_name(index))

    def compute_capability(self, index: int) -> tuple[int, int]:
        import torch

        major, minor = torch.cuda.get_device_capability(index)
        return int(major), int(minor)

    def total_memory_bytes(self, index: int) -> int:
        import torch

        props = torch.cuda.get_device_properties(index)
        return int(props.total_memory)


class TorchGpuDetector(GpuDetector):
    """Detecta a melhor GPU disponível e devolve um ``HardwareProfile``."""

    def __init__(self, probe: TorchProbe | None = None) -> None:
        self._probe: TorchProbe = probe or RealTorchProbe()

    def detect(self) -> HardwareProfile:
        if not self._probe.is_available() or self._probe.device_count() <= 0:
            return HardwareProfile(
                has_cuda=False,
                cuda_compute_capability=None,
                vram_total_gb=0.0,
                gpu_name="",
            )

        # Escolhemos o dispositivo com mais VRAM, desempate por menor índice.
        best_index = 0
        best_mem = -1
        for idx in range(self._probe.device_count()):
            mem = self._probe.total_memory_bytes(idx)
            if mem > best_mem:
                best_mem = mem
                best_index = idx

        cc = self._probe.compute_capability(best_index)
        name = self._probe.device_name(best_index)
        vram_gb = self._probe.total_memory_bytes(best_index) / (1024**3)
        return HardwareProfile(
            has_cuda=True,
            cuda_compute_capability=cc,
            vram_total_gb=vram_gb,
            gpu_name=name,
        )
