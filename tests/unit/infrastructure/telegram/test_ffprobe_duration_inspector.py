"""Regressões para a inspeção de duração de mídia Telegram."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from yt_transcriber_bot.infrastructure.telegram.ffprobe_duration_inspector import (
    FfprobeAudioDurationInspector,
)

_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


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


@pytest.mark.integration
@pytest.mark.skipif(
    not _FFMPEG_AVAILABLE,
    reason="ffmpeg/ffprobe não disponíveis para contrato real de duração",
)
def test_real_ffprobe_duration_inspector(tmp_path: Path) -> None:
    """Preserva o papel durável do terceiro contrato ffmpeg/ffprobe do baseline."""
    source = tmp_path / "duration-contract.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert FfprobeAudioDurationInspector().duration_seconds(source) == 2
