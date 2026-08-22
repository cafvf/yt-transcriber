"""Gate A regressions for typed ProcessingProvenance."""

from __future__ import annotations

from typing import cast

import pytest

from yt_transcriber_bot.domain.value_objects.language import LanguageSource
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance


def test_language_source_is_typed_and_serializes_at_boundary() -> None:
    provenance = ProcessingProvenance(language_source=LanguageSource.ASR)

    assert provenance.language_source is LanguageSource.ASR
    assert provenance.as_dict()["language_source"] == "asr"


def test_persisted_language_source_is_decoded_to_enum() -> None:
    provenance = ProcessingProvenance.from_dict({"language_source": "asr"})

    assert provenance.language_source is LanguageSource.ASR


def test_unknown_persisted_language_source_does_not_fabricate_fact() -> None:
    provenance = ProcessingProvenance.from_dict({"language_source": "future-provider"})

    assert provenance.language_source is None


def test_raw_language_source_is_rejected_by_canonical_constructor() -> None:
    raw_value = cast(LanguageSource, "asr")

    with pytest.raises(TypeError, match="LanguageSource"):
        ProcessingProvenance(language_source=raw_value)
