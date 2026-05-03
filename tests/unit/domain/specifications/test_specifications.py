"""Testes das especificações."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.domain.specifications.concrete import (
    DurationWithinLimit,
    HasEnoughSpeech,
    LanguageAllowed,
    UrlIsYoutube,
)
from yt_transcriber_bot.domain.specifications.specification import Specification
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language


class _AlwaysTrue(Specification[int]):
    def is_satisfied_by(self, candidate: int) -> bool:
        return True


class _AlwaysFalse(Specification[int]):
    def is_satisfied_by(self, candidate: int) -> bool:
        return False


class TestSpecificationCombination:
    def test_and_both_true(self) -> None:
        spec = _AlwaysTrue() & _AlwaysTrue()
        assert spec.is_satisfied_by(1)

    def test_and_one_false(self) -> None:
        spec = _AlwaysTrue() & _AlwaysFalse()
        assert not spec.is_satisfied_by(1)

    def test_or_both_false(self) -> None:
        spec = _AlwaysFalse() | _AlwaysFalse()
        assert not spec.is_satisfied_by(1)

    def test_or_one_true(self) -> None:
        spec = _AlwaysFalse() | _AlwaysTrue()
        assert spec.is_satisfied_by(1)

    def test_not_inverts(self) -> None:
        spec = ~_AlwaysTrue()
        assert not spec.is_satisfied_by(1)


class TestUrlIsYoutube:
    def test_accepts_valid_watch_url(self) -> None:
        assert UrlIsYoutube().is_satisfied_by("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_accepts_short_url(self) -> None:
        assert UrlIsYoutube().is_satisfied_by("https://youtu.be/dQw4w9WgXcQ")

    def test_rejects_invalid_url(self) -> None:
        assert not UrlIsYoutube().is_satisfied_by("https://www.vimeo.com/12345")

    def test_rejects_random_text(self) -> None:
        assert not UrlIsYoutube().is_satisfied_by("ola tudo bem?")

    def test_rejects_empty(self) -> None:
        assert not UrlIsYoutube().is_satisfied_by("")


class TestLanguageAllowed:
    def test_accepts_listed_language(self) -> None:
        spec = LanguageAllowed(frozenset({Language.pt(), Language.en()}))
        assert spec.is_satisfied_by(Language.pt())

    def test_rejects_unlisted_language(self) -> None:
        spec = LanguageAllowed(frozenset({Language.pt()}))
        assert not spec.is_satisfied_by(Language.en())

    def test_empty_allowlist_raises(self) -> None:
        with pytest.raises(ValueError, match="vazia"):
            LanguageAllowed(frozenset())


class TestDurationWithinLimit:
    def test_below_limit_accepted(self) -> None:
        spec = DurationWithinLimit(Duration.from_minutes(180))
        assert spec.is_satisfied_by(Duration.from_minutes(60))

    def test_at_limit_accepted(self) -> None:
        spec = DurationWithinLimit(Duration.from_minutes(180))
        assert spec.is_satisfied_by(Duration.from_minutes(180))

    def test_above_limit_rejected(self) -> None:
        spec = DurationWithinLimit(Duration.from_minutes(180))
        assert not spec.is_satisfied_by(Duration.from_minutes(181))


class TestHasEnoughSpeech:
    def test_above_threshold_accepted(self) -> None:
        spec = HasEnoughSpeech(min_ratio=0.3)
        assert spec.is_satisfied_by(0.5)

    def test_below_threshold_rejected(self) -> None:
        spec = HasEnoughSpeech(min_ratio=0.3)
        assert not spec.is_satisfied_by(0.2)

    def test_at_threshold_accepted(self) -> None:
        spec = HasEnoughSpeech(min_ratio=0.3)
        assert spec.is_satisfied_by(0.3)

    def test_threshold_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match=r"\[0,1\]"):
            HasEnoughSpeech(min_ratio=1.5)


class TestComposedSpecifications:
    def test_combining_url_and_language(self) -> None:
        url_spec = UrlIsYoutube()
        # Não há sentido combinar essas duas com mesmo tipo, mas validamos o mecanismo:
        composed = url_spec & UrlIsYoutube()
        assert composed.is_satisfied_by("https://youtu.be/dQw4w9WgXcQ")
