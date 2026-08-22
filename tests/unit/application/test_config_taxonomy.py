"""REQ-ARC-010 configuration taxonomy and compatibility tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings, MediaProcessingSettings
from yt_transcriber_bot.configuration.credentials import ProviderCredentials


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in (
        "TELEGRAM_BOT_TOKEN",
        "HF_TOKEN",
        "SUMMARY_API_KEY",
        "YOUTUBE_COOKIES_FILE",
        "YOUTUBE_COOKIES_BROWSER",
        "MAX_MEDIA_DURATION_MIN",
        "MAX_VIDEO_DURATION_MIN",
        "YT_TRANSCRIBER_ENV_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("YT_TRANSCRIBER_ENV_FILE", str(tmp_path / ".env"))


def test_provider_credentials_are_not_ordinary_appsettings_model_fields(
    isolated_env: None,
) -> None:
    secret_fields = {
        "telegram_bot_token",
        "hf_token",
        "summary_api_key",
        "youtube_cookies_file",
        "youtube_cookies_browser",
    }
    assert secret_fields.isdisjoint(AppSettings.model_fields)
    assert secret_fields == set(ProviderCredentials.model_fields)


def test_legacy_flat_constructor_arguments_remain_accepted(isolated_env: None) -> None:
    settings = AppSettings(
        telegram_bot_token="123:test-token",
        hf_token="hf_test",
        summary_api_key="test-key",
        youtube_cookies_file="/tmp/test-cookies.txt",
        youtube_cookies_browser="firefox",
    )
    assert settings.telegram_bot_token == "123:test-token"
    assert settings.hf_token == "hf_test"
    assert settings.summary_api_key == "test-key"
    assert settings.youtube_cookies_file == "/tmp/test-cookies.txt"
    assert settings.youtube_cookies_browser == "firefox"
    assert settings.credentials.telegram_bot_token == settings.telegram_bot_token


def test_approved_operator_environment_names_remain_accepted(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:env-token")
    monkeypatch.setenv("HF_TOKEN", "hf_env")
    monkeypatch.setenv("SUMMARY_API_KEY", "env-key")
    monkeypatch.setenv("YOUTUBE_COOKIES_FILE", "/tmp/env-cookies.txt")
    monkeypatch.setenv("YOUTUBE_COOKIES_BROWSER", "firefox")
    monkeypatch.setenv("MAX_VIDEO_DURATION_MIN", "17")
    settings = AppSettings()
    assert settings.credentials.telegram_bot_token == "123:env-token"
    assert settings.credentials.hf_token == "hf_env"
    assert settings.credentials.summary_api_key == "env-key"
    assert settings.credentials.youtube_cookies_file == "/tmp/env-cookies.txt"
    assert settings.credentials.youtube_cookies_browser == "firefox"
    assert settings.max_media_duration_min == 17


def test_generic_media_view_uses_source_neutral_internal_name(isolated_env: None) -> None:
    settings = AppSettings(max_media_duration_min=23)
    media = settings.media_processing
    assert isinstance(media, MediaProcessingSettings)
    assert media.max_media_duration_min == 23
    assert not any("video" in field for field in media.__dataclass_fields__)


def test_behavior_policy_constructs_without_provider_credentials(isolated_env: None) -> None:
    settings = AppSettings(telegram_bot_token="", hf_token="", summary_api_key="")
    media = settings.media_processing
    assert media.max_media_duration_min > 0
    assert media.allowed_languages
