from __future__ import annotations

import pytest

from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.operational_errors import (
    LanguageNotAllowedError,
    NoAudioAvailableError,
    OperationalErrorCategory,
    OperationalErrorCode,
    VideoTooLongError,
    classify_operational_error,
    error_for_code,
)
from yt_transcriber_bot.application.ports.diarization_engine import DiarizationUnavailableError
from yt_transcriber_bot.application.ports.transcription_engine import (
    ObservedLanguageNotAllowedError,
    OutOfMemoryError,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    AgeRestrictedError,
    MembersOnlyError,
    VideoUnavailableError,
)


@pytest.mark.parametrize(
    ("exc", "code", "category", "retryable"),
    [
        (
            MembersOnlyError("members only"),
            OperationalErrorCode.YOUTUBE_AUTH_REQUIRED,
            OperationalErrorCategory.ACCESS,
            False,
        ),
        (
            AgeRestrictedError("age restricted"),
            OperationalErrorCode.YOUTUBE_AUTH_REQUIRED,
            OperationalErrorCategory.ACCESS,
            False,
        ),
        (
            VideoUnavailableError("private video"),
            OperationalErrorCode.YOUTUBE_VIDEO_UNAVAILABLE,
            OperationalErrorCategory.ACCESS,
            False,
        ),
        (
            NoAudioAvailableError("provider detail"),
            OperationalErrorCode.YOUTUBE_NO_AUDIO_STREAM,
            OperationalErrorCategory.MEDIA,
            False,
        ),
        (
            VideoTooLongError("200 min"),
            OperationalErrorCode.MEDIA_DURATION_EXCEEDED,
            OperationalErrorCategory.MEDIA,
            False,
        ),
        (
            LanguageNotAllowedError("opaque-language-detail"),
            OperationalErrorCode.MEDIA_LANGUAGE_NOT_ALLOWED,
            OperationalErrorCategory.MEDIA,
            False,
        ),
        (
            OutOfMemoryError("cuda oom"),
            OperationalErrorCode.TRANSCRIPTION_OUT_OF_MEMORY,
            OperationalErrorCategory.TRANSCRIPTION,
            True,
        ),
        (
            ObservedLanguageNotAllowedError("opaque-observed-language-detail"),
            OperationalErrorCode.TRANSCRIPTION_LANGUAGE_NOT_ALLOWED,
            OperationalErrorCategory.TRANSCRIPTION,
            False,
        ),
        (
            DiarizationUnavailableError("provider unavailable"),
            OperationalErrorCode.DIARIZATION_UNAVAILABLE,
            OperationalErrorCategory.DIARIZATION,
            True,
        ),
        (
            OperationCanceledError("opaque-cancellation-detail"),
            OperationalErrorCode.OPERATION_CANCELLED,
            OperationalErrorCategory.OPERATION,
            False,
        ),
        (
            RuntimeError("unexpected"),
            OperationalErrorCode.INTERNAL_INVARIANT_VIOLATION,
            OperationalErrorCategory.INTERNAL,
            False,
        ),
    ],
)
def test_operational_error_classification_is_stable(
    exc: BaseException,
    code: OperationalErrorCode,
    category: OperationalErrorCategory,
    retryable: bool,
) -> None:
    error = classify_operational_error(exc)
    assert error.code is code
    assert error.category is category
    assert error.retryable is retryable
    assert error.safe_message
    assert str(exc) not in error.safe_message


def test_technical_context_is_sanitized_only_when_explicit_sanitizer_is_supplied() -> None:
    raw = "authorization: Bearer super-secret-token"
    error = classify_operational_error(
        RuntimeError(raw),
        sanitizer=lambda text: text.replace("super-secret-token", "[REDACTED]"),
    )
    assert error.technical_context["exception_type"] == "RuntimeError"
    assert "super-secret-token" not in error.technical_context["detail"]
    assert "[REDACTED]" in error.technical_context["detail"]
    assert raw not in error.safe_message


def test_delivery_error_has_stable_retryable_contract() -> None:
    error = error_for_code(OperationalErrorCode.DELIVERY_FAILED)
    assert error.category is OperationalErrorCategory.DELIVERY
    assert error.retryable is True
    assert error.safe_message
