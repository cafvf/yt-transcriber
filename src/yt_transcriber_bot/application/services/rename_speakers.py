"""Application service for speaker aliases over canonical transcript evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptStore,
)
from yt_transcriber_bot.application.ports.transcript_renderer import (
    TranscriptRenderer,
    TranscriptRenderRequest,
)
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata


@dataclass(frozen=True)
class RenameResult:
    md_path: Path
    speakers_renamed: int


class RenameSpeakersService:
    """Rename speakers using canonical structured evidence."""

    def __init__(
        self,
        snapshots: CanonicalTranscriptStore,
        renderer: TranscriptRenderer,
    ) -> None:
        self._snapshots = snapshots
        self._renderer = renderer

    def list_speakers(self, slug: str) -> tuple[str, ...]:
        return self._snapshots.require(slug).transcript.speaker_labels()

    def metadata_for(self, slug: str) -> VideoMetadata | None:
        """Return canonical metadata for history display."""
        return self._snapshots.load_metadata(slug)

    def metadata_for_many(self, slugs: tuple[str, ...]) -> dict[str, VideoMetadata]:
        """Load canonical metadata in batch for history commands."""
        return self._snapshots.load_metadata_many(slugs)

    def rename(
        self,
        slug: str,
        aliases: Mapping[str, str],
        md_path: Path,
    ) -> RenameResult:
        record = self._snapshots.require(slug)
        labels = set(record.transcript.speaker_labels())
        effective = {
            label: name.strip()
            for label, name in aliases.items()
            if label in labels and name.strip()
        }
        rendered = self._renderer.render_transcript(
            TranscriptRenderRequest(
                record=record,
                speaker_aliases=effective,
            )
        )
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(rendered, encoding="utf-8")
        return RenameResult(md_path=md_path, speakers_renamed=len(effective))
