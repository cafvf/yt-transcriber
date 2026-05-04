"""Testes de regressão da política de seleção de runtime.

Cada bug encontrado durante o gate gera um teste novo aqui para evitar
recorrência. Esta política está documentada na §0.2 do plano de execução.
"""

from __future__ import annotations

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.application.runtime_selection import select_runtime
from yt_transcriber_bot.domain.value_objects.device import DeviceKind


@pytest.fixture
def env_clean(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    for key in (
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_USER_ID",
        "HF_TOKEN",
        "DEVICE",
        "WHISPER_MODEL",
        "WHISPER_MODEL_PT",
        "WHISPER_MODEL_EN",
        "WHISPER_MODEL_DEFAULT",
        "COMPUTE_TYPE",
        "YT_TRANSCRIBER_ENV_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("YT_TRANSCRIBER_ENV_FILE", str(tmp_path / ".env"))


def _settings(**overrides: object) -> AppSettings:
    base: dict[str, object] = {
        "telegram_bot_token": "t",
        "telegram_allowed_user_id": 1,
        "hf_token": "hf",
        "whisper_model": "small",
        "device": "auto",
        "compute_type": "auto",
    }
    base.update(overrides)
    return AppSettings(**base)  # type: ignore[arg-type]


class TestRegressionVramFallbackIteration:
    """Bug: ``smaller_alternative`` só dava um passo para baixo.

    Com ``large-v3`` requisitando 10GB e VRAM = 6GB, o passo único caía em
    ``large-v2`` (também 10GB) e a política decidia CPU em vez de iterar
    até ``medium`` (5GB), que cabe.
    """

    def test_large_v3_steps_through_large_v2_to_medium(self, env_clean: None) -> None:
        plan = select_runtime(
            _settings(whisper_model="large-v3"),
            HardwareProfile(
                has_cuda=True,
                cuda_compute_capability=(8, 0),
                vram_total_gb=6.0,
                gpu_name="RTX 3060",
            ),
        )
        assert plan.device.kind is DeviceKind.CUDA
        assert plan.model.name == "medium"

    def test_large_v3_with_3gb_steps_to_small(self, env_clean: None) -> None:
        plan = select_runtime(
            _settings(whisper_model="large-v3"),
            HardwareProfile(
                has_cuda=True,
                cuda_compute_capability=(7, 5),
                vram_total_gb=3.0,
                gpu_name="X",
            ),
        )
        assert plan.device.kind is DeviceKind.CUDA
        assert plan.model.name == "small"

    def test_large_v3_with_1_5gb_steps_to_base(self, env_clean: None) -> None:
        plan = select_runtime(
            _settings(whisper_model="large-v3"),
            HardwareProfile(
                has_cuda=True,
                cuda_compute_capability=(7, 5),
                vram_total_gb=1.5,
                gpu_name="X",
            ),
        )
        assert plan.device.kind is DeviceKind.CUDA
        assert plan.model.name == "base"

    def test_large_v3_with_0_5gb_falls_back_to_cpu(self, env_clean: None) -> None:
        plan = select_runtime(
            _settings(whisper_model="large-v3"),
            HardwareProfile(
                has_cuda=True,
                cuda_compute_capability=(7, 5),
                vram_total_gb=0.5,
                gpu_name="X",
            ),
        )
        assert plan.device.kind is DeviceKind.CPU
