"""Contexto mutável e exclusivo de uma execução do pipeline."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from yt_transcriber_bot.application.ports.transcription_engine import TranscribedSegment
from yt_transcriber_bot.application.runtime_selection import RuntimePlan
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import Transcript
from yt_transcriber_bot.domain.value_objects.audio_track import AudioTrackSelection
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance


@dataclass
class PipelineContext:
    job: Job
    source_locator: str | None = None
    raw_audio_path: Path | None = None
    audio_track_selection: AudioTrackSelection = AudioTrackSelection.UNKNOWN
    metadata: MediaMetadata | None = None
    converted_audio_path: Path | None = None
    youtube_subtitle_used: bool = False
    requested_language: Language | None = None
    language_source: LanguageSource = LanguageSource.UNKNOWN
    transcribed_segments: tuple[TranscribedSegment, ...] = ()
    transcription_language: Language | None = None
    transcription_confidence: float | None = None
    observed_language: Language | None = None
    observed_language_confidence: float | None = None
    transcript: Transcript | None = None
    runtime_plan: RuntimePlan | None = None
    processing_provenance: ProcessingProvenance = field(
        default_factory=ProcessingProvenance.unknown
    )
    final_md_path: Path | None = None
    diagnostics: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancel_event: threading.Event | None = None

    def add_diagnostic(self, msg: str) -> None:
        self.diagnostics.append(msg)
