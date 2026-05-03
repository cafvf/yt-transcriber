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
        path.write_text(json.dumps(self._encode(snapshot), ensure_ascii=False, indent=2))
        return path

    def load(self, slug: str) -> TranscriptSnapshot | None:
        path = self.path_for(slug)
        if not path.is_file():
            return None
        data = json.loads(path.read_text())
        return self._decode(data)

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------

    @staticmethod
    def _encode(snap: TranscriptSnapshot) -> dict[str, object]:
        m = snap.metadata
        t = snap.transcript
        c = snap.context
        return {
            "schema_version": SCHEMA_VERSION,
            "metadata": {
                "video_id": str(m.video_id),
                "title": m.title,
                "channel": m.channel,
                "duration_seconds": m.duration.total_seconds,
                "upload_date": m.upload_date.isoformat() if m.upload_date else None,
                "original_language": m.original_language.code if m.original_language else None,
                "has_alternate_audio_tracks": m.has_alternate_audio_tracks,
                "alternate_languages": [lng.code for lng in m.alternate_languages],
            },
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

        upload = m["upload_date"]
        original_lang = m["original_language"]
        alt_langs = m.get("alternate_languages", [])
        if not isinstance(alt_langs, list):
            alt_langs = []
        metadata = VideoMetadata(
            video_id=VideoId(str(m["video_id"])),
            title=str(m["title"]),
            channel=str(m["channel"]),
            duration=Duration.from_seconds(float(m["duration_seconds"])),  # type: ignore[arg-type]
            upload_date=date.fromisoformat(str(upload)) if upload else None,
            original_language=Language(str(original_lang)) if original_lang else None,
            has_alternate_audio_tracks=bool(m["has_alternate_audio_tracks"]),
            alternate_languages=tuple(Language(str(code)) for code in alt_langs),
        )
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
