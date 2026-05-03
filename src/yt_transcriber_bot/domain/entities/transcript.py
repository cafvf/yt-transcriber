"""Entidades ``TranscriptSegment``, ``SpeakerTurn`` e ``Transcript``."""

from __future__ import annotations

from dataclasses import dataclass, field

from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """Segmento individual com timestamps em segundos."""

    start_seconds: float
    end_seconds: float
    text: str
    speaker_label: str  # ex.: "SPEAKER_00"

    def __post_init__(self) -> None:
        if self.start_seconds < 0:
            raise ValueError(f"start_seconds inválido: {self.start_seconds}")
        if self.end_seconds < self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) < start_seconds ({self.start_seconds})"
            )
        if not self.text:
            raise ValueError("text não pode ser vazio")
        if not self.speaker_label:
            raise ValueError("speaker_label não pode ser vazio")


@dataclass(frozen=True, slots=True)
class SpeakerTurn:
    """Turno: agregação contígua de segmentos do mesmo falante."""

    start_seconds: float
    end_seconds: float
    speaker_label: str
    text: str

    @property
    def duration(self) -> Duration:
        return Duration.from_seconds(self.end_seconds - self.start_seconds)


@dataclass(frozen=True, slots=True)
class Transcript:
    """Transcrição completa: lista de segmentos + idioma."""

    segments: tuple[TranscriptSegment, ...]
    language: Language
    language_confidence: float = 0.0
    source: str = "whisperx"  # whisperx | youtube_manual | youtube_auto
    word_segments: tuple[dict[str, float | str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.language_confidence <= 1.0:
            raise ValueError(f"language_confidence fora de [0,1]: {self.language_confidence}")
        if self.source not in {"whisperx", "youtube_manual", "youtube_auto"}:
            raise ValueError(f"source inválido: '{self.source}'")

    def to_speaker_turns(self) -> tuple[SpeakerTurn, ...]:
        """Agrupa segmentos consecutivos do mesmo falante em turnos."""
        if not self.segments:
            return ()

        turns: list[SpeakerTurn] = []
        current_label = self.segments[0].speaker_label
        current_start = self.segments[0].start_seconds
        current_end = self.segments[0].end_seconds
        current_text_parts = [self.segments[0].text]

        for seg in self.segments[1:]:
            if seg.speaker_label == current_label:
                current_end = seg.end_seconds
                current_text_parts.append(seg.text)
            else:
                turns.append(
                    SpeakerTurn(
                        start_seconds=current_start,
                        end_seconds=current_end,
                        speaker_label=current_label,
                        text=" ".join(current_text_parts).strip(),
                    )
                )
                current_label = seg.speaker_label
                current_start = seg.start_seconds
                current_end = seg.end_seconds
                current_text_parts = [seg.text]

        turns.append(
            SpeakerTurn(
                start_seconds=current_start,
                end_seconds=current_end,
                speaker_label=current_label,
                text=" ".join(current_text_parts).strip(),
            )
        )
        return tuple(turns)

    def speaker_labels(self) -> tuple[str, ...]:
        """Devolve os labels de falantes na ordem de aparição."""
        seen: list[str] = []
        for seg in self.segments:
            if seg.speaker_label not in seen:
                seen.append(seg.speaker_label)
        return tuple(seen)

    def speaker_speaking_time(self) -> dict[str, Duration]:
        """Tempo total de fala (em segundos) por label."""
        totals: dict[str, float] = {}
        for seg in self.segments:
            duration = seg.end_seconds - seg.start_seconds
            totals[seg.speaker_label] = totals.get(seg.speaker_label, 0.0) + duration
        return {label: Duration.from_seconds(secs) for label, secs in totals.items()}
