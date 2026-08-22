"""Testes da política de seleção de runtime."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.application.runtime_selection import (
    model_vram_requirement_gb,
    select_runtime,
    smaller_model_alternative,
)
from yt_transcriber_bot.domain.value_objects.compute_type import ComputeKind
from yt_transcriber_bot.domain.value_objects.device import DeviceKind
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.model_name import ModelName


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


def _hw(
    *,
    has_cuda: bool = True,
    cc: tuple[int, int] | None = (7, 5),
    vram_gb: float = 4.0,
    name: str = "Quadro T2000",
) -> HardwareProfile:
    return HardwareProfile(
        has_cuda=has_cuda,
        cuda_compute_capability=cc if has_cuda else None,
        vram_total_gb=vram_gb,
        gpu_name=name,
    )


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


class TestModelRuntimePolicy:
    def test_vram_requirement_increases_with_standard_model_size(self) -> None:
        tiny = model_vram_requirement_gb(ModelName("tiny"))
        large = model_vram_requirement_gb(ModelName("large-v3"))
        assert tiny < large

    def test_unknown_custom_model_uses_conservative_vram_policy(self) -> None:
        assert model_vram_requirement_gb(ModelName("provider/custom")) == 10.0

    def test_smaller_alternative_for_medium_is_small(self) -> None:
        result = smaller_model_alternative(ModelName("medium"))
        assert result == ModelName("small")

    def test_smaller_alternative_for_tiny_is_none(self) -> None:
        assert smaller_model_alternative(ModelName("tiny")) is None

    def test_custom_model_has_no_invented_smaller_alternative(self) -> None:
        assert smaller_model_alternative(ModelName("provider/custom")) is None


class TestForcedDevice:
    def test_force_cpu_respected(self, env_clean: None) -> None:
        plan = select_runtime(_settings(device="cpu"), _hw())
        assert plan.device.kind is DeviceKind.CPU
        assert plan.compute_type.kind is ComputeKind.INT8

    def test_force_cuda_respected_even_with_old_gpu(self, env_clean: None) -> None:
        plan = select_runtime(_settings(device="cuda"), _hw(cc=(5, 0), name="GeForce 940MX"))
        assert plan.device.kind is DeviceKind.CUDA
        assert plan.compute_type.kind is ComputeKind.FLOAT16

    def test_force_cpu_with_explicit_compute(self, env_clean: None) -> None:
        plan = select_runtime(_settings(device="cpu", compute_type="int8_float16"), _hw())
        assert plan.compute_type.kind is ComputeKind.INT8_FLOAT16


class TestAutoNoGpu:
    def test_no_cuda_falls_back_to_cpu(self, env_clean: None) -> None:
        plan = select_runtime(_settings(), _hw(has_cuda=False))
        assert plan.device.kind is DeviceKind.CPU
        assert "CUDA nao disponivel" in plan.reason

    def test_no_cuda_uses_int8_compute(self, env_clean: None) -> None:
        plan = select_runtime(_settings(), _hw(has_cuda=False))
        assert plan.compute_type.kind is ComputeKind.INT8


class TestAutoOldGpu:
    def test_cc_below_6_0_falls_back_to_cpu(self, env_clean: None) -> None:
        plan = select_runtime(_settings(), _hw(cc=(5, 0), vram_gb=4.0, name="GeForce 940MX"))
        assert plan.device.kind is DeviceKind.CPU
        assert "obsoleta" in plan.reason

    def test_cc_exactly_6_0_uses_cuda(self, env_clean: None) -> None:
        plan = select_runtime(
            _settings(whisper_model="tiny"),
            _hw(cc=(6, 0), vram_gb=4.0, name="GTX 1050"),
        )
        assert plan.device.kind is DeviceKind.CUDA


class TestAutoVramFallback:
    def test_insufficient_vram_for_large_v3_steps_down_to_medium_on_cuda(
        self, env_clean: None
    ) -> None:
        plan = select_runtime(
            _settings(whisper_model="large-v3"),
            _hw(cc=(8, 0), vram_gb=6.0),  # cabe medium (5GB) mas não large-v3 (10GB)
        )
        assert plan.device.kind is DeviceKind.CUDA
        assert plan.model.name == "medium"

    def test_insufficient_vram_for_smallest_falls_back_to_cpu(self, env_clean: None) -> None:
        plan = select_runtime(
            _settings(whisper_model="tiny"),
            _hw(cc=(8, 0), vram_gb=0.5),
        )
        assert plan.device.kind is DeviceKind.CPU

    def test_enough_vram_uses_cuda_with_requested_model(self, env_clean: None) -> None:
        plan = select_runtime(_settings(whisper_model="small"), _hw(cc=(7, 5), vram_gb=4.0))
        assert plan.device.kind is DeviceKind.CUDA
        assert plan.model.name == "small"


class TestComputeTypeResolution:
    def test_auto_compute_with_cuda_becomes_float16(self, env_clean: None) -> None:
        plan = select_runtime(_settings(compute_type="auto"), _hw())
        assert plan.compute_type.kind is ComputeKind.FLOAT16

    def test_auto_compute_with_cpu_becomes_int8(self, env_clean: None) -> None:
        plan = select_runtime(_settings(compute_type="auto"), _hw(has_cuda=False))
        assert plan.compute_type.kind is ComputeKind.INT8

    def test_explicit_float32_respected(self, env_clean: None) -> None:
        plan = select_runtime(_settings(compute_type="float32"), _hw())
        assert plan.compute_type.kind is ComputeKind.FLOAT32

    def test_int8_on_cuda_promoted_to_float16(self, env_clean: None) -> None:
        plan = select_runtime(_settings(compute_type="int8"), _hw())
        assert plan.compute_type.kind is ComputeKind.FLOAT16

    def test_float16_on_cpu_demoted_to_int8(self, env_clean: None) -> None:
        plan = select_runtime(_settings(compute_type="float16"), _hw(has_cuda=False))
        assert plan.compute_type.kind is ComputeKind.INT8


class TestLanguageAwareModelPolicy:
    def test_auto_model_uses_configured_model_for_portuguese(self, env_clean: None) -> None:
        settings = _settings(whisper_model="auto", whisper_model_pt="small")
        plan = select_runtime(
            settings,
            _hw(has_cuda=False),
            language=Language("pt"),
        )
        assert plan.model.name == settings.whisper_model_pt
        assert "idioma pt" in plan.reason

    def test_auto_model_uses_configured_model_for_english(self, env_clean: None) -> None:
        settings = _settings(whisper_model="auto", whisper_model_en="base")
        plan = select_runtime(
            settings,
            _hw(has_cuda=False),
            language=Language("en"),
        )
        assert plan.model.name == settings.whisper_model_en
        assert "idioma en" in plan.reason

    def test_explicit_model_overrides_language_policy(self, env_clean: None) -> None:
        plan = select_runtime(
            _settings(whisper_model="small"),
            _hw(has_cuda=False),
            language=Language("pt"),
        )
        assert plan.model.name == "small"
        assert "modelo fixo" in plan.reason
