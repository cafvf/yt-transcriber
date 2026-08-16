"""Exportação de texto limpo a partir de snapshots de transcrição.

O serviço gera um artefato ``.txt`` reutilizável; ele nunca aciona download,
ASR ou diarização.  Mantê-lo ao lado dos demais exportadores deixa a decisão
de transporte (Telegram) fora desta colaboração de persistência e renderização.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptRecord,
    CanonicalTranscriptStore,
)
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    _display_speaker,
    _valid_segments,
)
from yt_transcriber_bot.infrastructure.text.normalization import normalize_artifact_text


@dataclass(frozen=True)
class PlainTextExportResult:
    """Artefato ``.txt`` derivado de um snapshot persistido."""

    path: Path


class PlainTextTranscriptExportService:
    """Renderiza texto simples, sanitizado e legível de uma transcrição salva."""

    def __init__(self, snapshots: CanonicalTranscriptStore) -> None:
        self._snapshots = snapshots

    def export(
        self,
        *,
        slug: str,
        output_base_path: Path,
        speaker_aliases: Mapping[str, str] | None = None,
    ) -> PlainTextExportResult:
        snapshot = self._snapshots.load(slug)
        if snapshot is None:
            raise FileNotFoundError(f"Snapshot inexistente: {slug}")
        aliases = {
            key: value.strip()
            for key, value in dict(speaker_aliases or {}).items()
            if value.strip()
        }
        output_path = output_base_path.with_suffix(".txt")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_render_plain_text(snapshot, aliases), encoding="utf-8")
        return PlainTextExportResult(path=output_path)


def _render_plain_text(snapshot: CanonicalTranscriptRecord, aliases: Mapping[str, str]) -> str:
    """Representa metadados mínimos e segmentos válidos, sem Markdown."""
    metadata = snapshot.metadata
    transcript = snapshot.transcript
    language = transcript.language.code if transcript.language else "desconhecido"
    lines = [
        f"Título: {normalize_artifact_text(metadata.title)}",
        f"Canal: {normalize_artifact_text(metadata.channel)}",
        f"Idioma: {language}",
        "",
    ]
    if metadata.source_label == "YouTube":
        lines[2:2] = [f"Vídeo: {metadata.video_id}", f"URL: {metadata.canonical_url()}"]
    else:
        lines[2:2] = [f"Origem: {metadata.source_label}"]
    for segment in _valid_segments(transcript.segments):
        speaker = _display_speaker(segment.speaker_label, aliases)
        text = _clean_plain_text(segment.text)
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines).rstrip() + "\n"


def _clean_plain_text(text: str) -> str:
    """Remove marcadores Markdown comuns após a normalização compartilhada."""
    cleaned = normalize_artifact_text(text)
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned)
    return cleaned.replace("**", "").replace("__", "").replace("`", "").strip()
