"""Testes do value object ``Slug``."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.domain.value_objects.slug import Slug


class TestSlugFromTitle:
    def test_handles_accents(self) -> None:
        assert Slug.from_title("Não vou.").value == "nao-vou"

    def test_handles_uppercase(self) -> None:
        assert Slug.from_title("HELLO World").value == "hello-world"

    def test_handles_emoji_and_special_chars(self) -> None:
        slug = Slug.from_title("Olha 🎉 isso aqui!")
        assert slug.value == "olha-isso-aqui"

    def test_handles_only_special_chars_falls_back_to_untitled(self) -> None:
        slug = Slug.from_title("🎉🎊✨")
        assert slug.value == "untitled"

    def test_handles_multiple_spaces(self) -> None:
        slug = Slug.from_title("uma   palavra    longa")
        assert slug.value == "uma-palavra-longa"

    def test_truncates_long_titles_at_safe_limit(self) -> None:
        title = "a" * 200
        slug = Slug.from_title(title)
        assert len(slug.value) <= 80

    def test_truncation_preserves_word_boundary(self) -> None:
        title = "palavra " * 30
        slug = Slug.from_title(title)
        assert not slug.value.endswith("-")
        assert "palavra" in slug.value

    def test_empty_title_raises(self) -> None:
        with pytest.raises(ValueError, match="vazio"):
            Slug.from_title("")

    def test_whitespace_only_title_raises(self) -> None:
        with pytest.raises(ValueError, match="vazio"):
            Slug.from_title("   ")

    def test_handles_portuguese_accents_correctly(self) -> None:
        assert Slug.from_title("Coração & Alma").value == "coracao-alma"

    def test_handles_numbers(self) -> None:
        assert Slug.from_title("Episódio 42 — Parte 3").value == "episodio-42-parte-3"


class TestSlugConstruction:
    def test_construction_with_valid_value_succeeds(self) -> None:
        assert Slug(value="hello-world").value == "hello-world"

    def test_empty_slug_raises(self) -> None:
        with pytest.raises(ValueError, match="vazio"):
            Slug(value="")

    def test_oversized_slug_raises(self) -> None:
        with pytest.raises(ValueError, match="máximo"):
            Slug(value="a" * 100)

    def test_slug_is_immutable(self) -> None:
        slug = Slug(value="hello")
        with pytest.raises(Exception):  # noqa: B017,PT011
            slug.value = "other"  # type: ignore[misc]


class TestSlugWithSuffix:
    def test_appends_numeric_suffix(self) -> None:
        slug = Slug(value="hello-world")
        assert slug.with_suffix(2).value == "hello-world-2"

    def test_collision_appends_suffix_to_long_slug(self) -> None:
        long_slug = Slug(value="a" * 79)
        with_suffix = long_slug.with_suffix(2)
        assert len(with_suffix.value) <= 80
        assert with_suffix.value.endswith("-2")

    def test_negative_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="positivo"):
            Slug(value="hello").with_suffix(-1)

    def test_zero_suffix_raises(self) -> None:
        with pytest.raises(ValueError, match="positivo"):
            Slug(value="hello").with_suffix(0)


class TestSlugMethods:
    def test_str_returns_value(self) -> None:
        assert str(Slug(value="hello")) == "hello"

    def test_equality_by_value(self) -> None:
        assert Slug(value="x") == Slug(value="x")
        assert Slug(value="x") != Slug(value="y")
