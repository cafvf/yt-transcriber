from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.application.ports.derived_artifacts import (
    DerivedArtifactAssociation,
    StoredSummaryArtifact,
    SummaryArtifactStore,
)
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.infrastructure.filesystem_safety import (
    ensure_private_directory,
    ensure_private_file,
)


class FilesystemSummaryArtifactStore(SummaryArtifactStore):
    def __init__(self, root: Path) -> None:
        self._root = root

    @staticmethod
    def _safe(reference: str) -> str:
        value = reference.strip()
        if not value or Path(value).name != value or value in {".", ".."}:
            raise ValueError("invalid canonical transcript reference")
        return value

    def _path(self, reference: str) -> Path:
        return self._root / f"{self._safe(reference)}.summary.md"

    def save(self, association: DerivedArtifactAssociation, content: str) -> StoredSummaryArtifact:
        if association.artifact_class is not ArtifactClass.DERIVED_SUMMARY:
            raise ValueError("summary store accepts DERIVED_SUMMARY only")
        ensure_private_directory(self._root)
        path = self._path(association.canonical_transcript_ref)
        path.write_text(content, encoding="utf-8")
        ensure_private_file(path)
        return StoredSummaryArtifact(association, path, content)

    def load(self, *, job_id: str, canonical_transcript_ref: str) -> StoredSummaryArtifact | None:
        path = self._path(canonical_transcript_ref)
        if not path.is_file():
            return None
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        association = DerivedArtifactAssociation(
            job_id,
            canonical_transcript_ref,
            ArtifactClass.DERIVED_SUMMARY,
        )
        return StoredSummaryArtifact(association, path, content)

    def delete(self, *, job_id: str, canonical_transcript_ref: str) -> None:
        _ = job_id
        self._path(canonical_transcript_ref).unlink(missing_ok=True)
