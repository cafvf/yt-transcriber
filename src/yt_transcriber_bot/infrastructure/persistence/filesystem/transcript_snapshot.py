"""Persistência canônica e versionada de transcrição estruturada."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptCorruptError,
    CanonicalTranscriptRecord,
    CanonicalTranscriptStore,
    TranscriptRenderContext,
)
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import Transcript, TranscriptSegment
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance
from yt_transcriber_bot.domain.value_objects.video_id import VideoId

SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1


TranscriptSnapshot = CanonicalTranscriptRecord


class TranscriptSnapshotRepository(CanonicalTranscriptStore):
    """Salva/carrega snapshots JSON por referência canônica explícita."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def path_for(self, reference: str) -> Path:
        return self._base_dir / f"{reference}.json"

    def persist(self, reference: str, record: CanonicalTranscriptRecord) -> None:
        self.save(reference, record)

    def save(self, reference: str, snapshot: TranscriptSnapshot) -> Path:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(reference)
        tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            tmp.write_text(
                json.dumps(self._encode(snapshot), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
        return path

    def delete(self, reference: str) -> None:
        self.path_for(reference).unlink(missing_ok=True)

    def load(self, reference: str) -> TranscriptSnapshot | None:
        path = self.path_for(reference)
        if not path.is_file():
            return None
        try:
            return self._decode(self._read_json(path))
        except CanonicalTranscriptCorruptError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise CanonicalTranscriptCorruptError(
                "snapshot inválido: estrutura canônica corrompida"
            ) from exc

    def load_reference(self, reference: str) -> TranscriptSnapshot | None:
        return self.load(reference)

    def load_metadata(self, reference: str) -> MediaMetadata | None:
        path = self.path_for(reference)
        if not path.is_file():
            return None
        data = self._read_json(path)
        raw_metadata = data.get("metadata")
        if not isinstance(raw_metadata, dict):
            raise CanonicalTranscriptCorruptError("snapshot inválido: metadata deve ser um objeto")
        try:
            return self._decode_metadata(raw_metadata)
        except CanonicalTranscriptCorruptError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise CanonicalTranscriptCorruptError("snapshot inválido: metadata corrompida") from exc

    def load_metadata_many(self, references: tuple[str, ...]) -> dict[str, MediaMetadata]:
        metadata: dict[str, MediaMetadata] = {}
        for reference in references:
            loaded = self.load_metadata(reference)
            if loaded is not None:
                metadata[reference] = loaded
        return metadata

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CanonicalTranscriptCorruptError("snapshot inválido: JSON malformado") from exc
        if not isinstance(data, dict):
            raise CanonicalTranscriptCorruptError("snapshot inválido: JSON raiz deve ser um objeto")
        return data

    @staticmethod
    def _encode(snap: TranscriptSnapshot) -> dict[str, object]:
        m = snap.metadata
        t = snap.transcript
        c = snap.context
        metadata: dict[str, object] = {
            "title": m.title,
            "channel": m.channel,
            "duration_seconds": m.duration.total_seconds if m.duration else None,
            "upload_date": m.upload_date.isoformat() if m.upload_date else None,
            "original_language": m.original_language.code if m.original_language else None,
            "has_alternate_audio_tracks": m.has_alternate_audio_tracks,
            "alternate_languages": [lng.code for lng in m.alternate_languages],
            "source_label": m.source_label,
        }
        if m.source_label == "YouTube":
            metadata["video_id"] = str(m.video_id)
            if m.source_reference is not None:
                metadata["source_reference"] = m.source_reference
        return {
            "schema_version": SCHEMA_VERSION,
            "metadata": metadata,
            "transcript": {
                "language": t.language.code if t.language else None,
                "language_confidence": t.language_confidence,
                "language_source": t.language_source.value,
                "requested_language": (t.requested_language.code if t.requested_language else None),
                "observed_language": (t.observed_language.code if t.observed_language else None),
                "observed_language_confidence": t.observed_language_confidence,
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
            "processing": {
                "fingerprint": snap.processing_fingerprint,
                "provenance": snap.processing_provenance.as_dict(),
            },
        }

    @staticmethod
    def _decode(data: dict[str, object]) -> TranscriptSnapshot:
        version = data.get("schema_version")
        if version not in {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION}:
            raise CanonicalTranscriptCorruptError(f"schema_version não suportado: {version}")
        m_raw = data.get("metadata")
        t_raw = data.get("transcript")
        c_raw = data.get("context")
        if not (isinstance(m_raw, dict) and isinstance(t_raw, dict) and isinstance(c_raw, dict)):
            raise CanonicalTranscriptCorruptError(
                "snapshot inválido: metadata/transcript/context devem ser dicts"
            )
        metadata = TranscriptSnapshotRepository._decode_metadata(m_raw)
        raw_segments = t_raw.get("segments")
        if not isinstance(raw_segments, list):
            raise ValueError("transcript.segments deve ser uma lista")
        segments = _decode_segments(raw_segments)
        language = _decode_language(t_raw.get("language"))
        confidence = _decode_optional_confidence(t_raw.get("language_confidence"))
        if version == LEGACY_SCHEMA_VERSION:
            language_source = LanguageSource.UNKNOWN
            requested_language = None
            observed_language = None
            observed_confidence = None
            fingerprint = ""
            provenance = ProcessingProvenance.unknown()
        else:
            try:
                language_source = LanguageSource(str(t_raw.get("language_source", "unknown")))
            except ValueError:
                language_source = LanguageSource.UNKNOWN
            requested_language = _decode_language(t_raw.get("requested_language"))
            observed_language = _decode_language(t_raw.get("observed_language"))
            observed_confidence = _decode_optional_confidence(
                t_raw.get("observed_language_confidence")
            )
            processing = data.get("processing")
            if isinstance(processing, dict):
                fingerprint = str(processing.get("fingerprint") or "")
                provenance = ProcessingProvenance.from_dict(processing.get("provenance"))
            else:
                fingerprint = ""
                provenance = ProcessingProvenance.unknown()
        transcript = Transcript(
            segments=segments,
            language=language,
            language_confidence=confidence,
            source=str(t_raw.get("source", "whisperx")),
            requested_language=requested_language,
            observed_language=observed_language,
            observed_language_confidence=observed_confidence,
            language_source=language_source,
        )
        context = TranscriptRenderContext(
            rendered_at=datetime.fromisoformat(str(c_raw["rendered_at"])),
            whisper_model=str(c_raw["whisper_model"]),
            diarization_model=str(c_raw["diarization_model"]),
            transcription_source=str(c_raw["transcription_source"]),
        )
        return TranscriptSnapshot(
            metadata=metadata,
            transcript=transcript,
            context=context,
            processing_fingerprint=fingerprint,
            processing_provenance=provenance,
        )

    @staticmethod
    def _decode_metadata(raw: dict[str, object]) -> MediaMetadata:
        upload = raw.get("upload_date")
        original_lang = raw.get("original_language")
        alt_langs = raw.get("alternate_languages", [])
        if not isinstance(alt_langs, list):
            alt_langs = []
        source_label = str(raw.get("source_label", "YouTube"))
        raw_video_id = raw.get("video_id")
        duration_raw = raw.get("duration_seconds")
        if isinstance(duration_raw, bool) or not isinstance(duration_raw, (str, int, float)):
            duration_seconds = None
        else:
            try:
                duration_seconds = float(duration_raw)
            except ValueError:
                duration_seconds = None
        duration = (
            Duration.from_seconds(duration_seconds)
            if duration_seconds is not None and duration_seconds > 0
            else None
        )
        return MediaMetadata(
            video_id=VideoId(str(raw_video_id)) if raw_video_id else None,
            title=str(raw["title"]),
            channel=str(raw["channel"]),
            duration=duration,
            upload_date=date.fromisoformat(str(upload)) if upload else None,
            original_language=Language(str(original_lang)) if original_lang else None,
            has_alternate_audio_tracks=bool(raw.get("has_alternate_audio_tracks", False)),
            alternate_languages=tuple(Language(str(code)) for code in alt_langs),
            source_label=source_label,
            source_reference=(
                str(raw["source_reference"])
                if source_label == "YouTube" and raw.get("source_reference")
                else None
            ),
        )


def _decode_language(value: object) -> Language | None:
    if value is None or not str(value).strip():
        return None
    return Language(str(value))


def _decode_optional_confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        confidence = float(value)
    except ValueError:
        return None
    return confidence if 0.0 <= confidence <= 1.0 else None


def _decode_segments(raw_segments: list[object]) -> tuple[TranscriptSegment, ...]:
    segments: list[TranscriptSegment] = []
    for raw in raw_segments:
        if not isinstance(raw, dict):
            continue
        try:
            start = float(raw["start"])
            end = float(raw["end"])
            text = str(raw["text"])
            speaker = str(raw["speaker"])
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start or not text or not speaker:
            continue
        segments.append(
            TranscriptSegment(
                start_seconds=start,
                end_seconds=end,
                text=text,
                speaker_label=speaker,
            )
        )
    return tuple(segments)
