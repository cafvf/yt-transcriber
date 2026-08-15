"""Entidades de transcrição com fatos linguísticos explícitos e não fabricados."""

from __future__ import annotations

from dataclasses import dataclass, field

from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    """Segmento individual com intervalo temporal positivo."""

    start_seconds: float
    end_seconds: float
    text: str
    speaker_label: str

    def __post_init__(self) -> None:
        if self.start_seconds < 0:
            raise ValueError(f"start_seconds inválido: {self.start_seconds}")
        if self.end_seconds <= self.start_seconds:
            raise ValueError(
                f"end_seconds ({self.end_seconds}) deve ser > start_seconds ({self.start_seconds})"
            )
        if not self.text:
            raise ValueError("text não pode ser vazio")
        if not self.speaker_label:
            raise ValueError("speaker_label não pode ser vazio")


@dataclass(frozen=True, slots=True)
class SpeakerTurn:
    start_seconds: float
    end_seconds: float
    speaker_label: str
    text: str

    @property
    def duration(self) -> Duration:
        return Duration.from_seconds(self.end_seconds - self.start_seconds)


@dataclass(frozen=True, slots=True)
class Transcript:
    """Transcrição canônica e fatos linguísticos associados.

    ``language`` é o idioma efetivo da transcrição quando conhecido.
    ``requested_language`` e ``observed_language`` são fatos independentes.
    Uma confiança só é armazenada quando ela realmente se refere ao fato que
    está sendo exposto; ``None`` significa desconhecida/não fornecida.
    """

    segments: tuple[TranscriptSegment, ...]
    language: Language | None
    language_confidence: float | None = None
    source: str = "whisperx"
    requested_language: Language | None = None
    observed_language: Language | None = None
    observed_language_confidence: float | None = None
    language_source: LanguageSource = LanguageSource.UNKNOWN
    word_segments: tuple[dict[str, float | str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for value, name in (
            (self.language_confidence, "language_confidence"),
            (self.observed_language_confidence, "observed_language_confidence"),
        ):
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} fora de [0,1]: {value}")
        if self.language is None and self.language_confidence is not None:
            raise ValueError("language_confidence exige language conhecido")
        if self.observed_language is None and self.observed_language_confidence is not None:
            raise ValueError("observed_language_confidence exige observed_language conhecido")
        if self.source not in {"whisperx", "youtube_manual", "youtube_auto"}:
            raise ValueError(f"source inválido: '{self.source}'")

    def to_speaker_turns(self) -> tuple[SpeakerTurn, ...]:
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
        seen: list[str] = []
        for seg in self.segments:
            if seg.speaker_label not in seen:
                seen.append(seg.speaker_label)
        return tuple(seen)

    def speaker_speaking_time(self) -> dict[str, Duration]:
        totals: dict[str, float] = {}
        for seg in self.segments:
            duration = seg.end_seconds - seg.start_seconds
            totals[seg.speaker_label] = totals.get(seg.speaker_label, 0.0) + duration
        return {label: Duration.from_seconds(secs) for label, secs in totals.items()}
