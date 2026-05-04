"""Testes da configuração ``AppSettings``."""

from __future__ import annotations

from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import (
    AppSettings,
    find_project_root,
    resolve_settings_env_file,
)


def _assert_defined(value: str) -> None:
    """Verifica que um campo textual de configuração tem valor efetivo."""

    assert isinstance(value, str)
    assert value.strip()


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
        "SUMMARY_MODEL",
        "SUMMARY_BACKEND",
        "SUMMARY_BASE_URL",
        "SUMMARY_DISABLE_THINKING",
        "SUMMARY_VALIDATE_MODEL",
        "SUMMARY_STRICT_MODEL_MATCH",
        "YT_TRANSCRIBER_ENV_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("YT_TRANSCRIBER_ENV_FILE", str(tmp_path / ".env"))


class TestAppSettingsDefaults:
    def test_defaults_are_sensible(self, env_no_dotenv: None) -> None:
        s = AppSettings()
        _assert_defined(s.whisper_model)
        _assert_defined(s.whisper_model_pt)
        _assert_defined(s.whisper_model_en)
        _assert_defined(s.whisper_model_default)
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


def test_summary_settings_defaults_are_lm_studio_compatible(
    env_no_dotenv: None, tmp_path: Path
) -> None:
    settings = AppSettings(
        telegram_bot_token="x",
        telegram_allowed_user_id=42,
        hf_token="x",
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
    )
    assert settings.summary_backend == "openai_compatible"
    assert settings.summary_base_url == "http://localhost:1234/v1"
    _assert_defined(settings.summary_model)
    assert settings.summary_max_tokens > 0
    assert settings.summary_partial_max_tokens > 0
    assert settings.summary_final_max_tokens >= settings.summary_partial_max_tokens
    assert settings.summary_max_chars_per_chunk >= 1000
    assert settings.summary_max_input_tokens >= 1000
    assert settings.summary_chars_per_token >= 1.0
    assert settings.summary_tokenizer_backend == "auto"
    assert settings.summary_tokenizer_model == ""
    assert settings.summary_deduplicate_transcript is True
    assert settings.summary_merge_same_speaker_gap_s == 2.0
    assert settings.summary_min_overlap_words == 6
    assert settings.summary_timeout_s >= 300.0
    assert settings.summary_timeout_split_retries >= 0
    assert settings.summary_disable_thinking is True
    assert settings.summary_validate_model is True
    assert settings.summary_strict_model_match is True
    assert settings.summaries_dir() == tmp_path / "data" / "summaries"



def test_summary_tokenizer_backend_is_normalized(env_no_dotenv: None) -> None:
    assert AppSettings(summary_tokenizer_backend="huggingface").summary_tokenizer_backend == "hf"
    assert AppSettings(summary_tokenizer_backend="estimated").summary_tokenizer_backend == "estimate"

    with pytest.raises(ValueError):
        AppSettings(summary_tokenizer_backend="unknown")

def test_summary_disable_thinking_can_be_disabled_from_env(
    env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUMMARY_DISABLE_THINKING", "false")
    settings = AppSettings()
    assert settings.summary_disable_thinking is False


def test_summary_model_guard_can_be_disabled_from_env(
    env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUMMARY_VALIDATE_MODEL", "false")
    monkeypatch.setenv("SUMMARY_STRICT_MODEL_MATCH", "false")
    settings = AppSettings()
    assert settings.summary_validate_model is False
    assert settings.summary_strict_model_match is False


def test_summary_model_is_loaded_from_detected_project_root_dotenv(
    env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "yt-transcriber-bot"\n', encoding="utf-8"
    )
    (tmp_path / ".env").write_text("SUMMARY_MODEL=modelo-do-dotenv\n", encoding="utf-8")
    monkeypatch.delenv("YT_TRANSCRIBER_ENV_FILE", raising=False)

    settings = AppSettings()

    assert find_project_root() == tmp_path
    assert resolve_settings_env_file() == tmp_path / ".env"
    assert settings.summary_model == "modelo-do-dotenv"


def test_summary_model_can_be_forced_with_env_file_override(
    env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    forced_env = tmp_path / "config" / "bot.env"
    forced_env.parent.mkdir()
    forced_env.write_text("SUMMARY_MODEL=modelo-forcado\n", encoding="utf-8")
    other_cwd = tmp_path / "other-cwd"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    monkeypatch.setenv("YT_TRANSCRIBER_ENV_FILE", str(forced_env))

    settings = AppSettings()

    assert settings.summary_model == "modelo-forcado"


def test_env_example_is_not_loaded_as_runtime_default(
    env_no_dotenv: None, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "yt-transcriber-bot"\n', encoding="utf-8"
    )
    (tmp_path / ".env.example").write_text(
        "SUMMARY_MODEL=modelo-errado-do-example\n", encoding="utf-8"
    )

    settings = AppSettings()

    assert resolve_settings_env_file() == tmp_path / ".env"
    _assert_defined(settings.summary_model)
    assert settings.summary_model != "modelo-errado-do-example"


def test_forced_env_file_rejects_env_example(
    env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    example = tmp_path / ".env.example"
    example.write_text("SUMMARY_MODEL=modelo-errado-do-example\n", encoding="utf-8")
    monkeypatch.setenv("YT_TRANSCRIBER_ENV_FILE", str(example))

    with pytest.raises(ValueError, match=".env.example"):
        AppSettings()



def test_summary_model_real_environment_overrides_dotenv_and_is_diagnosable(
    env_no_dotenv: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text("SUMMARY_MODEL=modelo-do-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("SUMMARY_MODEL", "modelo-do-ambiente-real")

    settings = AppSettings()

    assert settings.summary_model == "modelo-do-ambiente-real"

    from scripts.config.print_effective_settings import build_report_lines

    report = "\n".join(build_report_lines(settings))
    assert "summary_model=modelo-do-ambiente-real" in report
    assert "origem: ambiente real SUMMARY_MODEL" in report
    assert "sobrescreve .env" in report
