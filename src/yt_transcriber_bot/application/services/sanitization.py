"""Sanitização defensiva de segredos antes de expor diagnósticos ao Telegram."""

from __future__ import annotations

import re
from collections.abc import Iterable

from yt_transcriber_bot.application.config import AppSettings

_REDACTED = "[REDACTED]"

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
)

_VALUE_PREFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?im)\b(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
    re.compile(r"(?im)\b(authorization\s*[:=]\s*)([^\r\n]+)"),
    re.compile(r"(?im)\b((?:set-cookie|cookie)\s*[:=]\s*)([^\r\n]+)"),
    re.compile(r"(?im)\b((?:x-)?api[_-]?key\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?im)\b((?:request[_-]?|response[_-]?)?body\s*[:=]\s*)([^\r\n]+)"),
    re.compile(
        r"""(?im)(["']?(?:authorization|api[_-]?key|token|secret|password|cookie)["']?\s*:\s*)(["'][^"']*["']|[^,\r\n}]+)"""
    ),
    re.compile(
        r"(?im)\b((?:[A-Z0-9]+_)*(?:TOKEN|KEY|SECRET|PASSWORD|COOKIE)(?:_[A-Z0-9]+)*\s*=\s*)([^\s#]+)"
    ),
    re.compile(r"(?i)([?&](?:token|api[_-]?key|key|access[_-]?token)=)([^&\s]+)"),
)

_PAYLOAD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"""(?is)(["']?messages["']?\s*[:=]\s*)(\[[^\]]*]|\{[^}]*}|"[^"]*"|'[^']*')"""),
    re.compile(
        r"""(?is)(["']?(?:prompt|user_prompt|system_prompt|content|input|transcript|request_body|response_body)["']?\s*[:=]\s*)("[^"]*"|'[^']*'|[^,\r\n}]+)"""
    ),
)

_NETSCAPE_COOKIE_PATTERN = re.compile(r"(?im)^([^\t\r\n]+(?:\t+[^\t\r\n]+){5}\t+)([^\t\r\n]+)$")


def sanitize_text(text: str, settings: AppSettings | None = None) -> str:
    """Remove tokens e valores sensíveis conhecidos de uma string de diagnóstico."""

    cleaned = str(text or "")
    for secret in _settings_secret_values(settings):
        cleaned = cleaned.replace(secret, _REDACTED)
    for pattern in _PAYLOAD_PATTERNS:
        cleaned = pattern.sub(_keep_prefix, cleaned)
    for pattern in _VALUE_PREFIX_PATTERNS:
        cleaned = pattern.sub(_keep_prefix, cleaned)
    cleaned = _NETSCAPE_COOKIE_PATTERN.sub(_keep_prefix, cleaned)
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub(_REDACTED, cleaned)
    return cleaned


def _settings_secret_values(settings: AppSettings | None) -> Iterable[str]:
    if settings is None:
        return ()
    values = [settings.telegram_bot_token, settings.hf_token, settings.summary_api_key]
    return tuple(value for value in values if isinstance(value, str) and len(value.strip()) >= 8)


def _keep_prefix(match: re.Match[str]) -> str:
    if match.lastindex:
        return f"{match.group(1)}{_REDACTED}"
    return _REDACTED
