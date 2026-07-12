"""Inspeção local de duração para documentos Telegram sem metadados."""

from __future__ import annotations

import subprocess
from math import ceil, isfinite
from pathlib import Path

from yt_transcriber_bot.application.ports.incoming_media import AudioDurationInspector


class FfprobeAudioDurationInspector(AudioDurationInspector):
    def duration_seconds(self, path: Path) -> int:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=15.0,
            )
            duration = float(result.stdout.strip())
            if not isfinite(duration) or duration <= 0:
                raise ValueError("duração inválida")
            return ceil(duration)
        except (OverflowError, ValueError, subprocess.SubprocessError) as exc:
            raise ValueError("Não foi possível validar a duração do áudio.") from exc
