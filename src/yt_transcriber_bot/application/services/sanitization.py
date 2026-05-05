"""Sanitização defensiva de segredos antes de expor diagnósticos ao Telegram."""

from __future__ import annotations

import re
from collections.abc import Iterable

from yt_transcriber_bot.application.config import AppSettings

_REDACTED = "[REDACTED]"

_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s]+"),
)


def sanitize_text(text: str, settings: AppSettings | None = None) -> str:
    """Remove tokens e valores sensíveis conhecidos de uma string de diagnóstico."""

    cleaned = str(text or "")
    for secret in _settings_secret_values(settings):
        cleaned = cleaned.replace(secret, _REDACTED)
    for pattern in _TOKEN_PATTERNS:
        cleaned = pattern.sub(lambda match: _keep_prefix(match), cleaned)
    return cleaned


def _settings_secret_values(settings: AppSettings | None) -> Iterable[str]:
    if settings is None:
        return ()
    values = [settings.telegram_bot_token, settings.hf_token, settings.summary_api_key]
    return tuple(value for value in values if isinstance(value, str) and len(value) >= 8)


def _keep_prefix(match: re.Match[str]) -> str:
    if match.lastindex:
        return f"{match.group(1)}{_REDACTED}"
    return _REDACTED
