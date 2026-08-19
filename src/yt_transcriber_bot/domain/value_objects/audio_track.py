"""Taxonomia da faixa de áudio efetivamente selecionada."""

from __future__ import annotations

from enum import StrEnum


class AudioTrackSelection(StrEnum):
    """Classificação baseada na evidência disponível durante a aquisição."""

    ORIGINAL = "original"
    DEFAULT = "default"
    UNKNOWN = "unknown"
