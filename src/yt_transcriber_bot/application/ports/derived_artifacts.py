from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


@dataclass(frozen=True, slots=True)
class DerivedArtifactAssociation:
    job_id: str
    canonical_transcript_ref: str
    artifact_class: ArtifactClass

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.canonical_transcript_ref.strip():
            raise ValueError("derived artifact requires canonical Job/transcript identity")
        if self.artifact_class.is_canonical or self.artifact_class.is_volatile:
            raise ValueError("artifact class is not derived")

    @classmethod
    def from_job(cls, job: Job, artifact_class: ArtifactClass) -> DerivedArtifactAssociation:
        reference = (job.canonical_transcript_ref or "").strip()
        if not reference:
            raise ValueError("completed job has no canonical transcript reference")
        return cls(job.job_id, reference, artifact_class)


@dataclass(frozen=True, slots=True)
class StoredSummaryArtifact:
    association: DerivedArtifactAssociation
    path: Path
    content: str


class SummaryArtifactStore(ABC):
    @abstractmethod
    def save(
        self, association: DerivedArtifactAssociation, content: str
    ) -> StoredSummaryArtifact: ...

    @abstractmethod
    def load(
        self, *, job_id: str, canonical_transcript_ref: str
    ) -> StoredSummaryArtifact | None: ...

    @abstractmethod
    def delete(self, *, job_id: str, canonical_transcript_ref: str) -> None: ...


@dataclass(frozen=True, slots=True)
class GeneratedDerivativeFile:
    path: Path
    format: str = ""
    size_bytes: int | None = None


class TranscriptDerivativeGateway(ABC):
    @abstractmethod
    def export_text(
        self,
        *,
        canonical_transcript_ref: str,
        output_base_path: Path,
        speaker_aliases: Mapping[str, str],
    ) -> GeneratedDerivativeFile: ...

    @abstractmethod
    def export_transcript(
        self,
        *,
        canonical_transcript_ref: str,
        output_base_path: Path,
        format: str,
        speaker_aliases: Mapping[str, str],
    ) -> GeneratedDerivativeFile: ...

    @abstractmethod
    def export_video(
        self,
        *,
        video_id: VideoId,
        canonical_transcript_ref: str,
        speaker_aliases: Mapping[str, str],
    ) -> GeneratedDerivativeFile: ...
