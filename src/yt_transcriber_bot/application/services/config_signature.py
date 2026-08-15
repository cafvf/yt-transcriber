"""Único mecanismo canônico de fingerprint de processamento."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yt_transcriber_bot.application.config import AppSettings

PROCESSING_FINGERPRINT_VERSION = 1

# Apenas parâmetros de configuração que podem alterar o resultado/evidência.
SIGNIFICANT_FIELDS: tuple[str, ...] = (
    "whisper_model",
    "whisper_model_pt",
    "whisper_model_en",
    "whisper_model_default",
    "device",
    "compute_type",
    "audio_bitrate_kbps",
    "audio_sample_rate_hz",
    "allowed_languages",
    "prefer_youtube_subtitles",
)

_FIXED_PROCESSING_POLICY: dict[str, str | int] = {
    "fingerprint_version": PROCESSING_FINGERPRINT_VERSION,
    "asr_backend": "whisperx",
    "diarization_policy": "whisperx_then_pyannote",
    "transcript_normalization": "normalize_artifact_text:v1",
    "snapshot_schema": 2,
}


@dataclass(frozen=True)
class ConfigChange:
    field: str
    old_value: str
    new_value: str


def processing_fingerprint_payload(
    settings: AppSettings,
    *,
    requested_language: str | None = None,
    source_type: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = dict(_FIXED_PROCESSING_POLICY)
    payload["requested_language"] = (requested_language or "").strip().lower() or None
    payload["source_type"] = (source_type or "").strip().lower() or None
    for field in SIGNIFICANT_FIELDS:
        value = getattr(settings, field)
        payload[field] = list(value) if isinstance(value, tuple) else value
    return payload


def compute_processing_fingerprint(
    settings: AppSettings,
    *,
    requested_language: str | None = None,
    source_type: str | None = None,
) -> str:
    raw = json.dumps(
        processing_fingerprint_payload(
            settings, requested_language=requested_language, source_type=source_type
        ),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def compute_config_signature(settings: AppSettings) -> str:
    """Nome de compatibilidade; delega ao único fingerprint canônico."""

    return compute_processing_fingerprint(settings)


def describe_config(settings: AppSettings) -> dict[str, str]:
    return {field: str(getattr(settings, field)) for field in SIGNIFICANT_FIELDS}


def diff_configs(old: dict[str, str], new: dict[str, str]) -> tuple[ConfigChange, ...]:
    changes: list[ConfigChange] = []
    for field in SIGNIFICANT_FIELDS:
        old_v = old.get(field, "<n/a>")
        new_v = new.get(field, "<n/a>")
        if old_v != new_v:
            changes.append(ConfigChange(field=field, old_value=old_v, new_value=new_v))
    return tuple(changes)
