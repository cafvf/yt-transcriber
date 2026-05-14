from __future__ import annotations

import html
import re

_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "�", "¤", "€", "™", "œ", "€�", "€¦")
_PORTUGUESE_LETTERS = (
    "\u00e1\u00e0\u00e2\u00e3\u00e9\u00ea\u00ed\u00f3\u00f4\u00f5\u00fa\u00fc\u00e7"
)
_PORTUGUESE_LETTERS += (
    "\u00c1\u00c0\u00c2\u00c3\u00c9\u00ca\u00cd\u00d3\u00d4\u00d5\u00da\u00dc\u00c7"
)
_PORTUGUESE_CHARS = set(_PORTUGUESE_LETTERS + "\u201c\u201d\u2018\u2019\u2026")
_COMMON_CP1252_SEQUENCES = {
    "\u00e2\u20ac\u0153": "\u201c",
    "\u00e2\u20ac\ufffd": "\u201d",
    "\u00e2\u20ac\x9d": "\u201d",
    "\u00e2\u20ac\u02dc": "\u2018",
    "\u00e2\u20ac\u2122": "\u2019",
    "\u00e2\u20ac\u00a6": "\u2026",
    "\u00e2\u20ac\u201c": "\u2013",
    "\u00e2\u20ac\u201d": "\u2014",
}
_COMMON_LATIN1_UTF8_SEQUENCES = {
    char.encode("utf-8").decode("latin-1"): char for char in _PORTUGUESE_LETTERS
}


def normalize_artifact_text(text: str) -> str:
    """Normaliza texto vindo de snapshots/subtitles para artefatos legíveis."""

    for _ in range(3):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    text = _repair_mojibake(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _repair_mojibake(text: str) -> str:
    """Repara mojibake UTF-8 lido como Latin-1/Windows-1252.

    A correção é conservadora: só aceita a recodificação quando os marcadores
    clássicos de mojibake diminuem e o resultado não introduz mais caracteres
    de substituição. Texto UTF-8 já correto normalmente não contém os marcadores
    e permanece inalterado.
    """

    original_markers = _marker_count(text)
    if original_markers == 0:
        return text
    best = _replace_common_mojibake_sequences(_remove_stray_latin1_markers(text))
    best_key = _repair_score(text, best)
    sources = (text, best)
    for source in sources:
        for encoding in ("cp1252", "latin-1"):
            try:
                candidate = source.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
            candidate = _replace_common_mojibake_sequences(_remove_stray_latin1_markers(candidate))
            key = _repair_score(text, candidate)
            if key > best_key:
                best = candidate
                best_key = key
    return best


def _replace_common_mojibake_sequences(text: str) -> str:
    replacements = _COMMON_CP1252_SEQUENCES | _COMMON_LATIN1_UTF8_SEQUENCES
    for mojibake, replacement in replacements.items():
        text = text.replace(mojibake, replacement)
    return text


def _remove_stray_latin1_markers(text: str) -> str:
    """Remove ``Â`` órfão antes de espaços/pontuação sem tocar em palavras válidas."""

    return re.sub(r"Â(?=[\s\.,;:!?\)\]\}])", "", text)


def _repair_score(original: str, candidate: str) -> tuple[int, int, int, int]:
    marker_delta = _marker_count(original) - _marker_count(candidate)
    replacement_delta = original.count("�") - candidate.count("�")
    portuguese_delta = _portuguese_score(candidate) - _portuguese_score(original)
    length_penalty = -abs(len(candidate) - len(original))
    return (marker_delta, replacement_delta, portuguese_delta, length_penalty)


def _marker_count(text: str) -> int:
    return sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)


def _portuguese_score(text: str) -> int:
    return sum(1 for char in text if char in _PORTUGUESE_CHARS)
