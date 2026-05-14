"""Structured execution audit log for local, privacy-aware operations."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

_SECRET_KEY_PARTS = ("token", "secret", "api_key", "apikey", "authorization", "cookie", "password")
_PAYLOAD_KEYS = (
    "transcript",
    "text",
    "chat_payload",
    "message",
    "content",
    "body",
    "prompt",
    "response",
    "error",
)
_PAYLOAD_KEY_PATTERN = (
    r"(?:transcript|text|chat_payload|message|content|body|prompt|response|error)"
)
_VALUE_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bhf_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s;,]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s;,]+"),
    re.compile(r"(?i)(token\s*[:=]\s*)[^\s;,]+"),
    re.compile(
        r"(?i)((?:set-)?cookies?\s*[:=]\s*)(.*?)"
        r"(?=\s+(?:authorization|api[_-]?key|token)\s*[:=]"
        rf"|\s+[{{\[]?[\"']?{_PAYLOAD_KEY_PATTERN}[\"']?\s*:|$)"
    ),
)
_VALUE_PAYLOAD_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        rf"(?i)([\"']{_PAYLOAD_KEY_PATTERN}[\"']\s*:\s*)"
        r"(?:\"[^\"]*\"|'[^']*'|\{.*?\}|\[.*?\])"
    ),
    re.compile(
        rf"(?i)(\b{_PAYLOAD_KEY_PATTERN}\s*[:=]\s*)"
        rf"(.*?)(?=\s+[{{\[]?[\"']?{_PAYLOAD_KEY_PATTERN}[\"']?\s*[:=]"
        r"|\s+(?:authorization|api[_-]?key|token|(?:set-)?cookies?)\s*[:=]|$)"
    ),
)


class ExecutionAuditLogger:
    """Append-only JSONL audit logger.

    The audit file records operational lifecycle events and intentionally omits
    transcript/chat payloads while redacting likely credentials. It is meant for
    local troubleshooting, not for storing user content.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def record(self, event: str, **fields: object) -> None:
        row: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "event": event,
        }
        row.update({key: _sanitize_value(key, value) for key, value in fields.items()})
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
        with self._lock, self._path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")


def _sanitize_value(key: str, value: object) -> object:
    key_lower = key.lower()
    if any(part in key_lower for part in _SECRET_KEY_PARTS):
        return "[REDACTED]"
    if key_lower.replace("-", "_") in _PAYLOAD_KEYS:
        return "[OMITTED]"
    if isinstance(value, Mapping):
        return {str(k): _sanitize_value(str(k), v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(key, item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        return _sanitize_free_form_string(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _sanitize_free_form_string(str(value))


def _sanitize_free_form_string(value: str) -> str:
    sanitized = value
    for pattern in _VALUE_SECRET_PATTERNS:
        sanitized = pattern.sub(lambda match: _keep_prefix(match, "[REDACTED]"), sanitized)
    for pattern in _VALUE_PAYLOAD_PATTERNS:
        sanitized = pattern.sub(lambda match: _keep_prefix(match, "[OMITTED]"), sanitized)
    return sanitized


def _keep_prefix(match: re.Match[str], replacement: str) -> str:
    if match.lastindex:
        return f"{match.group(1)}{replacement}"
    return replacement
