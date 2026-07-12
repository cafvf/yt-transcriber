"""Persistência do snapshot de uma transcrição (segments + metadata + ctx).

Permite re-renderizar o MD após renomear falantes em um vídeo legado, mesmo
após o áudio comprimido ter sido expurgado pela política FIFO.

Formato: JSON simples e estável, versionado pelo campo ``schema_version``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from yt_transcriber_bot.domain.entities.transcript import (
    Transcript,
    TranscriptSegment,
)
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    RenderContext,
)

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TranscriptSnapshot:
    metadata: VideoMetadata
    transcript: Transcript
    context: RenderContext


class TranscriptSnapshotRepository:
    """Salva/carrega snapshots em JSON dentro de ``segments_dir``."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def path_for(self, slug: str) -> Path:
        return self._base_dir / f"{slug}.json"

    def save(self, slug: str, snapshot: TranscriptSnapshot) -> Path:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(slug)
        path.write_text(
            json.dumps(self._encode(snapshot), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, slug: str) -> TranscriptSnapshot | None:
        path = self.path_for(slug)
        if not path.is_file():
            return None
        data = self._read_json(path)
        return self._decode(data)

    def load_metadata(self, slug: str) -> VideoMetadata | None:
        path = self.path_for(slug)
        if not path.is_file():
            return None
        data = self._read_json(path)
        raw_metadata = data.get("metadata")
        if not isinstance(raw_metadata, dict):
            raise ValueError("snapshot inválido: metadata deve ser um objeto")
        return self._decode_metadata(raw_metadata)

    def load_metadata_many(self, slugs: tuple[str, ...]) -> dict[str, VideoMetadata]:
        metadata: dict[str, VideoMetadata] = {}
        for slug in slugs:
            loaded = self.load_metadata(slug)
            if loaded is not None:
                metadata[slug] = loaded
        return metadata

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("snapshot inválido: JSON raiz deve ser um objeto")
        return data

    @staticmethod
    def _encode(snap: TranscriptSnapshot) -> dict[str, object]:
        m = snap.metadata
        t = snap.transcript
        c = snap.context
        metadata: dict[str, object] = {
            "title": m.title,
            "channel": m.channel,
            "duration_seconds": m.duration.total_seconds,
            "upload_date": m.upload_date.isoformat() if m.upload_date else None,
            "original_language": m.original_language.code if m.original_language else None,
            "has_alternate_audio_tracks": m.has_alternate_audio_tracks,
            "alternate_languages": [lng.code for lng in m.alternate_languages],
            "source_label": m.source_label,
        }
        if m.source_label == "YouTube":
            metadata["video_id"] = str(m.video_id)
            metadata["source_reference"] = m.source_reference
        return {
            "schema_version": SCHEMA_VERSION,
            "metadata": metadata,
            "transcript": {
                "language": t.language.code,
                "language_confidence": t.language_confidence,
                "source": t.source,
                "segments": [
                    {
                        "start": s.start_seconds,
                        "end": s.end_seconds,
                        "text": s.text,
                        "speaker": s.speaker_label,
                    }
                    for s in t.segments
                ],
            },
            "context": {
                "rendered_at": c.rendered_at.isoformat(),
                "whisper_model": c.whisper_model,
                "diarization_model": c.diarization_model,
                "transcription_source": c.transcription_source,
            },
        }

    @staticmethod
    def _decode(data: dict[str, object]) -> TranscriptSnapshot:
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(f"schema_version não suportado: {version}")
        m_raw = data["metadata"]
        t_raw = data["transcript"]
        c_raw = data["context"]
        if not (isinstance(m_raw, dict) and isinstance(t_raw, dict) and isinstance(c_raw, dict)):
            raise ValueError("snapshot inválido: metadata/transcript/context devem ser dicts")
        m: dict[str, object] = m_raw
        t: dict[str, object] = t_raw
        c: dict[str, object] = c_raw

        metadata = TranscriptSnapshotRepository._decode_metadata(m)
        raw_segments = t["segments"]
        if not isinstance(raw_segments, list):
            raise ValueError("transcript.segments deve ser uma lista")
        segments = tuple(
            TranscriptSegment(
                start_seconds=float(s["start"]),
                end_seconds=float(s["end"]),
                text=str(s["text"]),
                speaker_label=str(s["speaker"]),
            )
            for s in raw_segments
        )
        transcript = Transcript(
            segments=segments,
            language=Language(str(t["language"])),
            language_confidence=float(t["language_confidence"]),  # type: ignore[arg-type]
            source=str(t["source"]),
        )
        context = RenderContext(
            rendered_at=datetime.fromisoformat(str(c["rendered_at"])),
            whisper_model=str(c["whisper_model"]),
            diarization_model=str(c["diarization_model"]),
            transcription_source=str(c["transcription_source"]),
        )
        return TranscriptSnapshot(metadata=metadata, transcript=transcript, context=context)

    @staticmethod
    def _decode_metadata(raw: dict[str, object]) -> VideoMetadata:
        upload = raw["upload_date"]
        original_lang = raw["original_language"]
        alt_langs = raw.get("alternate_languages", [])
        if not isinstance(alt_langs, list):
            alt_langs = []
        source_label = str(raw.get("source_label", "YouTube"))
        raw_video_id = raw.get("video_id")
        return VideoMetadata(
            video_id=VideoId(str(raw_video_id)) if raw_video_id else None,
            title=str(raw["title"]),
            channel=str(raw["channel"]),
            duration=Duration.from_seconds(float(raw["duration_seconds"])),  # type: ignore[arg-type]
            upload_date=date.fromisoformat(str(upload)) if upload else None,
            original_language=Language(str(original_lang)) if original_lang else None,
            has_alternate_audio_tracks=bool(raw["has_alternate_audio_tracks"]),
            alternate_languages=tuple(Language(str(code)) for code in alt_langs),
            source_label=source_label,
            source_reference=(
                str(raw["source_reference"])
                if source_label == "YouTube" and raw.get("source_reference")
                else None
            ),
        )
