"""Testes para os value objects ``Duration``, ``Language``, ``ModelName``, ``Device``, ``ComputeType``."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.domain.value_objects.compute_type import ComputeType
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.model_name import ModelName


class TestDuration:
    def test_construction_with_zero_seconds_succeeds(self) -> None:
        assert Duration(seconds=0).seconds == 0

    def test_negative_seconds_raises(self) -> None:
        with pytest.raises(ValueError, match="não-negativa"):
            Duration(seconds=-1)

    def test_from_seconds_floors_floats(self) -> None:
        assert Duration.from_seconds(330.7).seconds == 330

    def test_from_minutes(self) -> None:
        assert Duration.from_minutes(3).seconds == 180

    def test_from_minutes_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="não-negativo"):
            Duration.from_minutes(-1)

    def test_to_hms_under_an_hour(self) -> None:
        assert Duration(seconds=330).to_hms() == "00:05:30"

    def test_to_hms_over_an_hour(self) -> None:
        assert Duration(seconds=3725).to_hms() == "01:02:05"

    def test_to_human_seconds_only(self) -> None:
        assert Duration(seconds=42).to_human() == "42s"

    def test_to_human_minutes_and_seconds(self) -> None:
        assert Duration(seconds=125).to_human() == "2min 05s"

    def test_to_human_hours_minutes_seconds(self) -> None:
        assert Duration(seconds=3725).to_human() == "1h 02min 05s"

    def test_comparison(self) -> None:
        a = Duration(seconds=100)
        b = Duration(seconds=200)
        assert a < b
        assert b > a
        assert a <= a
        assert a >= a


class TestLanguage:
    def test_pt_factory(self) -> None:
        assert Language.pt().code == "pt"

    def test_en_factory(self) -> None:
        assert Language.en().code == "en"

    def test_uppercase_code_rejected(self) -> None:
        with pytest.raises(ValueError, match="inválido"):
            Language(code="PT")

    def test_three_letters_rejected(self) -> None:
        with pytest.raises(ValueError, match="inválido"):
            Language(code="por")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError, match="inválido"):
            Language(code="")

    def test_str_returns_code(self) -> None:
        assert str(Language.pt()) == "pt"

    def test_equality(self) -> None:
        assert Language.pt() == Language(code="pt")
        assert Language.pt() != Language.en()


class TestModelName:
    @pytest.mark.parametrize(
        "name",
        ["tiny", "base", "small", "medium", "large-v2", "large-v3"],
    )
    def test_accepts_supported_models(self, name: str) -> None:
        assert ModelName(name=name).name == name

    def test_rejects_unsupported(self) -> None:
        with pytest.raises(ValueError, match="não suportado"):
            ModelName(name="huge")

    def test_vram_requirement_increases_with_size(self) -> None:
        tiny = ModelName(name="tiny").vram_requirement_gb()
        large = ModelName(name="large-v3").vram_requirement_gb()
        assert tiny < large

    def test_smaller_alternative_for_medium_is_small(self) -> None:
        result = ModelName.smaller_alternative(ModelName(name="medium"))
        assert result == ModelName(name="small")

    def test_smaller_alternative_for_tiny_is_none(self) -> None:
        assert ModelName.smaller_alternative(ModelName(name="tiny")) is None


class TestDevice:
    def test_auto_factory(self) -> None:
        assert Device.auto().is_auto()

    def test_cpu_factory(self) -> None:
        assert Device.cpu().is_cpu()

    def test_cuda_factory(self) -> None:
        assert Device.cuda().is_cuda()

    def test_from_string_valid(self) -> None:
        assert Device.from_string("cuda").is_cuda()

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="inválido"):
            Device.from_string("tpu")

    def test_str_returns_kind(self) -> None:
        assert str(Device.cpu()) == "cpu"


class TestComputeType:
    @pytest.mark.parametrize(
        "raw",
        ["auto", "float32", "float16", "int8_float16", "int8"],
    )
    def test_accepts_valid(self, raw: str) -> None:
        assert ComputeType.from_string(raw).kind.value == raw

    def test_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="inválido"):
            ComputeType.from_string("bfloat16")

    def test_auto_factory(self) -> None:
        assert ComputeType.auto().kind.value == "auto"
