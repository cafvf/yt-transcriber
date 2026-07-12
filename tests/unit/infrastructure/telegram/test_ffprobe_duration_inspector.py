"""Regressões para a inspeção de duração de mídia Telegram."""

from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path

import pytest

from yt_transcriber_bot.infrastructure.telegram.ffprobe_duration_inspector import (
    FfprobeAudioDurationInspector,
)


def test_ffprobe_uses_a_finite_subprocess_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observed: dict[str, object] = {}

    def run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs)
        return subprocess.CompletedProcess([], 0, stdout="12.1\n", stderr="")

    monkeypatch.setattr(subprocess, "run", run)

    assert FfprobeAudioDurationInspector().duration_seconds(tmp_path / "audio.wav") == 13
    assert isinstance(observed.get("timeout"), float)
    assert observed["timeout"] > 0


@pytest.mark.asyncio
async def test_duration_inspection_does_not_block_the_event_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        time.sleep(0.1)
        return subprocess.CompletedProcess([], 0, stdout="12.1\n", stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    inspector = FfprobeAudioDurationInspector()
    completed = asyncio.Event()

    async def tick() -> None:
        await asyncio.sleep(0.01)
        completed.set()

    inspection = asyncio.to_thread(inspector.duration_seconds, tmp_path / "audio.wav")
    await asyncio.gather(inspection, tick())
    assert completed.is_set()
