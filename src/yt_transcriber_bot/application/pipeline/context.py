"""Contexto compartilhado entre os passos do pipeline (Chain of Responsibility).

O contexto é mutável dentro do pipeline mas pertence a UM job: cada job
cria seu próprio contexto e é processado sequencialmente. Atributos vão
sendo preenchidos por cada step à medida que executam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from yt_transcriber_bot.application.ports.transcription_engine import (
    TranscribedSegment,
)
from yt_transcriber_bot.application.runtime_selection import RuntimePlan
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.entities.transcript import Transcript
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata


@dataclass
class PipelineContext:
    """Contêiner mutável de tudo o que circula entre steps."""

    job: Job
    raw_audio_path: Path | None = None
    audio_track_was_dubbed: bool = False
    metadata: VideoMetadata | None = None
    converted_audio_path: Path | None = None
    youtube_subtitle_used: bool = False
    youtube_subtitle_kind: str | None = None  # 'manual' | 'auto'
    requested_language: str | None = None
    language_source: str | None = None  # 'user' | 'metadata' | 'asr' | 'youtube_manual' | 'youtube_auto'
    transcribed_segments: tuple[TranscribedSegment, ...] = ()
    transcription_language: str | None = None
    transcription_confidence: float | None = None
    transcript: Transcript | None = None
    runtime_plan: RuntimePlan | None = None
    final_md_path: Path | None = None
    diagnostics: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def add_diagnostic(self, msg: str) -> None:
        self.diagnostics.append(msg)
