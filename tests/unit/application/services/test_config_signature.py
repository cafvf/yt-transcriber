"""Testes do compute_config_signature, describe_config e diff_configs."""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.config_signature import (
    compute_config_signature,
    describe_config,
    diff_configs,
)


def _make_settings(tmp_path: Path, **overrides: object) -> AppSettings:
    base = {
        "telegram_bot_token": "x",
        "telegram_allowed_user_id": 42,
        "hf_token": "x",
        "data_dir": tmp_path / "data",
        "models_dir": tmp_path / "models",
        "logs_dir": tmp_path / "logs",
    }
    base.update(overrides)
    return AppSettings(**base)  # type: ignore[arg-type]


def test_signature_is_stable(tmp_path: Path) -> None:
    a = _make_settings(tmp_path)
    b = _make_settings(tmp_path)
    assert compute_config_signature(a) == compute_config_signature(b)


def test_signature_changes_when_model_changes(tmp_path: Path) -> None:
    a = _make_settings(tmp_path, whisper_model="small")
    b = _make_settings(tmp_path, whisper_model="medium")
    assert compute_config_signature(a) != compute_config_signature(b)


def test_signature_unchanged_for_irrelevant_fields(tmp_path: Path) -> None:
    a = _make_settings(tmp_path, telegram_message_edit_min_interval_s=2.0)
    b = _make_settings(tmp_path, telegram_message_edit_min_interval_s=5.0)
    assert compute_config_signature(a) == compute_config_signature(b)


def test_describe_returns_significant_fields(tmp_path: Path) -> None:
    s = _make_settings(tmp_path, whisper_model="medium", device="cuda")
    desc = describe_config(s)
    assert desc["whisper_model"] == "medium"
    assert desc["device"] == "cuda"
    assert "telegram_bot_token" not in desc


def test_diff_returns_only_changed_fields(tmp_path: Path) -> None:
    a = describe_config(_make_settings(tmp_path, whisper_model="small", device="cpu"))
    b = describe_config(_make_settings(tmp_path, whisper_model="medium", device="cpu"))
    changes = diff_configs(a, b)
    assert len(changes) == 1
    assert changes[0].field == "whisper_model"
    assert changes[0].old_value == "small"
    assert changes[0].new_value == "medium"


def test_diff_empty_when_equal(tmp_path: Path) -> None:
    a = describe_config(_make_settings(tmp_path))
    b = describe_config(_make_settings(tmp_path))
    assert diff_configs(a, b) == ()


def test_diff_handles_missing_field() -> None:
    """Se uma das versões não tiver um campo, marca <n/a>."""
    a = {"whisper_model": "small"}
    b = {"whisper_model": "small", "device": "cuda"}
    changes = diff_configs(a, b)
    assert any(c.field == "device" and c.old_value == "<n/a>" for c in changes)
