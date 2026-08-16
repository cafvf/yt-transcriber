"""Proveniência efetivamente observada durante um processamento."""

from __future__ import annotations

from dataclasses import asdict, dataclass


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
    language_source: str | None = None

    @classmethod
    def unknown(cls) -> ProcessingProvenance:
        return cls()

    def as_dict(self) -> dict[str, str | bool | None]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> ProcessingProvenance:
        if not isinstance(value, dict):
            return cls.unknown()

        def text(key: str) -> str | None:
            raw = value.get(key)
            return str(raw) if isinstance(raw, str) and raw else None

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
            language_source=text("language_source"),
        )
