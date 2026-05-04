"""Testes da configuração ``AppSettings``."""

from __future__ import annotations

from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings


@pytest.fixture
def env_no_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Garante que nenhum ``.env`` real influencia os testes."""
    monkeypatch.chdir(tmp_path)
    for key in (
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_USER_ID",
        "HF_TOKEN",
        "WHISPER_MODEL",
        "WHISPER_MODEL_PT",
        "WHISPER_MODEL_EN",
        "WHISPER_MODEL_DEFAULT",
        "DEVICE",
        "COMPUTE_TYPE",
        "AUDIO_BITRATE_KBPS",
        "MAX_VIDEO_DURATION_MIN",
        "RETENTION_COUNT",
        "SUMMARY_DISABLE_THINKING",
    ):
        monkeypatch.delenv(key, raising=False)


class TestAppSettingsDefaults:
    def test_defaults_are_sensible(self, env_no_dotenv: None) -> None:
        s = AppSettings()
        assert s.whisper_model == "auto"
        assert s.whisper_model_pt == "large-v3"
        assert s.whisper_model_en == "medium"
        assert s.whisper_model_default == "medium"
        assert s.device == "auto"
        assert s.compute_type == "auto"
        assert s.audio_bitrate_kbps == 32
        assert s.audio_sample_rate_hz == 16000
        assert s.max_video_duration_min == 180
        assert s.retention_count == 5
        assert s.allowed_languages == ("pt", "en")

    def test_directories_derive_from_base_dir(self, env_no_dotenv: None) -> None:
        s = AppSettings(base_dir=Path("/tmp/foo"))
        assert s.downloads_dir() == Path("/tmp/foo/downloads")
        assert s.processed_dir() == Path("/tmp/foo/processed")
        assert s.transcripts_dir() == Path("/tmp/foo/transcripts")
        assert s.logs_dir() == Path("/tmp/foo/logs")


class TestAppSettingsValidation:
    def test_invalid_device_raises(self, env_no_dotenv: None) -> None:
        with pytest.raises(ValueError, match="device"):
            AppSettings(device="tpu")

    def test_invalid_compute_type_raises(self, env_no_dotenv: None) -> None:
        with pytest.raises(ValueError, match="compute_type"):
            AppSettings(compute_type="bfloat16")

    def test_invalid_model_raises(self, env_no_dotenv: None) -> None:
        with pytest.raises(ValueError, match="whisper_model"):
            AppSettings(whisper_model="huge")

    def test_invalid_language_model_raises(self, env_no_dotenv: None) -> None:
        with pytest.raises(ValueError, match="modelo Whisper por idioma"):
            AppSettings(whisper_model_pt="huge")

    def test_bitrate_lower_bound(self, env_no_dotenv: None) -> None:
        with pytest.raises(ValueError, match="audio_bitrate_kbps"):
            AppSettings(audio_bitrate_kbps=8)

    def test_bitrate_upper_bound(self, env_no_dotenv: None) -> None:
        with pytest.raises(ValueError, match="audio_bitrate_kbps"):
            AppSettings(audio_bitrate_kbps=256)

    def test_max_duration_min_positive(self, env_no_dotenv: None) -> None:
        with pytest.raises(ValueError, match="max_video_duration_min"):
            AppSettings(max_video_duration_min=0)


class TestAppSettingsEnvLoading:
    def test_loads_from_env_vars(
        self, env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("TELEGRAM_ALLOWED_USER_ID", "42")
        monkeypatch.setenv("HF_TOKEN", "hf_x")
        monkeypatch.setenv("WHISPER_MODEL", "medium")
        monkeypatch.setenv("WHISPER_MODEL_PT", "large-v3")
        monkeypatch.setenv("WHISPER_MODEL_EN", "medium")
        s = AppSettings()
        assert s.telegram_bot_token == "tok"
        assert s.telegram_allowed_user_id == 42
        assert s.hf_token == "hf_x"
        assert s.whisper_model == "medium"
        assert s.whisper_model_pt == "large-v3"
        assert s.whisper_model_en == "medium"


class TestRuntimeSecretsValidation:
    def test_all_present_returns_empty(self, env_no_dotenv: None) -> None:
        s = AppSettings(
            telegram_bot_token="t",
            telegram_allowed_user_id=42,
            hf_token="hf",
        )
        assert s.validate_runtime_secrets() == []

    def test_missing_token_reported(self, env_no_dotenv: None) -> None:
        s = AppSettings(
            telegram_bot_token="",
            telegram_allowed_user_id=42,
            hf_token="hf",
        )
        problems = s.validate_runtime_secrets()
        assert any("TELEGRAM_BOT_TOKEN" in p for p in problems)

    def test_missing_user_id_reported(self, env_no_dotenv: None) -> None:
        s = AppSettings(
            telegram_bot_token="t",
            telegram_allowed_user_id=0,
            hf_token="hf",
        )
        problems = s.validate_runtime_secrets()
        assert any("ALLOWED_USER_ID" in p for p in problems)

    def test_missing_hf_token_reported(self, env_no_dotenv: None) -> None:
        s = AppSettings(
            telegram_bot_token="t",
            telegram_allowed_user_id=42,
            hf_token="",
        )
        problems = s.validate_runtime_secrets()
        assert any("HF_TOKEN" in p for p in problems)

    def test_all_missing_returns_three(self, env_no_dotenv: None) -> None:
        s = AppSettings()
        assert len(s.validate_runtime_secrets()) == 3


class TestTranscriptionSignature:
    def test_signature_is_stable_for_same_inputs(self, env_no_dotenv: None) -> None:
        s1 = AppSettings(whisper_model="small")
        s2 = AppSettings(whisper_model="small")
        assert s1.transcription_signature() == s2.transcription_signature()

    def test_signature_changes_when_model_changes(self, env_no_dotenv: None) -> None:
        s1 = AppSettings(whisper_model="small")
        s2 = AppSettings(whisper_model="medium")
        assert s1.transcription_signature() != s2.transcription_signature()

    def test_signature_changes_when_language_model_changes(self, env_no_dotenv: None) -> None:
        s1 = AppSettings(whisper_model="auto", whisper_model_pt="large-v3")
        s2 = AppSettings(whisper_model="auto", whisper_model_pt="medium")
        assert s1.transcription_signature() != s2.transcription_signature()

    def test_signature_changes_when_compute_type_changes(self, env_no_dotenv: None) -> None:
        s1 = AppSettings(compute_type="auto")
        s2 = AppSettings(compute_type="int8")
        assert s1.transcription_signature() != s2.transcription_signature()

    def test_signature_changes_when_bitrate_changes(self, env_no_dotenv: None) -> None:
        s1 = AppSettings(audio_bitrate_kbps=32)
        s2 = AppSettings(audio_bitrate_kbps=64)
        assert s1.transcription_signature() != s2.transcription_signature()


def test_summary_settings_defaults_are_lm_studio_compatible(tmp_path):
    settings = AppSettings(
        telegram_bot_token="x",
        telegram_allowed_user_id=42,
        hf_token="x",
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
    )
    assert settings.summary_backend == "openai_compatible"
    assert settings.summary_base_url == "http://localhost:1234/v1"
    assert settings.summary_model == "qwen3.5-9b"
    assert settings.summary_max_tokens == 1024
    assert settings.summary_max_chars_per_chunk == 4000
    assert settings.summary_max_input_tokens == 2500
    assert settings.summary_chars_per_token == 2.0
    assert settings.summary_timeout_s == 300.0
    assert settings.summary_disable_thinking is True
    assert settings.summary_validate_model is True
    assert settings.summary_strict_model_match is True
    assert settings.summaries_dir() == tmp_path / "data" / "summaries"


def test_summary_disable_thinking_can_be_disabled_from_env(env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUMMARY_DISABLE_THINKING", "false")
    settings = AppSettings()
    assert settings.summary_disable_thinking is False


def test_summary_model_guard_can_be_disabled_from_env(env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUMMARY_VALIDATE_MODEL", "false")
    monkeypatch.setenv("SUMMARY_STRICT_MODEL_MATCH", "false")
    settings = AppSettings()
    assert settings.summary_validate_model is False
    assert settings.summary_strict_model_match is False
