"""PLAN-007 Gate A1 taxonomy conformance for selected audio tracks."""

from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.domain.value_objects.audio_track import AudioTrackSelection

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"

_LEGACY_AUDIO_TRACK_NAMES = (
    "used_" + "alternate_track",
    "audio_track_" + "was_dubbed",
)


def test_audio_track_selection_distinguishes_truthful_states() -> None:
    assert AudioTrackSelection.ORIGINAL != AudioTrackSelection.DEFAULT
    assert AudioTrackSelection.DEFAULT != AudioTrackSelection.UNKNOWN
    assert AudioTrackSelection.ORIGINAL.value == "original"
    assert AudioTrackSelection.DEFAULT.value == "default"
    assert AudioTrackSelection.UNKNOWN.value == "unknown"


def test_legacy_audio_track_booleans_do_not_remain_in_core_source() -> None:
    violations: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(name in text for name in _LEGACY_AUDIO_TRACK_NAMES):
            violations.append(path.relative_to(REPO_ROOT).as_posix())

    assert not violations, f"legacy audio-track vocabulary remains in core: {violations!r}"
