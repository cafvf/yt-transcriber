"""PLAN-007 Gate A compatibility tests for media duration naming."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.config.print_effective_settings import build_report_lines

from yt_transcriber_bot.application.config import AppSettings


@pytest.fixture
def isolated_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    for key in (
        "MAX_MEDIA_DURATION_MIN",
        "MAX_VIDEO_DURATION_MIN",
        "YT_TRANSCRIBER_ENV_FILE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(
        "YT_TRANSCRIBER_ENV_FILE",
        str(tmp_path / ".env"),
    )


def test_canonical_media_duration_environment_name(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_MEDIA_DURATION_MIN", "31")
    settings = AppSettings()
    assert settings.max_media_duration_min == 31


def test_legacy_video_duration_environment_name_remains_compatible(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_VIDEO_DURATION_MIN", "17")
    settings = AppSettings()
    assert settings.max_media_duration_min == 17


def test_canonical_environment_name_wins_when_both_are_set(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_VIDEO_DURATION_MIN", "17")
    monkeypatch.setenv("MAX_MEDIA_DURATION_MIN", "29")
    settings = AppSettings()
    assert settings.max_media_duration_min == 29


def test_canonical_constructor_name_is_accepted_at_config_boundary(
    isolated_env: None,
) -> None:
    settings = AppSettings(max_media_duration_min=23)
    assert settings.max_media_duration_min == 23


def test_invalid_canonical_duration_environment_value_is_rejected(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_MEDIA_DURATION_MIN", "0")
    with pytest.raises(ValueError, match="MAX_MEDIA_DURATION_MIN"):
        AppSettings()


def test_invalid_legacy_duration_environment_value_is_rejected(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_VIDEO_DURATION_MIN", "0")
    with pytest.raises(ValueError, match="MAX_MEDIA_DURATION_MIN"):
        AppSettings()


def test_invalid_canonical_duration_constructor_value_is_rejected(
    isolated_env: None,
) -> None:
    with pytest.raises(ValueError, match=r"(?i)max_media_duration_min"):
        AppSettings(max_media_duration_min=0)


def test_report_identifies_legacy_duration_environment_source(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_VIDEO_DURATION_MIN", "17")
    settings = AppSettings()
    report = "\n".join(build_report_lines(settings))

    assert "max_media_duration_min=17" in report
    assert "origem: ambiente real MAX_VIDEO_DURATION_MIN" in report


def test_report_identifies_canonical_duration_source_when_both_are_set(
    isolated_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_VIDEO_DURATION_MIN", "17")
    monkeypatch.setenv("MAX_MEDIA_DURATION_MIN", "29")
    settings = AppSettings()
    report = "\n".join(build_report_lines(settings))

    assert settings.max_media_duration_min == 29
    assert "max_media_duration_min=29" in report
    assert "origem: ambiente real MAX_MEDIA_DURATION_MIN" in report
