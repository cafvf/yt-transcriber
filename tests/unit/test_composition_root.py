from __future__ import annotations

import sys

from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.composition_root import _make_gpu_detector


def test_make_gpu_detector_falls_back_to_cpu_stub_when_torch_detector_is_unavailable(
    monkeypatch,
) -> None:
    monkeypatch.setitem(
        sys.modules,
        "yt_transcriber_bot.infrastructure.gpu.torch_gpu_detector",
        None,
    )

    detector = _make_gpu_detector()
    profile = detector.detect()

    assert isinstance(profile, HardwareProfile)
    assert profile.has_cuda is False
    assert profile.cuda_compute_capability is None
    assert profile.vram_total_gb == 0.0
    assert profile.gpu_name == ""
