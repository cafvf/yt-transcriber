"""Exportação de vídeo MP4 com legenda selecionável.

A implementação gera uma faixa de legenda ``mov_text`` dentro do MP4, sem
queimar a legenda na imagem e sem reencodar vídeo/áudio. O fluxo parte do
snapshot já persistido, reutiliza o exportador SRT e baixa um MP4 muxado do
YouTube quando necessário.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.ports.canonical_transcript import CanonicalTranscriptStore
from yt_transcriber_bot.application.ports.derived_artifacts import (
    DerivativeExportError,
    DerivativeTooLargeError,
    DerivativeTooLongError,
)
from yt_transcriber_bot.application.services.sanitization import sanitize_text
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.exporting.transcript_exporter import (
    TranscriptExportService,
)


class _YDLLike(Protocol):
    def extract_info(self, url: str, download: bool = ...) -> dict[str, Any]: ...

    def __enter__(self) -> _YDLLike: ...

    def __exit__(self, *args: object) -> None: ...


class _YDLFactory(Protocol):
    def __call__(self, params: dict[str, Any]) -> _YDLLike: ...


CommandRunner = Callable[[list[str], float], subprocess.CompletedProcess[str]]


class VideoSubtitleExportError(DerivativeExportError):
    """Erro genérico ao gerar vídeo com legenda selecionável."""


class VideoSubtitleTooLongError(DerivativeTooLongError, VideoSubtitleExportError):
    """Vídeo excede o limite de duração configurado."""


class VideoSubtitleTooLargeError(DerivativeTooLargeError, VideoSubtitleExportError):
    """Vídeo excede o limite de tamanho configurado."""


@dataclass(frozen=True)
class VideoSubtitleExportLimits:
    """Limites operacionais para exportação de vídeo legendado."""

    max_duration_seconds: int = 30 * 60
    max_size_bytes: int = 200 * 1024 * 1024


@dataclass(frozen=True)
class VideoSubtitleExportResult:
    """Resultado da geração de vídeo com faixa de legenda selecionável."""

    path: Path
    subtitle_path: Path
    source_video_path: Path
    size_bytes: int


class VideoSoftSubtitleExportService:
    """Gera MP4 com legenda selecionável a partir de um snapshot.

    A legenda é embutida como ``mov_text``. Isso permite ligar/desligar a
    legenda em players compatíveis e evita o custo de reencodificação do vídeo.
    """

    def __init__(
        self,
        *,
        snapshots: CanonicalTranscriptStore,
        transcript_exporter: TranscriptExportService,
        ydl_factory: _YDLFactory,
        output_dir: Path,
        limits: VideoSubtitleExportLimits | None = None,
        socket_timeout_s: float = 30.0,
        command_timeout_s: float = 120.0,
        cookies_file: str | None = None,
        cookies_browser: str | None = None,
        ffmpeg_bin: str = "ffmpeg",
        command_runner: CommandRunner | None = None,
        error_sanitizer: Callable[[str], str] | None = None,
    ) -> None:
        self._snapshots = snapshots
        self._transcript_exporter = transcript_exporter
        self._ydl_factory = ydl_factory
        self._output_dir = output_dir
        self._limits = limits or VideoSubtitleExportLimits()
        if socket_timeout_s <= 0:
            raise ValueError("socket_timeout_s deve ser > 0")
        if command_timeout_s <= 0:
            raise ValueError("command_timeout_s deve ser > 0")
        self._socket_timeout_s = float(socket_timeout_s)
        self._command_timeout_s = float(command_timeout_s)
        self._cookies_file = cookies_file or None
        self._cookies_browser = cookies_browser or None
        self._ffmpeg_bin = ffmpeg_bin
        self._command_runner = command_runner or _run_command
        self._error_sanitizer = error_sanitizer or sanitize_text

    def export(
        self,
        *,
        video_id: VideoId,
        slug: str,
        speaker_aliases: Mapping[str, str] | None = None,
    ) -> VideoSubtitleExportResult:
        snap = self._snapshots.load(slug)
        if snap is None:
            raise FileNotFoundError(f"Snapshot inexistente: {slug}")
        if snap.metadata.duration is None:
            raise VideoSubtitleExportError(
                "Snapshot sem duração conhecida; não é seguro validar o limite do vídeo."
            )
        duration_s = snap.metadata.duration.total_seconds
        if duration_s > self._limits.max_duration_seconds:
            raise VideoSubtitleTooLongError(
                "Vídeo longo demais para exportação com legenda selecionável: "
                f"{_format_minutes(duration_s)} min. Limite: "
                f"{_format_minutes(self._limits.max_duration_seconds)} min."
            )

        work_dir = self._output_dir / slug
        work_dir.mkdir(parents=True, exist_ok=True)
        subtitle = self._transcript_exporter.export(
            slug=slug,
            output_base_path=work_dir / slug,
            format="srt",
            speaker_aliases=speaker_aliases,
        ).path
        source_video = self._download_video(video_id=video_id, work_dir=work_dir)
        self._assert_size_ok(source_video, kind="vídeo baixado")
        output = work_dir / f"{slug}-legendas-selecionaveis.mp4"
        self._mux_soft_subtitles(source_video=source_video, subtitle=subtitle, output=output)
        if not output.is_file():
            raise VideoSubtitleExportError("ffmpeg não gerou o arquivo de vídeo final")
        self._assert_size_ok(output, kind="vídeo final")
        return VideoSubtitleExportResult(
            path=output,
            subtitle_path=subtitle,
            source_video_path=source_video,
            size_bytes=output.stat().st_size,
        )

    def _download_video(self, *, video_id: VideoId, work_dir: Path) -> Path:
        outtmpl = str(work_dir / f"{video_id.value}.%(ext)s")
        params: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": False,
            "ignoreconfig": True,
            # Preferimos MP4 progressivo com áudio/vídeo para simplificar o mux
            # da faixa de legenda. O formato 18 é pequeno e compatível, bom para
            # Telegram e para o limite de 200 MB.
            "format": "18/22/best[ext=mp4][acodec!=none][vcodec!=none]/best[acodec!=none][vcodec!=none]",
            "merge_output_format": "mp4",
            "outtmpl": outtmpl,
            "restrictfilenames": True,
            "socket_timeout": self._socket_timeout_s,
            "max_filesize": self._limits.max_size_bytes,
            "progress_hooks": [self._download_progress_hook],
        }
        if self._cookies_file:
            params["cookiefile"] = self._cookies_file
        if self._cookies_browser:
            params["cookiesfrombrowser"] = (self._cookies_browser,)
        try:
            with self._ydl_factory(params) as ydl:
                info = ydl.extract_info(video_id.canonical_url(), download=True)
        except VideoSubtitleTooLargeError:
            raise
        except Exception as exc:  # pragma: no cover - mapeamento defensivo
            raise VideoSubtitleExportError(
                f"Falha ao baixar vídeo para legendagem: {self._error_sanitizer(str(exc))}"
            ) from exc
        path = _extract_downloaded_video_path(info, work_dir, video_id)
        if path is None or not path.is_file():
            raise VideoSubtitleExportError("yt-dlp não retornou um arquivo de vídeo baixado")
        return path

    @staticmethod
    def _reported_bytes(value: object) -> int:
        if isinstance(value, int) and not isinstance(value, bool):
            return max(0, value)
        return 0

    def _download_progress_hook(self, status: dict[str, object]) -> None:
        observed = max(
            self._reported_bytes(status.get("downloaded_bytes")),
            self._reported_bytes(status.get("total_bytes")),
            self._reported_bytes(status.get("total_bytes_estimate")),
        )
        if observed > self._limits.max_size_bytes:
            raise VideoSubtitleTooLargeError(
                "Download do vídeo excede o limite configurado antes da conclusão: "
                f"{_format_mb(observed)} MB. Limite: "
                f"{_format_mb(self._limits.max_size_bytes)} MB."
            )

    def _mux_soft_subtitles(self, *, source_video: Path, subtitle: Path, output: Path) -> None:
        cmd = [
            self._ffmpeg_bin,
            "-y",
            "-i",
            str(source_video),
            "-i",
            str(subtitle),
            "-map",
            "0",
            "-map",
            "1:0",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=por",
            "-movflags",
            "+faststart",
            str(output),
        ]
        try:
            completed = self._command_runner(cmd, self._command_timeout_s)
        except subprocess.TimeoutExpired as exc:
            raise VideoSubtitleExportError(
                "ffmpeg excedeu o tempo máximo configurado para gerar o vídeo legendado"
            ) from exc
        if completed.returncode != 0:
            stderr = (completed.stderr or completed.stdout or "").strip()
            raise VideoSubtitleExportError(
                "ffmpeg falhou ao muxar a legenda selecionável"
                + (f": {self._error_sanitizer(stderr)}" if stderr else "")
            )

    def _assert_size_ok(self, path: Path, *, kind: str) -> None:
        size = path.stat().st_size
        if size > self._limits.max_size_bytes:
            raise VideoSubtitleTooLargeError(
                f"{kind.capitalize()} excede o limite configurado: "
                f"{_format_mb(size)} MB. Limite: {_format_mb(self._limits.max_size_bytes)} MB."
            )


def _run_command(cmd: list[str], timeout_s: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout_s)


def _extract_downloaded_video_path(
    info: dict[str, Any] | None, work_dir: Path, video_id: VideoId
) -> Path | None:
    if not info:
        return None
    candidates: list[Path] = []
    for item in info.get("requested_downloads") or []:
        if isinstance(item, dict):
            raw = item.get("filepath") or item.get("filename")
            if raw:
                candidates.append(Path(raw))
    for key in ("filepath", "_filename", "filename"):
        raw = info.get(key)
        if raw:
            candidates.append(Path(raw))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    for ext in ("mp4", "mkv", "webm"):
        candidate = work_dir / f"{video_id.value}.{ext}"
        if candidate.is_file():
            return candidate
    found = sorted(work_dir.glob(f"{video_id.value}.*"))
    return found[0] if found else None


def _format_minutes(seconds: float | int) -> str:
    return f"{float(seconds) / 60:.1f}"


def _format_mb(bytes_count: int) -> str:
    return f"{bytes_count / (1024 * 1024):.1f}"
