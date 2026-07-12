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


def test_build_wires_summary_tokenizer_trust_remote_code(monkeypatch, tmp_path) -> None:
    import yt_transcriber_bot.composition_root as composition_root
    from yt_transcriber_bot.application.config import AppSettings

    captured: dict[str, object] = {}

    class FakeTranscriptSummaryService:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(composition_root, "_make_gpu_detector", lambda: object())
    monkeypatch.setattr(composition_root, "_make_transcription_engine", lambda: object())
    monkeypatch.setattr(composition_root, "_make_diarization_engine", lambda: object())
    monkeypatch.setattr(
        composition_root,
        "TranscriptSummaryService",
        FakeTranscriptSummaryService,
    )

    settings = AppSettings(
        telegram_bot_token="123:token",
        telegram_allowed_user_id=42,
        hf_token="hf_test",
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        db_path=tmp_path / "data" / "jobs.db",
        summary_backend="openai_compatible",
        summary_tokenizer_trust_remote_code=True,
    )

    composition = composition_root.build(settings)

    assert isinstance(composition.summary_service, FakeTranscriptSummaryService)
    assert captured["tokenizer_trust_remote_code"] is True
