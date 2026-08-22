"""PLAN-007 Gate A2 conformance for canonical media metadata taxonomy."""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"
ENTITIES_ROOT = SRC_ROOT / "domain" / "entities"

_LEGACY_SYMBOL = "Video" + "Metadata"
_LEGACY_MODULE = "video_" + "metadata"


def test_media_metadata_is_owned_by_canonical_module() -> None:
    assert MediaMetadata.__module__.endswith(".media_metadata")
    assert not (ENTITIES_ROOT / f"{_LEGACY_MODULE}.py").exists()


def test_legacy_media_metadata_vocabulary_is_absent_from_core_source() -> None:
    violations: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _LEGACY_SYMBOL in text or _LEGACY_MODULE in text:
            violations.append(path.relative_to(REPO_ROOT).as_posix())

    assert not violations, f"legacy media metadata vocabulary remains: {violations!r}"
