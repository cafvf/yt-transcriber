"""Testes do ``TorchGpuDetector`` usando probes falsos."""

from __future__ import annotations

from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.infrastructure.gpu.torch_gpu_detector import (
    TorchGpuDetector,
    TorchProbe,
)


class FakeProbe(TorchProbe):
    def __init__(
        self,
        *,
        available: bool = True,
        devices: tuple[tuple[str, tuple[int, int], int], ...] = (),
    ) -> None:
        self._available = available
        self._devices = devices

    def is_available(self) -> bool:
        return self._available

    def device_count(self) -> int:
        return len(self._devices)

    def device_name(self, index: int) -> str:
        return self._devices[index][0]

    def compute_capability(self, index: int) -> tuple[int, int]:
        return self._devices[index][1]

    def total_memory_bytes(self, index: int) -> int:
        return self._devices[index][2]


_GB = 1024**3


class TestTorchGpuDetector:
    def test_no_cuda_returns_empty_profile(self) -> None:
        detector = TorchGpuDetector(probe=FakeProbe(available=False))
        profile = detector.detect()
        assert profile.has_cuda is False
        assert profile.cuda_compute_capability is None
        assert profile.vram_total_gb == 0.0
        assert profile.gpu_name == ""

    def test_no_devices_returns_empty(self) -> None:
        detector = TorchGpuDetector(probe=FakeProbe(available=True, devices=()))
        profile = detector.detect()
        assert profile.has_cuda is False

    def test_single_gpu_detected(self) -> None:
        probe = FakeProbe(
            available=True,
            devices=(("Quadro T2000", (7, 5), 4 * _GB),),
        )
        profile = TorchGpuDetector(probe=probe).detect()
        assert profile.has_cuda is True
        assert profile.gpu_name == "Quadro T2000"
        assert profile.cuda_compute_capability == (7, 5)
        assert profile.vram_total_gb == 4.0

    def test_multiple_gpus_picks_largest_vram(self) -> None:
        probe = FakeProbe(
            available=True,
            devices=(
                ("Old GPU", (5, 0), 2 * _GB),
                ("Newer GPU", (8, 6), 8 * _GB),
                ("Mid GPU", (7, 5), 4 * _GB),
            ),
        )
        profile = TorchGpuDetector(probe=probe).detect()
        assert profile.gpu_name == "Newer GPU"
        assert profile.vram_total_gb == 8.0
        assert profile.cuda_compute_capability == (8, 6)


class TestHardwareProfileMethods:
    def test_is_cuda_compatible_true_above_threshold(self) -> None:
        p = HardwareProfile(
            has_cuda=True,
            cuda_compute_capability=(7, 5),
            vram_total_gb=4.0,
            gpu_name="Quadro T2000",
        )
        assert p.is_cuda_compatible() is True

    def test_is_cuda_compatible_false_below_threshold(self) -> None:
        p = HardwareProfile(
            has_cuda=True,
            cuda_compute_capability=(5, 0),
            vram_total_gb=4.0,
            gpu_name="GeForce 940MX",
        )
        assert p.is_cuda_compatible() is False

    def test_is_cuda_compatible_false_no_cuda(self) -> None:
        p = HardwareProfile(
            has_cuda=False,
            cuda_compute_capability=None,
            vram_total_gb=0.0,
            gpu_name="",
        )
        assert p.is_cuda_compatible() is False

    def test_custom_threshold(self) -> None:
        p = HardwareProfile(
            has_cuda=True,
            cuda_compute_capability=(8, 0),
            vram_total_gb=12.0,
            gpu_name="A100",
        )
        assert p.is_cuda_compatible(min_compute_capability=(8, 0)) is True
        assert p.is_cuda_compatible(min_compute_capability=(9, 0)) is False

    def test_can_fit_model_true(self) -> None:
        p = HardwareProfile(
            has_cuda=True,
            cuda_compute_capability=(8, 0),
            vram_total_gb=12.0,
            gpu_name="X",
        )
        assert p.can_fit_model(10.0) is True

    def test_can_fit_model_false(self) -> None:
        p = HardwareProfile(
            has_cuda=True,
            cuda_compute_capability=(8, 0),
            vram_total_gb=4.0,
            gpu_name="X",
        )
        assert p.can_fit_model(8.0) is False
