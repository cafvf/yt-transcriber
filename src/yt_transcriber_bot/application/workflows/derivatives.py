from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.derived_artifacts import (
    DerivedArtifactAssociation,
    GeneratedDerivativeFile,
    TranscriptDerivativeGateway,
)
from yt_transcriber_bot.application.ports.job_repository import JobRepository
from yt_transcriber_bot.application.services.rename_speakers import (
    RenameResult,
    RenameSpeakersService,
)
from yt_transcriber_bot.application.services.search_indexing import SearchIndexingService
from yt_transcriber_bot.application.workflows.history import CompletedHistoryWorkflow
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass


@dataclass(frozen=True, slots=True)
class PreparedRenameTarget:
    job: Job
    canonical_transcript_ref: str
    speakers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AssociatedDerivedFile:
    association: DerivedArtifactAssociation
    path: Path
    format: str = ""
    size_bytes: int | None = None


class TranscriptDerivativeWorkflow:
    def __init__(
        self,
        *,
        repository: JobRepository,
        history: CompletedHistoryWorkflow,
        rename_service: RenameSpeakersService,
        gateway: TranscriptDerivativeGateway,
        indexer: SearchIndexingService,
        transcripts_dir: Path,
    ) -> None:
        self._repository = repository
        self._history = history
        self._rename_service = rename_service
        self._gateway = gateway
        self._indexer = indexer
        self._transcripts_dir = transcripts_dir

    def select(self, *, user_id: int, index: int) -> Job:
        if index <= 0:
            raise ValueError("Use um número positivo.")
        job = self._history.select(user_id, index=index)
        if job is None or job.status is not JobStatus.COMPLETED:
            raise LookupError(f"Não encontrei a transcrição #{index}.")
        return job

    @staticmethod
    def _reference(job: Job) -> str:
        reference = (job.canonical_transcript_ref or "").strip()
        if not reference:
            raise FileNotFoundError("Não consegui localizar o snapshot dessa transcrição.")
        return reference

    def prepare_rename(self, *, user_id: int, index: int) -> PreparedRenameTarget:
        job = self.select(user_id=user_id, index=index)
        reference = self._reference(job)
        return PreparedRenameTarget(job, reference, self._rename_service.list_speakers(reference))

    def rename(self, *, job_id: str, aliases: dict[str, str]) -> RenameResult:
        job = self._repository.get_by_id(job_id)
        if job is None or job.status is not JobStatus.COMPLETED:
            raise LookupError("Job selecionado não encontrado.")
        reference = self._reference(job)
        if not job.md_path:
            raise FileNotFoundError("O Markdown desse job não está disponível.")
        normalized_aliases = {label: name.strip() for label, name in aliases.items()}
        result = self._rename_service.rename(reference, normalized_aliases, Path(job.md_path))
        job.speaker_renames = normalized_aliases
        self._repository.save(job)
        self._indexer.refresh(job)
        return result

    def _base(self, job: Job, reference: str) -> Path:
        return Path(job.md_path) if job.md_path else self._transcripts_dir / reference

    def export_text(self, *, user_id: int, index: int) -> AssociatedDerivedFile:
        job = self.select(user_id=user_id, index=index)
        reference = self._reference(job)
        generated = self._gateway.export_text(
            canonical_transcript_ref=reference,
            output_base_path=self._base(job, reference),
            speaker_aliases=job.speaker_renames,
        )
        return self._associated(job, ArtifactClass.DERIVED_EXPORT, generated)

    def export_transcript(self, *, user_id: int, index: int, format: str) -> AssociatedDerivedFile:
        job = self.select(user_id=user_id, index=index)
        reference = self._reference(job)
        generated = self._gateway.export_transcript(
            canonical_transcript_ref=reference,
            output_base_path=self._base(job, reference),
            format=format,
            speaker_aliases=job.speaker_renames,
        )
        return self._associated(job, ArtifactClass.DERIVED_EXPORT, generated)

    def export_video(self, *, user_id: int, index: int) -> AssociatedDerivedFile:
        job = self.select(user_id=user_id, index=index)
        reference = self._reference(job)
        if job.video_id is None:
            raise ValueError("Vídeo legendado está disponível apenas para transcrições do YouTube.")
        generated = self._gateway.export_video(
            video_id=job.video_id,
            canonical_transcript_ref=reference,
            speaker_aliases=job.speaker_renames,
        )
        return self._associated(job, ArtifactClass.DERIVED_VIDEO, generated)

    @staticmethod
    def _associated(
        job: Job, artifact_class: ArtifactClass, generated: GeneratedDerivativeFile
    ) -> AssociatedDerivedFile:
        return AssociatedDerivedFile(
            DerivedArtifactAssociation.from_job(job, artifact_class),
            generated.path,
            generated.format,
            generated.size_bytes,
        )
