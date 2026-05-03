"""Geração de assinatura da configuração e diff humano-legível.

A assinatura captura apenas os parâmetros que afetam o resultado final da
transcrição, para que a comparação não dispare reprocessamento por mudanças
irrelevantes (ex.: nível de log, intervalo de progresso).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from yt_transcriber_bot.application.config import AppSettings

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


@dataclass(frozen=True)
class ConfigChange:
    field: str
    old_value: str
    new_value: str


def compute_config_signature(settings: AppSettings) -> str:
    """Devolve um hash determinístico dos campos significativos."""
    pairs: list[str] = []
    for field in SIGNIFICANT_FIELDS:
        if hasattr(settings, field):
            pairs.append(f"{field}={getattr(settings, field)}")
    raw = ";".join(pairs).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def describe_config(settings: AppSettings) -> dict[str, str]:
    """Expande a config significativa em um dict ``str → str`` para diff."""
    return {
        field: str(getattr(settings, field))
        for field in SIGNIFICANT_FIELDS
        if hasattr(settings, field)
    }


def diff_configs(old: dict[str, str], new: dict[str, str]) -> tuple[ConfigChange, ...]:
    """Computa as mudanças entre duas descrições de config."""
    changes: list[ConfigChange] = []
    for field in SIGNIFICANT_FIELDS:
        old_v = old.get(field, "<n/a>")
        new_v = new.get(field, "<n/a>")
        if old_v != new_v:
            changes.append(ConfigChange(field=field, old_value=old_v, new_value=new_v))
    return tuple(changes)
