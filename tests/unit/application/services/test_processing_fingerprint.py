"""Testes do fingerprint canônico de processamento."""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.processing_fingerprint import (
    PROCESSING_FINGERPRINT_VERSION,
    SIGNIFICANT_FIELDS,
    compute_processing_fingerprint,
    describe_config,
    diff_configs,
    processing_fingerprint_payload,
)
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.media_source import MediaSourceType


def _settings(tmp_path: Path, **kwargs: object) -> AppSettings:
    values: dict[str, object] = {
        "telegram_bot_token": "token-for-test",
        "telegram_allowed_user_id": 42,
        "hf_token": "hf_test",
        "base_dir": tmp_path / "data",
        "models_dir": tmp_path / "models",
    }
    values.update(kwargs)
    return AppSettings(**values)


def test_fingerprint_is_stable_for_same_output_significant_inputs(
    tmp_path: Path,
) -> None:
    first = _settings(tmp_path)
    second = _settings(tmp_path)
    assert compute_processing_fingerprint(first) == compute_processing_fingerprint(second)


def test_fingerprint_changes_for_asr_audio_language_and_source_policy(
    tmp_path: Path,
) -> None:
    base = _settings(tmp_path)
    variants = (
        _settings(tmp_path, whisper_model="small"),
        _settings(tmp_path, audio_bitrate_kbps=64),
        _settings(tmp_path, allowed_languages=("en",)),
        _settings(tmp_path, prefer_youtube_subtitles=False),
    )
    baseline = compute_processing_fingerprint(base)
    assert all(compute_processing_fingerprint(item) != baseline for item in variants)


def test_fingerprint_changes_with_request_language(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    automatic = compute_processing_fingerprint(settings)
    forced = compute_processing_fingerprint(
        settings,
        requested_language=Language("pt"),
    )
    assert forced != automatic


def test_fingerprint_changes_with_media_source_type(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    youtube = compute_processing_fingerprint(
        settings,
        source_type=MediaSourceType.YOUTUBE,
    )
    telegram = compute_processing_fingerprint(
        settings,
        source_type=MediaSourceType.TELEGRAM_AUDIO,
    )
    assert youtube != telegram


def test_credentials_paths_and_operational_settings_do_not_change_fingerprint(
    tmp_path: Path,
) -> None:
    base = _settings(tmp_path)
    changed = _settings(
        tmp_path,
        telegram_bot_token="another-token",
        hf_token="hf_another",
        summary_api_key="private-key",
        base_dir=tmp_path / "another-data",
        models_dir=tmp_path / "another-models",
        retention_count=99,
        telegram_message_edit_min_interval_s=5.0,
    )
    assert compute_processing_fingerprint(base) == compute_processing_fingerprint(changed)


def test_payload_is_versioned_and_contains_declared_significant_fields(
    tmp_path: Path,
) -> None:
    payload = processing_fingerprint_payload(_settings(tmp_path))
    assert payload["fingerprint_version"] == PROCESSING_FINGERPRINT_VERSION == 1
    for field in SIGNIFICANT_FIELDS:
        assert field in payload
    assert "telegram_bot_token" not in payload
    assert "hf_token" not in payload
    assert "base_dir" not in payload


def test_describe_config_and_diff_use_canonical_fingerprint_fields(
    tmp_path: Path,
) -> None:
    old = describe_config(_settings(tmp_path, whisper_model="small"))
    new = describe_config(_settings(tmp_path, whisper_model="medium"))
    changes = diff_configs(old, new)
    assert [change.field for change in changes] == ["whisper_model"]
    assert changes[0].old_value == "small"
    assert changes[0].new_value == "medium"
