"""Porta e DTO para mídia recebida pelo transporte."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class IncomingMediaKind(StrEnum):
    AUDIO = "audio"
    VOICE = "voice"
    DOCUMENT = "document"


@dataclass(frozen=True, slots=True)
class IncomingMedia:
    """Metadados já fornecidos pelo Telegram, sem classes do SDK."""

    file_id: str
    file_name: str | None
    mime_type: str | None
    size_bytes: int | None
    duration_seconds: int | None
    kind: IncomingMediaKind


class IncomingMediaDownloader(ABC):
    """Baixa uma mídia remota validada para o diretório privado local."""

    @abstractmethod
    async def download(self, media: IncomingMedia, dest_dir: Path) -> Path: ...


class AudioDurationInspector(ABC):
    """Lê a duração de arquivos cujo transporte não a informa (documents)."""

    @abstractmethod
    def duration_seconds(self, path: Path) -> int: ...
