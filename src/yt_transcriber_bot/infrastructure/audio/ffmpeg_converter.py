"""Implementação de ``AudioConverter`` baseada em ``ffmpeg``.

Usa a CLI do ffmpeg via ``subprocess`` (sem ``ffmpeg-python`` para reduzir
superfície de dependência). Toda a interação com o processo é feita por
um ``CommandRunner`` injetável, permitindo testes determinísticos.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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
    def run(self, args: Sequence[str]) -> CompletedRun: ...


class SubprocessCommandRunner:
    """Implementação real de ``CommandRunner`` usando ``subprocess.run``."""

    def run(self, args: Sequence[str]) -> CompletedRun:
        proc = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            check=False,
        )
        return CompletedRun(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


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
        ffprobe_bin: str = "ffprobe",
    ) -> None:
        self._runner: CommandRunner = runner or SubprocessCommandRunner()
        self._ffmpeg = ffmpeg_bin
        self._ffprobe = ffprobe_bin

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
    ) -> ConvertedAudio:
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
        result = self._runner.run(args)
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

    # ------------------------------------------------------------------
    # Particionamento para Telegram
    # ------------------------------------------------------------------

    def split_for_telegram(
        self,
        source: Path,
        dest_dir: Path,
        *,
        max_size_bytes: int = 49 * 1024 * 1024,
    ) -> tuple[Path, ...]:
        if not source.exists():
            raise AudioConversionError(f"Arquivo não existe: {source}")
        size = source.stat().st_size
        if size <= max_size_bytes:
            return (source,)

        dest_dir.mkdir(parents=True, exist_ok=True)
        duration = self._probe_duration_seconds(source)
        if duration <= 0:
            raise AudioConversionError("ffprobe não conseguiu obter duração do áudio")

        ratio = size / max_size_bytes
        parts = max(2, int(ratio) + 1)
        chunk_seconds = duration / parts

        out_pattern = dest_dir / f"{source.stem}_part%03d{source.suffix}"
        args = [
            self._ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-c",
            "copy",
            "-f",
            "segment",
            "-segment_time",
            f"{chunk_seconds:.3f}",
            "-reset_timestamps",
            "1",
            str(out_pattern),
        ]
        result = self._runner.run(args)
        if result.returncode != 0:
            raise AudioConversionError(f"ffmpeg segment falhou: {result.stderr.strip()[:500]}")
        produced = sorted(dest_dir.glob(f"{source.stem}_part*{source.suffix}"))
        if not produced:
            raise AudioConversionError("Nenhuma parte foi produzida")
        return tuple(produced)

    # ------------------------------------------------------------------
    # ffprobe
    # ------------------------------------------------------------------

    def _probe_duration_seconds(self, path: Path) -> float:
        args = [
            self._ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ]
        result = self._runner.run(args)
        if result.returncode != 0:
            return 0.0
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return 0.0
        fmt = payload.get("format") or {}
        try:
            return float(fmt.get("duration") or 0.0)
        except (TypeError, ValueError):
            return 0.0
