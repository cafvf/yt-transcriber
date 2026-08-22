"""Proveniência efetivamente observada durante um processamento."""

from __future__ import annotations

from dataclasses import dataclass

from yt_transcriber_bot.domain.value_objects.language import LanguageSource


@dataclass(frozen=True, slots=True)
class ProcessingProvenance:
    processing_path: str | None = None
    transcription_backend: str | None = None
    transcription_model: str | None = None
    device: str | None = None
    compute_type: str | None = None
    asr_fallback_used: bool | None = None
    diarization_backend: str | None = None
    diarization_model: str | None = None
    diarization_fallback_used: bool | None = None
    language_source: LanguageSource | None = None

    def __post_init__(self) -> None:
        if self.language_source is not None and not isinstance(
            self.language_source, LanguageSource
        ):
            raise TypeError("ProcessingProvenance.language_source exige LanguageSource | None")

    @classmethod
    def unknown(cls) -> ProcessingProvenance:
        return cls()

    def as_dict(self) -> dict[str, str | bool | None]:
        return {
            "processing_path": self.processing_path,
            "transcription_backend": self.transcription_backend,
            "transcription_model": self.transcription_model,
            "device": self.device,
            "compute_type": self.compute_type,
            "asr_fallback_used": self.asr_fallback_used,
            "diarization_backend": self.diarization_backend,
            "diarization_model": self.diarization_model,
            "diarization_fallback_used": self.diarization_fallback_used,
            "language_source": (
                self.language_source.value if self.language_source is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> ProcessingProvenance:
        if not isinstance(value, dict):
            return cls.unknown()

        def text(key: str) -> str | None:
            raw = value.get(key)
            return str(raw) if isinstance(raw, str) and raw else None

        language_source_raw = text("language_source")
        try:
            language_source = (
                LanguageSource(language_source_raw) if language_source_raw is not None else None
            )
        except ValueError:
            language_source = None

        asr_fallback = value.get("asr_fallback_used")
        diarization_fallback = value.get("diarization_fallback_used")
        return cls(
            processing_path=text("processing_path"),
            transcription_backend=text("transcription_backend"),
            transcription_model=text("transcription_model"),
            device=text("device"),
            compute_type=text("compute_type"),
            asr_fallback_used=(asr_fallback if isinstance(asr_fallback, bool) else None),
            diarization_backend=text("diarization_backend"),
            diarization_model=text("diarization_model"),
            diarization_fallback_used=(
                diarization_fallback if isinstance(diarization_fallback, bool) else None
            ),
            language_source=language_source,
        )
