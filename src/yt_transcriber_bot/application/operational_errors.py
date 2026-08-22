"""Provider-neutral operational failure taxonomy for application boundaries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.ports.audio_converter import AudioConversionError
from yt_transcriber_bot.application.ports.derived_artifacts import (
    DerivativeExportError,
    DerivativeTooLargeError,
    DerivativeTooLongError,
)
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationError,
    DiarizationUnavailableError,
)
from yt_transcriber_bot.application.ports.text_generation import (
    TextGenerationError,
    TextGenerationTimeoutError,
)
from yt_transcriber_bot.application.ports.transcription_engine import (
    ObservedLanguageNotAllowedError,
    OutOfMemoryError,
    TranscriptionError,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    AgeRestrictedError,
    MembersOnlyError,
    NoAudioStreamError,
    VideoUnavailableError,
    YouTubeError,
)


class OperationalErrorCategory(StrEnum):
    ACCESS = "access"
    MEDIA = "media"
    TRANSCRIPTION = "transcription"
    DIARIZATION = "diarization"
    GENERATION = "generation"
    ARTIFACT = "artifact"
    OPERATION = "operation"
    DELIVERY = "delivery"
    INTERNAL = "internal"


class OperationalErrorCode(StrEnum):
    YOUTUBE_AUTH_REQUIRED = "youtube.auth_required"
    YOUTUBE_VIDEO_UNAVAILABLE = "youtube.video_unavailable"
    YOUTUBE_NO_AUDIO_STREAM = "youtube.no_audio_stream"
    YOUTUBE_PROVIDER_FAILURE = "youtube.provider_failure"
    MEDIA_DURATION_EXCEEDED = "media.duration_exceeded"
    MEDIA_DURATION_UNKNOWN = "media.duration_unknown"
    MEDIA_LANGUAGE_NOT_ALLOWED = "media.language_not_allowed"
    MEDIA_REJECTED = "media.rejected"
    MEDIA_CONVERSION_FAILED = "media.conversion_failed"
    TRANSCRIPTION_OUT_OF_MEMORY = "transcription.out_of_memory"
    TRANSCRIPTION_LANGUAGE_NOT_ALLOWED = "transcription.language_not_allowed"
    TRANSCRIPTION_FAILED = "transcription.failed"
    DIARIZATION_UNAVAILABLE = "diarization.unavailable"
    DIARIZATION_FAILED = "diarization.failed"
    TEXT_GENERATION_TIMEOUT = "text_generation.timeout"
    TEXT_GENERATION_FAILED = "text_generation.failed"
    ARTIFACT_TOO_LONG = "artifact.too_long"
    ARTIFACT_TOO_LARGE = "artifact.too_large"
    ARTIFACT_EXPORT_FAILED = "artifact.export_failed"
    OPERATION_CANCELLED = "operation.cancelled"
    DELIVERY_FAILED = "delivery.failed"
    INTERNAL_IO_FAILURE = "internal.io_failure"
    INTERNAL_INVARIANT_VIOLATION = "internal.invariant_violation"
    LEGACY_UNCLASSIFIED = "legacy.unclassified"


@dataclass(frozen=True, slots=True)
class OperationalErrorSpec:
    category: OperationalErrorCategory
    retryable: bool
    safe_message: str


@dataclass(frozen=True, slots=True)
class OperationalError:
    code: OperationalErrorCode
    category: OperationalErrorCategory
    retryable: bool
    safe_message: str
    technical_context: Mapping[str, str] = field(default_factory=dict)


class PipelineRejectionError(Exception):
    """Base for deliberate application rejections with stable semantics."""


class VideoTooLongError(PipelineRejectionError):
    """Media duration exceeds the configured processing limit."""


class MediaDurationUnknownError(PipelineRejectionError):
    """Media duration could not be established before expensive processing."""


class LanguageNotAllowedError(PipelineRejectionError):
    """Requested or evidenced language is outside the configured allowlist."""


class NoAudioAvailableError(PipelineRejectionError):
    """The source has no eligible audio stream for transcription."""


_SPECS: dict[OperationalErrorCode, OperationalErrorSpec] = {
    OperationalErrorCode.YOUTUBE_AUTH_REQUIRED: OperationalErrorSpec(
        OperationalErrorCategory.ACCESS,
        False,
        "O vídeo exige autenticação válida para acesso.",
    ),
    OperationalErrorCode.YOUTUBE_VIDEO_UNAVAILABLE: OperationalErrorSpec(
        OperationalErrorCategory.ACCESS,
        False,
        "O vídeo não está disponível para processamento.",
    ),
    OperationalErrorCode.YOUTUBE_NO_AUDIO_STREAM: OperationalErrorSpec(
        OperationalErrorCategory.MEDIA,
        False,
        "A mídia não possui uma faixa de áudio elegível para transcrição.",
    ),
    OperationalErrorCode.YOUTUBE_PROVIDER_FAILURE: OperationalErrorSpec(
        OperationalErrorCategory.ACCESS,
        True,
        "Falha temporária ao acessar o YouTube.",
    ),
    OperationalErrorCode.MEDIA_DURATION_EXCEEDED: OperationalErrorSpec(
        OperationalErrorCategory.MEDIA,
        False,
        "A mídia excede o limite de duração configurado.",
    ),
    OperationalErrorCode.MEDIA_DURATION_UNKNOWN: OperationalErrorSpec(
        OperationalErrorCategory.MEDIA,
        False,
        "Não foi possível estabelecer a duração da mídia antes do processamento.",
    ),
    OperationalErrorCode.MEDIA_LANGUAGE_NOT_ALLOWED: OperationalErrorSpec(
        OperationalErrorCategory.MEDIA,
        False,
        "O idioma da mídia não está permitido pela configuração atual.",
    ),
    OperationalErrorCode.MEDIA_REJECTED: OperationalErrorSpec(
        OperationalErrorCategory.MEDIA,
        False,
        "A mídia não pôde ser aceita para processamento.",
    ),
    OperationalErrorCode.MEDIA_CONVERSION_FAILED: OperationalErrorSpec(
        OperationalErrorCategory.MEDIA,
        True,
        "A conversão de áudio falhou durante o processamento.",
    ),
    OperationalErrorCode.TRANSCRIPTION_OUT_OF_MEMORY: OperationalErrorSpec(
        OperationalErrorCategory.TRANSCRIPTION,
        True,
        "A transcrição ficou sem memória mesmo após aplicar o fallback disponível.",
    ),
    OperationalErrorCode.TRANSCRIPTION_LANGUAGE_NOT_ALLOWED: OperationalErrorSpec(
        OperationalErrorCategory.TRANSCRIPTION,
        False,
        "O idioma observado pelo ASR não está permitido pela configuração atual.",
    ),
    OperationalErrorCode.TRANSCRIPTION_FAILED: OperationalErrorSpec(
        OperationalErrorCategory.TRANSCRIPTION,
        True,
        "A transcrição falhou no backend de ASR.",
    ),
    OperationalErrorCode.DIARIZATION_UNAVAILABLE: OperationalErrorSpec(
        OperationalErrorCategory.DIARIZATION,
        True,
        "A diarização está temporariamente indisponível.",
    ),
    OperationalErrorCode.DIARIZATION_FAILED: OperationalErrorSpec(
        OperationalErrorCategory.DIARIZATION,
        True,
        "A diarização falhou durante o processamento.",
    ),
    OperationalErrorCode.TEXT_GENERATION_TIMEOUT: OperationalErrorSpec(
        OperationalErrorCategory.GENERATION,
        True,
        "A geração de texto excedeu o tempo limite configurado.",
    ),
    OperationalErrorCode.TEXT_GENERATION_FAILED: OperationalErrorSpec(
        OperationalErrorCategory.GENERATION,
        True,
        "A geração de texto falhou no backend configurado.",
    ),
    OperationalErrorCode.ARTIFACT_TOO_LONG: OperationalErrorSpec(
        OperationalErrorCategory.ARTIFACT,
        False,
        "O artefato solicitado excede o limite de duração configurado.",
    ),
    OperationalErrorCode.ARTIFACT_TOO_LARGE: OperationalErrorSpec(
        OperationalErrorCategory.ARTIFACT,
        False,
        "O artefato solicitado excede o limite de tamanho configurado.",
    ),
    OperationalErrorCode.ARTIFACT_EXPORT_FAILED: OperationalErrorSpec(
        OperationalErrorCategory.ARTIFACT,
        True,
        "A geração do artefato derivado falhou.",
    ),
    OperationalErrorCode.OPERATION_CANCELLED: OperationalErrorSpec(
        OperationalErrorCategory.OPERATION,
        False,
        "Operação cancelada pelo usuário.",
    ),
    OperationalErrorCode.DELIVERY_FAILED: OperationalErrorSpec(
        OperationalErrorCategory.DELIVERY,
        True,
        "A entrega do artefato falhou; o arquivo local foi preservado quando disponível.",
    ),
    OperationalErrorCode.INTERNAL_IO_FAILURE: OperationalErrorSpec(
        OperationalErrorCategory.INTERNAL,
        True,
        "Falha de entrada/saída durante o processamento.",
    ),
    OperationalErrorCode.INTERNAL_INVARIANT_VIOLATION: OperationalErrorSpec(
        OperationalErrorCategory.INTERNAL,
        False,
        "O processamento falhou por uma condição interna inesperada.",
    ),
    OperationalErrorCode.LEGACY_UNCLASSIFIED: OperationalErrorSpec(
        OperationalErrorCategory.INTERNAL,
        False,
        "Erro operacional legado sem classificação estruturada.",
    ),
}

Sanitizer = Callable[[str], str]


def error_for_code(
    code: OperationalErrorCode,
    *,
    safe_message: str | None = None,
    technical_context: Mapping[str, str] | None = None,
) -> OperationalError:
    spec = _SPECS[code]
    return OperationalError(
        code=code,
        category=spec.category,
        retryable=spec.retryable,
        safe_message=safe_message or spec.safe_message,
        technical_context=dict(technical_context or {}),
    )


def classify_operational_error(
    exc: BaseException,
    *,
    sanitizer: Sanitizer | None = None,
) -> OperationalError:
    if isinstance(exc, (MembersOnlyError, AgeRestrictedError)):
        code = OperationalErrorCode.YOUTUBE_AUTH_REQUIRED
    elif isinstance(exc, VideoUnavailableError):
        code = OperationalErrorCode.YOUTUBE_VIDEO_UNAVAILABLE
    elif isinstance(exc, (NoAudioAvailableError, NoAudioStreamError)):
        code = OperationalErrorCode.YOUTUBE_NO_AUDIO_STREAM
    elif isinstance(exc, VideoTooLongError):
        code = OperationalErrorCode.MEDIA_DURATION_EXCEEDED
    elif isinstance(exc, MediaDurationUnknownError):
        code = OperationalErrorCode.MEDIA_DURATION_UNKNOWN
    elif isinstance(exc, LanguageNotAllowedError):
        code = OperationalErrorCode.MEDIA_LANGUAGE_NOT_ALLOWED
    elif isinstance(exc, PipelineRejectionError):
        code = OperationalErrorCode.MEDIA_REJECTED
    elif isinstance(exc, AudioConversionError):
        code = OperationalErrorCode.MEDIA_CONVERSION_FAILED
    elif isinstance(exc, OutOfMemoryError):
        code = OperationalErrorCode.TRANSCRIPTION_OUT_OF_MEMORY
    elif isinstance(exc, ObservedLanguageNotAllowedError):
        code = OperationalErrorCode.TRANSCRIPTION_LANGUAGE_NOT_ALLOWED
    elif isinstance(exc, TranscriptionError):
        code = OperationalErrorCode.TRANSCRIPTION_FAILED
    elif isinstance(exc, DiarizationUnavailableError):
        code = OperationalErrorCode.DIARIZATION_UNAVAILABLE
    elif isinstance(exc, DiarizationError):
        code = OperationalErrorCode.DIARIZATION_FAILED
    elif isinstance(exc, TextGenerationTimeoutError):
        code = OperationalErrorCode.TEXT_GENERATION_TIMEOUT
    elif isinstance(exc, TextGenerationError):
        code = OperationalErrorCode.TEXT_GENERATION_FAILED
    elif isinstance(exc, DerivativeTooLongError):
        code = OperationalErrorCode.ARTIFACT_TOO_LONG
    elif isinstance(exc, DerivativeTooLargeError):
        code = OperationalErrorCode.ARTIFACT_TOO_LARGE
    elif isinstance(exc, DerivativeExportError):
        code = OperationalErrorCode.ARTIFACT_EXPORT_FAILED
    elif isinstance(exc, OperationCanceledError):
        code = OperationalErrorCode.OPERATION_CANCELLED
    elif isinstance(exc, YouTubeError):
        code = OperationalErrorCode.YOUTUBE_PROVIDER_FAILURE
    elif isinstance(exc, OSError):
        code = OperationalErrorCode.INTERNAL_IO_FAILURE
    else:
        code = OperationalErrorCode.INTERNAL_INVARIANT_VIOLATION

    detail_source: BaseException = exc.__cause__ if exc.__cause__ is not None else exc
    context = {"exception_type": type(exc).__name__}
    if detail_source is not exc:
        context["cause_exception_type"] = type(detail_source).__name__
    if sanitizer is not None:
        detail = sanitizer(str(detail_source)).strip()
        if detail:
            context["detail"] = detail
    return error_for_code(code, technical_context=context)


__all__ = [
    "LanguageNotAllowedError",
    "MediaDurationUnknownError",
    "NoAudioAvailableError",
    "OperationalError",
    "OperationalErrorCategory",
    "OperationalErrorCode",
    "PipelineRejectionError",
    "VideoTooLongError",
    "classify_operational_error",
    "error_for_code",
]
