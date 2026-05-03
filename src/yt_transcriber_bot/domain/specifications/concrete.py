"""Especificações concretas usadas para validar entradas/estados de domínio."""

from __future__ import annotations

from yt_transcriber_bot.domain.specifications.specification import Specification
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import (
    InvalidYouTubeUrlError,
    VideoId,
)


class UrlIsYoutube(Specification[str]):
    """A string fornecida contém uma URL válida do YouTube."""

    def is_satisfied_by(self, candidate: str) -> bool:
        try:
            VideoId.from_url(candidate)
        except InvalidYouTubeUrlError:
            return False
        return True


class LanguageAllowed(Specification[Language]):
    """O idioma está dentro da allowlist configurada."""

    def __init__(self, allowlist: frozenset[Language]) -> None:
        if not allowlist:
            raise ValueError("Allowlist de idiomas não pode ser vazia")
        self._allowlist = allowlist

    def is_satisfied_by(self, candidate: Language) -> bool:
        return candidate in self._allowlist


class DurationWithinLimit(Specification[Duration]):
    """A duração não excede o limite definido."""

    def __init__(self, max_duration: Duration) -> None:
        self._max_duration = max_duration

    def is_satisfied_by(self, candidate: Duration) -> bool:
        return candidate <= self._max_duration


class HasEnoughSpeech(Specification[float]):
    """A razao de fala detectada (0.0 a 1.0) esta acima do limiar."""

    def __init__(self, min_ratio: float) -> None:
        if not 0.0 <= min_ratio <= 1.0:
            raise ValueError(f"min_ratio deve estar em [0,1], recebeu {min_ratio}")
        self._min_ratio = min_ratio

    def is_satisfied_by(self, candidate: float) -> bool:
        return candidate >= self._min_ratio
