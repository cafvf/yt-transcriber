"""Value object ``VideoId``.

Encapsula a extração e validação do identificador YouTube a partir de URLs
em diversos formatos (``watch``, ``youtu.be``, ``shorts``, ``embed``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

# YouTube IDs são exatamente 11 caracteres alfanuméricos + ``-_``.
_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
_URL_IN_TEXT_PATTERN = re.compile(
    r"https?://(?:www\.|m\.)?(?:youtube\.com/[^\s]+|youtu\.be/[^\s]+)",
    re.IGNORECASE,
)
_ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}


class InvalidYouTubeUrlError(ValueError):
    """A URL fornecida não é uma URL válida do YouTube."""


@dataclass(frozen=True, slots=True)
class VideoId:
    """Identificador de 11 caracteres de um vídeo do YouTube."""

    value: str

    def __post_init__(self) -> None:
        if not _VIDEO_ID_PATTERN.match(self.value):
            raise InvalidYouTubeUrlError(
                f"VideoId inválido: '{self.value}' (esperado 11 chars alfanuméricos/_-)"
            )

    @classmethod
    def from_url(cls, url: str) -> VideoId:
        """Extrai um ``VideoId`` a partir de qualquer URL do YouTube suportada.

        Aceita também strings que contenham a URL embutida em texto livre
        (por exemplo, mensagens do Telegram com texto ao redor do link).
        """
        if not isinstance(url, str) or not url.strip():
            raise InvalidYouTubeUrlError("URL vazia ou inválida")

        # Se a string contém texto além da URL, isolamos a URL primeiro.
        match = _URL_IN_TEXT_PATTERN.search(url)
        candidate = match.group(0) if match else url.strip()

        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"}:
            raise InvalidYouTubeUrlError(f"Esquema inválido: '{parsed.scheme}'")

        host = parsed.netloc.lower()
        if host not in _ALLOWED_HOSTS:
            raise InvalidYouTubeUrlError(f"Domínio não suportado: '{host}'")

        video_id = cls._extract_id(host, parsed.path, parsed.query)
        return cls(value=video_id)

    @staticmethod
    def _extract_id(host: str, path: str, query: str) -> str:
        if host == "youtu.be":
            video_id = path.lstrip("/").split("/", 1)[0]
        elif path.startswith("/watch"):
            params = parse_qs(query)
            values = params.get("v", [])
            if not values:
                raise InvalidYouTubeUrlError("Parâmetro 'v' ausente em /watch")
            video_id = values[0]
        elif path.startswith("/shorts/"):
            video_id = path[len("/shorts/") :].split("/", 1)[0]
        elif path.startswith("/embed/"):
            video_id = path[len("/embed/") :].split("/", 1)[0]
        elif path.startswith("/v/"):
            video_id = path[len("/v/") :].split("/", 1)[0]
        else:
            raise InvalidYouTubeUrlError(f"Caminho não suportado: '{path}'")

        if not _VIDEO_ID_PATTERN.match(video_id):
            raise InvalidYouTubeUrlError(f"ID extraído '{video_id}' não tem 11 chars válidos")
        return video_id

    def canonical_url(self) -> str:
        """Devolve a URL canônica ``https://www.youtube.com/watch?v=<id>``."""
        return f"https://www.youtube.com/watch?v={self.value}"

    def __str__(self) -> str:
        return self.value
