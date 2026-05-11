"""Exportação de snapshots de transcrição para JSON, SRT e VTT.

Os exportadores trabalham sobre ``TranscriptSnapshot`` já persistido. Assim,
artefatos derivados podem ser gerados para vídeos antigos sem reprocessar áudio,
WhisperX ou diarização.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from yt_transcriber_bot.domain.entities.transcript import TranscriptSegment
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.text.normalization import normalize_artifact_text

ExportFormat = Literal["json", "srt", "vtt"]
SUPPORTED_EXPORT_FORMATS: tuple[ExportFormat, ...] = ("json", "srt", "vtt")


@dataclass(frozen=True)
class ExportResult:
    """Resultado de uma exportação de transcrição."""

    format: ExportFormat
    path: Path


class TranscriptExportService:
    """Exporta uma transcrição persistida em formatos interoperáveis."""

    def __init__(self, snapshots: TranscriptSnapshotRepository) -> None:
        self._snapshots = snapshots

    def export(
        self,
        *,
        slug: str,
        output_base_path: Path,
        format: str,
        speaker_aliases: Mapping[str, str] | None = None,
    ) -> ExportResult:
        fmt = _normalize_format(format)
        snap = self._snapshots.load(slug)
        if snap is None:
            raise FileNotFoundError(f"Snapshot inexistente: {slug}")
        aliases = {k: v.strip() for k, v in dict(speaker_aliases or {}).items() if v.strip()}
        output_path = output_base_path.with_suffix(f".{fmt}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            output_path.write_text(_render_json(snap, aliases), encoding="utf-8")
        elif fmt == "srt":
            output_path.write_text(_render_srt(snap, aliases), encoding="utf-8")
        elif fmt == "vtt":
            output_path.write_text(_render_vtt(snap, aliases), encoding="utf-8")
        else:  # pragma: no cover - protegido por _normalize_format
            raise ValueError(f"Formato não suportado: {format}")
        return ExportResult(format=fmt, path=output_path)


def _normalize_format(value: str) -> ExportFormat:
    fmt = value.strip().lower().lstrip(".")
    if fmt not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError(
            "Formato de exportação inválido. Use um de: "
            + ", ".join(SUPPORTED_EXPORT_FORMATS)
            + "."
        )
    return fmt  # type: ignore[return-value]


def _display_speaker(label: str, aliases: Mapping[str, str]) -> str:
    alias = aliases.get(label, "").strip()
    return alias or label


def _clean_caption_text(text: str) -> str:
    return normalize_artifact_text(text)


def _render_json(snap: TranscriptSnapshot, aliases: Mapping[str, str]) -> str:
    m = snap.metadata
    t = snap.transcript
    c = snap.context
    data = {
        "schema_version": 1,
        "format": "yt_transcriber_bot.transcript_export",
        "metadata": {
            "video_id": str(m.video_id),
            "url": m.canonical_url(),
            "title": m.title,
            "channel": m.channel,
            "duration_seconds": m.duration.total_seconds,
            "duration_hms": m.duration.to_hms(),
            "upload_date": m.upload_date.isoformat() if m.upload_date else None,
            "original_language": m.original_language.code if m.original_language else None,
            "has_alternate_audio_tracks": m.has_alternate_audio_tracks,
            "alternate_languages": [lang.code for lang in m.alternate_languages],
        },
        "transcript": {
            "language": t.language.code,
            "language_confidence": t.language_confidence,
            "source": t.source,
            "speaker_aliases": dict(aliases),
            "segments": [
                {
                    "index": idx,
                    "start_seconds": seg.start_seconds,
                    "end_seconds": seg.end_seconds,
                    "start": _format_timestamp_vtt(seg.start_seconds),
                    "end": _format_timestamp_vtt(seg.end_seconds),
                    "speaker_label": seg.speaker_label,
                    "speaker": _display_speaker(seg.speaker_label, aliases),
                    "text": _clean_caption_text(seg.text),
                }
                for idx, seg in enumerate(_valid_segments(t.segments), start=1)
            ],
        },
        "render_context": {
            "rendered_at": c.rendered_at.isoformat(),
            "whisper_model": c.whisper_model,
            "diarization_model": c.diarization_model,
            "transcription_source": c.transcription_source,
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _render_srt(snap: TranscriptSnapshot, aliases: Mapping[str, str]) -> str:
    blocks: list[str] = []
    for idx, seg in enumerate(_valid_segments(snap.transcript.segments), start=1):
        speaker = _display_speaker(seg.speaker_label, aliases)
        text = _clean_caption_text(seg.text)
        blocks.append(
            f"{idx}\n"
            f"{_format_timestamp_srt(seg.start_seconds)} --> {_format_timestamp_srt(seg.end_seconds)}\n"
            f"{speaker}: {text}"
        )
    return "\n\n".join(blocks).rstrip() + "\n"


def _render_vtt(snap: TranscriptSnapshot, aliases: Mapping[str, str]) -> str:
    blocks = ["WEBVTT", ""]
    for seg in _valid_segments(snap.transcript.segments):
        speaker = _display_speaker(seg.speaker_label, aliases)
        text = _clean_caption_text(seg.text)
        blocks.append(
            f"{_format_timestamp_vtt(seg.start_seconds)} --> {_format_timestamp_vtt(seg.end_seconds)}\n"
            f"{speaker}: {text}"
        )
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def _valid_segments(segments: tuple[TranscriptSegment, ...]) -> tuple[TranscriptSegment, ...]:
    return tuple(
        seg for seg in segments if seg.text.strip() and seg.end_seconds > seg.start_seconds
    )


def _format_timestamp_srt(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
