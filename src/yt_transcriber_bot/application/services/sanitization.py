"""Central defensive sanitization for private operational disclosure paths."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

from yt_transcriber_bot.application.config import AppSettings

_REDACTED = "[REDACTED]"
_OMITTED = "[OMITTED]"
_PRIVATE_PATH = "[PRIVATE PATH]"
_PRIVATE_IDENTIFIER = "[PRIVATE IDENTIFIER]"
_SAFE_FALLBACK = "[SAFE ERROR DETAIL OMITTED]"

_SECRET_KEY_PARTS = (
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
)
_PAYLOAD_KEYS = {
    "transcript",
    "text",
    "chat_payload",
    "message",
    "content",
    "body",
    "prompt",
    "response",
    "request_body",
    "response_body",
}

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
)

_VALUE_PREFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?im)\b(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
    re.compile(
        r"(?im)\b(authorization\s*[:=]\s*)(?!bearer\b)"
        r"((?:(?:basic|token|digest)\s+)?[^\s,;]+)"
    ),
    re.compile(
        r"(?im)\b((?:set-cookie|cookies?)\s*[:=]\s*)(.*?)"
        r"(?=\s+[\{\[]?[\"\']?(?:authorization|api[_-]?key|token|secret|password|"
        r"body|messages|prompt|user_prompt|system_prompt|content|input|transcript|chat_payload|"
        r"text|message|response|request_body|response_body)[\"\']?\s*[:=]|$)"
    ),
    re.compile(r"(?im)\b((?:x-)?api[_-]?key\s*[:=]\s*)([^\s,;]+)"),
    re.compile(
        r"""(?im)(["'](?:authorization|api[_-]?key|token|secret|password|cookie)["']\s*:\s*)(["'][^"']*["']|[^,\r\n}]+)"""
    ),
    re.compile(
        r"(?im)\b((?:[A-Z0-9]+_)*(?:TOKEN|KEY|SECRET|PASSWORD|COOKIE)(?:_[A-Z0-9]+)*\s*=\s*)([^\s#]+)"
    ),
    re.compile(r"(?i)([?&](?:token|api[_-]?key|key|access[_-]?token)=)([^&\s]+)"),
)

_PAYLOAD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"""(?is)(["']?messages["']?\s*[:=]\s*)(\[[^\]]*]|\{[^}]*}|"[^"]*"|'[^']*')"""),
    re.compile(
        r"""(?is)(["']?(?:prompt|user_prompt|system_prompt|content|input|transcript|chat_payload|text|message|response|request_body|response_body|body)["']?\s*[:=]\s*)("[^"]*"|'[^']*'|[^,\r\n}]+)"""
    ),
)

_NETSCAPE_COOKIE_PATTERN = re.compile(r"(?im)^([^\t\r\n]+(?:\t+[^\t\r\n]+){5}\t+)([^\t\r\n]+)$")


def sanitize_text(text: str, settings: AppSettings | None = None) -> str:
    """Remove secrets and echoed private payloads from diagnostic text.

    Sanitization is itself a security boundary. If an unexpected sanitization
    failure occurs, raw input is never returned to the caller.
    """

    try:
        return _sanitize_text(text, settings)
    except Exception:
        return _SAFE_FALLBACK


def sanitize_value(
    key: str,
    value: object,
    settings: AppSettings | None = None,
) -> object:
    """Sanitize one structured operational/audit value with shared policy."""

    try:
        return _sanitize_value(key, value, settings)
    except Exception:
        return _SAFE_FALLBACK


def _sanitize_text(text: str, settings: AppSettings | None) -> str:
    cleaned = str(text or "")
    if settings is not None and settings.telegram_allowed_user_id > 0:
        user_id = re.escape(str(settings.telegram_allowed_user_id))
        cleaned = re.sub(
            rf"(?i)(\b(?:user_id|chat_id)\s*[:=]\s*){user_id}\b",
            rf"\1{_PRIVATE_IDENTIFIER}",
            cleaned,
        )
    for private_path in _settings_private_paths(settings):
        rendered = str(private_path)
        if rendered:
            cleaned = re.sub(
                re.escape(rendered) + r"[^\s,;]*",
                _PRIVATE_PATH,
                cleaned,
            )
    for secret in _settings_secret_values(settings):
        cleaned = cleaned.replace(secret, _REDACTED)
    for pattern in _PAYLOAD_PATTERNS:
        cleaned = pattern.sub(_keep_prefix_omitted, cleaned)
    for pattern in _VALUE_PREFIX_PATTERNS:
        cleaned = pattern.sub(_keep_prefix_redacted, cleaned)
    cleaned = _NETSCAPE_COOKIE_PATTERN.sub(_keep_prefix_redacted, cleaned)
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub(_REDACTED, cleaned)
    return cleaned


def _sanitize_value(key: str, value: object, settings: AppSettings | None) -> object:
    normalized_key = key.lower().replace("-", "_")
    if any(part in normalized_key for part in _SECRET_KEY_PARTS):
        return _REDACTED
    if normalized_key in _PAYLOAD_KEYS:
        return _OMITTED
    if normalized_key in {"user_id", "chat_id", "telegram_user_id", "telegram_chat_id"}:
        return _PRIVATE_IDENTIFIER
    if isinstance(value, Mapping):
        return {
            str(nested_key): _sanitize_value(str(nested_key), nested_value, settings)
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(key, item, settings) for item in value]
    if isinstance(value, Path):
        return _PRIVATE_PATH
    if isinstance(value, str):
        if _looks_like_path_key(normalized_key):
            return _PRIVATE_PATH
        return _sanitize_text(value, settings)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _sanitize_text(str(value), settings)


def _looks_like_path_key(normalized_key: str) -> bool:
    return normalized_key in {
        "path",
        "file",
        "files",
        "directory",
        "dir",
    } or normalized_key.endswith(("_path", "_paths", "_file", "_files", "_directory", "_dir"))


def _settings_private_paths(settings: AppSettings | None) -> tuple[Path, ...]:
    if settings is None:
        return ()
    paths = {
        settings.base_dir,
        settings.db_path,
        settings.models_dir,
        settings.downloads_dir(),
        settings.processed_dir(),
        settings.transcripts_dir(),
        settings.logs_dir(),
        settings.summaries_dir(),
        settings.video_exports_dir(),
    }
    cookie_file = settings.youtube_cookies_file.strip()
    if cookie_file:
        paths.add(Path(cookie_file).expanduser())
    resolved: list[Path] = []
    for path in paths:
        candidate = path.expanduser().resolve(strict=False)
        if candidate not in resolved:
            resolved.append(candidate)
    return tuple(sorted(resolved, key=lambda item: len(str(item)), reverse=True))


def _settings_secret_values(settings: AppSettings | None) -> Iterable[str]:
    if settings is None:
        return ()
    values = [settings.telegram_bot_token, settings.hf_token, settings.summary_api_key]
    return tuple(value for value in values if isinstance(value, str) and len(value.strip()) >= 8)


def _keep_prefix_redacted(match: re.Match[str]) -> str:
    return _keep_prefix(match, _REDACTED)


def _keep_prefix_omitted(match: re.Match[str]) -> str:
    return _keep_prefix(match, _OMITTED)


def _keep_prefix(match: re.Match[str], replacement: str) -> str:
    if match.lastindex:
        return f"{match.group(1)}{replacement}"
    return replacement
