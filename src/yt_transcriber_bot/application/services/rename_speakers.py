"""Serviço RenameSpeakers — aplica aliases e re-renderiza o MD.

Funciona inclusive em vídeos legados (cujo .ogg foi expurgado), pois o
snapshot persistido em JSON contém tudo que o renderer precisa.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
)


@dataclass(frozen=True)
class RenameResult:
    md_path: Path
    speakers_renamed: int


class RenameSpeakersService:
    """Renomeia falantes em uma transcrição persistida."""

    def __init__(
        self,
        snapshots: TranscriptSnapshotRepository,
        renderer: MarkdownTranscriptRenderer,
    ) -> None:
        self._snapshots = snapshots
        self._renderer = renderer

    def list_speakers(self, slug: str) -> tuple[str, ...]:
        snap = self._snapshots.load(slug)
        if snap is None:
            raise FileNotFoundError(f"Snapshot inexistente: {slug}")
        return snap.transcript.speaker_labels()

    def metadata_for(self, slug: str) -> VideoMetadata | None:
        """Retorna metadados do snapshot, quando ele ainda existe.

        Usado pela interface do Telegram para exibir títulos reais no histórico
        sem acoplar o adapter à persistência de snapshots.
        """
        return self._snapshots.load_metadata(slug)

    def metadata_for_many(self, slugs: tuple[str, ...]) -> dict[str, VideoMetadata]:
        """Carrega títulos em lote para comandos que listam histórico."""
        return self._snapshots.load_metadata_many(slugs)

    def rename(
        self,
        slug: str,
        aliases: Mapping[str, str],
        md_path: Path,
    ) -> RenameResult:
        snap = self._snapshots.load(slug)
        if snap is None:
            raise FileNotFoundError(f"Snapshot inexistente: {slug}")
        # Filtra aliases vazios ou para labels inexistentes
        labels = set(snap.transcript.speaker_labels())
        effective = {
            label: name.strip()
            for label, name in aliases.items()
            if label in labels and name.strip()
        }
        rendered = self._renderer.render(
            snap.metadata,
            snap.transcript,
            snap.context,
            speaker_aliases=effective,
        )
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(rendered, encoding="utf-8")
        return RenameResult(md_path=md_path, speakers_renamed=len(effective))
