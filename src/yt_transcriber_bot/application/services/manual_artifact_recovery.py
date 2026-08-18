"""Read-only manual recovery classification for persisted delivery artifacts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.domain.entities.job import JobStatus


class ArtifactRecoveryState(StrEnum):
    AVAILABLE = "available"
    REFERENCE_ABSENT = "reference_absent"
    REFERENCED_MISSING = "referenced_missing"


@dataclass(frozen=True)
class RecoverableArtifact:
    kind: str
    path: Path | None
    state: ArtifactRecoveryState

    @property
    def available(self) -> bool:
        return self.state is ArtifactRecoveryState.AVAILABLE


@dataclass(frozen=True)
class ManualArtifactRecoveryReport:
    job_id: str
    status: JobStatus
    eligible: bool
    artifacts: tuple[RecoverableArtifact, ...]

    @property
    def recoverable(self) -> tuple[RecoverableArtifact, ...]:
        return tuple(item for item in self.artifacts if item.available)


class ManualArtifactRecoveryService:
    """Classify persisted artifacts without mutating the Job or filesystem."""

    def __init__(
        self,
        repository: JobRepository,
        *,
        artifact_available: Callable[[Path], bool],
    ) -> None:
        self._repository = repository
        self._artifact_available = artifact_available

    def inspect(self, job_id: str) -> ManualArtifactRecoveryReport | None:
        job = self._repository.get_by_id(job_id)
        if job is None:
            return None
        artifacts = (
            self._classify("markdown", job.md_path),
            self._classify("audio", job.audio_path),
        )
        return ManualArtifactRecoveryReport(
            job_id=job.job_id,
            status=job.status,
            eligible=job.status is JobStatus.DELIVERY_FAILED,
            artifacts=artifacts,
        )

    def _classify(self, kind: str, raw_path: str | None) -> RecoverableArtifact:
        if not raw_path:
            return RecoverableArtifact(
                kind=kind,
                path=None,
                state=ArtifactRecoveryState.REFERENCE_ABSENT,
            )
        path = Path(raw_path)
        return RecoverableArtifact(
            kind=kind,
            path=path,
            state=(
                ArtifactRecoveryState.AVAILABLE
                if self._artifact_available(path)
                else ArtifactRecoveryState.REFERENCED_MISSING
            ),
        )


__all__ = [
    "ArtifactRecoveryState",
    "ManualArtifactRecoveryReport",
    "ManualArtifactRecoveryService",
    "RecoverableArtifact",
]
