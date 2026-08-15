"""Shared sanitization security contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services import sanitization
from yt_transcriber_bot.application.services.sanitization import sanitize_text, sanitize_value


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="configured-telegram-secret-123",
        telegram_allowed_user_id=42,
        hf_token="configured-hf-secret-123",
        summary_api_key="configured-summary-secret-123",
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
    )


def test_structured_sanitizer_redacts_secrets_omits_payloads_and_paths(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    value = {
        "authorization": "Bearer configured-telegram-secret-123",
        "transcript": "private transcript body",
        "model": "approved-model",
        "artifact_path": "/private/transcripts/item.md",
        "user_id": 42,
    }

    cleaned = sanitize_value("details", value, settings)

    assert cleaned == {
        "authorization": "[REDACTED]",
        "transcript": "[OMITTED]",
        "model": "approved-model",
        "artifact_path": "[PRIVATE PATH]",
        "user_id": "[PRIVATE IDENTIFIER]",
    }


def test_configured_secret_is_redacted_from_free_form_text(tmp_path: Path) -> None:
    secret = "configured-summary-secret-123"
    cleaned = sanitize_text(f"backend failed with {secret}", _settings(tmp_path))

    assert secret not in cleaned
    assert "[REDACTED]" in cleaned


def test_sanitization_failure_returns_generic_safe_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_text: str, _settings: AppSettings | None) -> str:
        raise RuntimeError("raw private material")

    monkeypatch.setattr(sanitization, "_sanitize_text", fail)

    assert sanitize_text("must never be returned") == "[SAFE ERROR DETAIL OMITTED]"


def test_free_form_operator_transport_id_is_not_disclosed(tmp_path: Path) -> None:
    cleaned = sanitize_text("Usuário autorizado: user_id=42", _settings(tmp_path))

    assert "user_id=42" not in cleaned
    assert "[PRIVATE IDENTIFIER]" in cleaned


def test_free_form_configured_filesystem_path_is_not_disclosed(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    private_path = settings.logs_dir().resolve() / "job-1.log"
    cleaned = sanitize_text(f"failed reading {private_path}", settings)

    assert str(private_path) not in cleaned
    assert "[PRIVATE PATH]" in cleaned


def test_free_form_mixed_secret_and_payload_preserves_distinct_markers(tmp_path: Path) -> None:
    cleaned = sanitize_text(
        "Authorization: Bearer bearer-secret Cookie: session=abc transcript=private body",
        _settings(tmp_path),
    )

    assert "bearer-secret" not in cleaned
    assert "session=abc" not in cleaned
    assert "private body" not in cleaned
    assert "[REDACTED]" in cleaned
    assert "[OMITTED]" in cleaned
