"""Fakes reusáveis para testar steps e use case sem mexer em I/O real."""

from __future__ import annotations

import shutil
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.audio_converter import (
    AudioConverter,
    ConvertedAudio,
)
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationResult,
    DiarizedSpeakerSegment,
)
from yt_transcriber_bot.application.ports.gpu_detector import (
    GpuDetector,
    HardwareProfile,
)
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.ports.transcription_engine import (
    TranscribedSegment,
    TranscriptionEngine,
    TranscriptionRequest,
    TranscriptionResult,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    DownloadedAudio,
    FetchedSubtitle,
    SubtitleTrack,
    YouTubeDownloader,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId

# ----------------------------------------------------------------------
# Fake YouTubeDownloader
# ----------------------------------------------------------------------


@dataclass
class FakeYouTubeDownloader(YouTubeDownloader):
    metadata: VideoMetadata | None = None
    subtitles: tuple[SubtitleTrack, ...] = ()
    fetched_subtitle: FetchedSubtitle | None = None
    audio_payload: bytes = b"FAKE_AUDIO_BYTES"
    audio_container: str = "m4a"
    audio_used_alternate: bool = False
    raise_on_metadata: Exception | None = None
    raise_on_audio: Exception | None = None
    raise_on_list_subtitles: Exception | None = None

    def fetch_metadata(self, video_id: VideoId) -> VideoMetadata:
        if self.raise_on_metadata is not None:
            raise self.raise_on_metadata
        if self.metadata is None:
            self.metadata = VideoMetadata(
                video_id=video_id,
                title="Video de Teste",
                channel="Canal Fake",
                duration=Duration.from_seconds(120),
                upload_date=date(2024, 1, 1),
                original_language=Language(code="pt"),
            )
        return self.metadata

    def list_subtitles(self, video_id: VideoId) -> tuple[SubtitleTrack, ...]:
        if self.raise_on_list_subtitles is not None:
            raise self.raise_on_list_subtitles
        return self.subtitles

    def fetch_subtitle(
        self,
        video_id: VideoId,
        track: SubtitleTrack,
        *,
        cancel_event: threading.Event | None = None,
    ) -> FetchedSubtitle:
        if self.fetched_subtitle is None:
            return FetchedSubtitle(
                language=track.language,
                is_auto_generated=track.is_auto_generated,
                segments=(),
            )
        return self.fetched_subtitle

    def download_audio(
        self,
        video_id: VideoId,
        dest_dir: Path,
        *,
        cancel_event: threading.Event | None = None,
    ) -> DownloadedAudio:
        if self.raise_on_audio is not None:
            raise self.raise_on_audio
        path = dest_dir / f"{video_id.value}.{self.audio_container}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.audio_payload)
        meta = self.fetch_metadata(video_id)
        return DownloadedAudio(
            audio_path=path,
            container=self.audio_container,
            used_alternate_track=self.audio_used_alternate,
            metadata=meta,
        )


# ----------------------------------------------------------------------
# Fake AudioConverter
# ----------------------------------------------------------------------


@dataclass
class FakeAudioConverter(AudioConverter):
    raise_on_convert: Exception | None = None
    convert_calls: list[dict[str, object]] = field(default_factory=list)

    def convert_to_opus_mono(
        self,
        source: Path,
        dest: Path,
        *,
        bitrate_kbps: int = 32,
        sample_rate_hz: int = 16000,
        cancel_event: threading.Event | None = None,
    ) -> ConvertedAudio:
        self.convert_calls.append(
            {
                "source": source,
                "dest": dest,
                "bitrate_kbps": bitrate_kbps,
                "sample_rate_hz": sample_rate_hz,
            }
        )
        if self.raise_on_convert is not None:
            raise self.raise_on_convert
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Simula conversão copiando bytes (não é Opus de verdade, mas serve para
        # os steps que apenas precisam do arquivo existir).
        shutil.copyfile(source, dest)
        return ConvertedAudio(
            path=dest,
            bitrate_kbps=bitrate_kbps,
            sample_rate_hz=sample_rate_hz,
            channels=1,
            container="ogg",
            size_bytes=dest.stat().st_size,
        )

    def split_for_telegram(
        self,
        source: Path,
        dest_dir: Path,
        *,
        max_size_bytes: int = 49 * 1024 * 1024,
        cancel_event: threading.Event | None = None,
    ) -> tuple[Path, ...]:
        return (source,)


# ----------------------------------------------------------------------
# Fake GpuDetector
# ----------------------------------------------------------------------


@dataclass
class FakeGpuDetector(GpuDetector):
    profile: HardwareProfile = field(
        default_factory=lambda: HardwareProfile(
            has_cuda=False,
            cuda_compute_capability=None,
            vram_total_gb=0.0,
            gpu_name="",
        )
    )

    def detect(self) -> HardwareProfile:
        return self.profile


# ----------------------------------------------------------------------
# Fake TranscriptionEngine
# ----------------------------------------------------------------------


@dataclass
class FakeTranscriptionEngine(TranscriptionEngine):
    result: TranscriptionResult | None = None
    raise_on_call: Exception | None = None
    calls: list[dict[str, object]] = field(default_factory=list)

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        self.calls.append(
            {
                "request": request,
                "audio_path": request.audio_path,
                "profile": request.processing_profile,
                "allowed_languages": request.allowed_languages,
                "requested_language": request.requested_language,
            }
        )
        if self.raise_on_call is not None:
            exc, self.raise_on_call = self.raise_on_call, None
            raise exc
        if self.result is None:
            return TranscriptionResult(
                segments=(
                    TranscribedSegment(
                        start_seconds=0.0,
                        end_seconds=2.0,
                        text="Olá.",
                    ),
                ),
                detected_language=Language(code="pt"),
                language_confidence=0.95,
            )
        return self.result


# ----------------------------------------------------------------------
# Fake DiarizationEngine
# ----------------------------------------------------------------------


@dataclass
class FakeDiarizationEngine(DiarizationEngine):
    result: DiarizationResult | None = None
    raise_on_call: Exception | None = None
    calls: list[dict[str, object]] = field(default_factory=list)

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        progress: Callable[[float, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> DiarizationResult:
        self.calls.append(
            {
                "audio_path": audio_path,
                "device": device,
                "min_speakers": min_speakers,
                "max_speakers": max_speakers,
            }
        )
        if self.raise_on_call is not None:
            raise self.raise_on_call
        if self.result is None:
            return DiarizationResult(
                speaker_segments=(
                    DiarizedSpeakerSegment(
                        start_seconds=0.0,
                        end_seconds=10.0,
                        speaker_label="SPEAKER_00",
                    ),
                ),
                total_speakers=1,
            )
        return self.result


# ----------------------------------------------------------------------
# Fake JobRepository (in-memory)
# ----------------------------------------------------------------------


@dataclass
class FakeJobRepository(JobRepository):
    jobs: dict[str, Job] = field(default_factory=dict)

    def save(self, job: Job) -> None:
        self.jobs[job.job_id] = job

    def get_by_id(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def get_latest_by_video_id(self, video_id: VideoId) -> Job | None:
        candidates = [j for j in self.jobs.values() if j.video_id == video_id]
        if not candidates:
            return None
        return max(candidates, key=lambda j: j.requested_at)

    def get_latest_completed_for_user(self, user_id: int) -> Job | None:
        candidates = [
            j
            for j in self.jobs.values()
            if j.requested_by_user_id == user_id and j.status == JobStatus.COMPLETED
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda j: j.requested_at)

    def list_recent_for_user(self, user_id: int, limit: int) -> list[Job]:
        ordered = sorted(
            (j for j in self.jobs.values() if j.requested_by_user_id == user_id),
            key=lambda j: j.requested_at,
            reverse=True,
        )
        return list(ordered[:limit])

    def list_completed_oldest_first(self) -> list[Job]:
        ordered = sorted(
            (j for j in self.jobs.values() if j.status == JobStatus.COMPLETED),
            key=lambda j: j.requested_at,
        )
        return list(ordered)

    def list_by_statuses_oldest_first(self, statuses: set[JobStatus]) -> list[Job]:
        ordered = sorted(
            (j for j in self.jobs.values() if j.status in statuses),
            key=lambda j: j.requested_at,
        )
        return list(ordered)

    def delete(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)


# ----------------------------------------------------------------------
# Fixtures pytest
# ----------------------------------------------------------------------


@pytest.fixture
def settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        telegram_bot_token="fake-token-XX",
        telegram_allowed_user_id=42,
        hf_token="hf_fake",
        whisper_model="small",
        device="cpu",
        compute_type="int8",
        base_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        db_path=tmp_path / "data" / "jobs.db",
    )


@pytest.fixture
def fake_repo() -> FakeJobRepository:
    return FakeJobRepository()


@pytest.fixture
def fake_downloader() -> FakeYouTubeDownloader:
    return FakeYouTubeDownloader()


@pytest.fixture
def fake_converter() -> FakeAudioConverter:
    return FakeAudioConverter()


@pytest.fixture
def fake_gpu_cpu() -> FakeGpuDetector:
    return FakeGpuDetector()


@pytest.fixture
def fake_transcription() -> FakeTranscriptionEngine:
    return FakeTranscriptionEngine()


@pytest.fixture
def fake_diarization() -> FakeDiarizationEngine:
    return FakeDiarizationEngine()
