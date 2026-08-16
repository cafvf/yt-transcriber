"""Implementação de ``AudioConverter`` baseada em ``ffmpeg``.

Usa a CLI do ffmpeg via ``subprocess`` (sem ``ffmpeg-python`` para reduzir
superfície de dependência). Toda a interação com o processo é feita por
um ``CommandRunner`` injetável, permitindo testes determinísticos.
"""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from yt_transcriber_bot.application.cancellation import OperationCanceledError, raise_if_cancelled
from yt_transcriber_bot.application.ports.audio_converter import (
    AudioConversionError,
    AudioConverter,
    ConvertedAudio,
)


@dataclass(frozen=True)
class CompletedRun:
    """Resultado de um processo executado pelo runner."""

    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(
        self,
        args: Sequence[str],
        *,
        cancel_event: threading.Event | None = None,
    ) -> CompletedRun: ...


class SubprocessCommandRunner:
    """Implementação real de ``CommandRunner`` usando ``subprocess.run``."""

    def run(
        self,
        args: Sequence[str],
        *,
        cancel_event: threading.Event | None = None,
    ) -> CompletedRun:
        if cancel_event is None:
            completed = subprocess.run(
                list(args),
                capture_output=True,
                text=True,
                check=False,
            )
            return CompletedRun(
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        raise_if_cancelled(cancel_event)
        process = subprocess.Popen(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while process.poll() is None:
            if cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
                raise OperationCanceledError("Processo ffmpeg cancelado pelo usuário")
            time.sleep(0.05)
        stdout, stderr = process.communicate()
        return CompletedRun(returncode=process.returncode, stdout=stdout, stderr=stderr)


class FfmpegAudioConverter(AudioConverter):
    """Converte áudios para Opus/OGG mono com perfil voip.

    O perfil ``voip`` do encoder libopus é otimizado para fala e oferece
    excelente inteligibilidade em bitrates muito baixos (16 a 32 kbps).
    """

    def __init__(
        self,
        runner: CommandRunner | None = None,
        *,
        ffmpeg_bin: str = "ffmpeg",
    ) -> None:
        self._runner: CommandRunner = runner or SubprocessCommandRunner()
        self._ffmpeg = ffmpeg_bin

    # ------------------------------------------------------------------
    # Conversão principal
    # ------------------------------------------------------------------

    def convert_to_opus_mono(
        self,
        source: Path,
        dest: Path,
        *,
        bitrate_kbps: int = 32,
        sample_rate_hz: int = 16000,
        cancel_event: threading.Event | None = None,
    ) -> ConvertedAudio:
        raise_if_cancelled(cancel_event)
        if not source.exists():
            raise AudioConversionError(f"Arquivo de origem não existe: {source}")
        if bitrate_kbps < 16 or bitrate_kbps > 128:
            raise AudioConversionError(f"bitrate_kbps fora da faixa [16, 128]: {bitrate_kbps}")
        if sample_rate_hz not in (8000, 12000, 16000, 24000, 48000):
            raise AudioConversionError(f"sample_rate_hz inválido para Opus: {sample_rate_hz}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()

        args = [
            self._ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate_hz),
            "-c:a",
            "libopus",
            "-application",
            "voip",
            "-b:a",
            f"{bitrate_kbps}k",
            str(dest),
        ]
        try:
            result = self._runner.run(args, cancel_event=cancel_event)
        except OperationCanceledError:
            if dest.exists():
                dest.unlink(missing_ok=True)
            raise
        if result.returncode != 0:
            raise AudioConversionError(
                f"ffmpeg retornou {result.returncode}: {result.stderr.strip()[:500]}"
            )
        if not dest.exists() or dest.stat().st_size == 0:
            raise AudioConversionError(f"ffmpeg terminou OK mas arquivo de destino vazio: {dest}")

        return ConvertedAudio(
            path=dest,
            bitrate_kbps=bitrate_kbps,
            sample_rate_hz=sample_rate_hz,
            channels=1,
            container="ogg",
            size_bytes=dest.stat().st_size,
        )
