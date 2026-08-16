"""Application-owned structured transcript rendering capability."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptRecord,
)


@dataclass(frozen=True, slots=True)
class TranscriptRenderRequest:
    """Structured evidence plus presentation aliases.

    Processing provenance travels inside ``record`` so a renderer can use it
    without depending on a persistence implementation.
    """

    record: CanonicalTranscriptRecord
    speaker_aliases: Mapping[str, str] | None = None


class TranscriptRenderer(ABC):
    """Render structured transcript evidence without owning persistence."""

    @abstractmethod
    def render_transcript(self, request: TranscriptRenderRequest) -> str: ...
