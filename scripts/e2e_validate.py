"""Script E2E de validação do pipeline (sem Telegram, conforme Dúvida 47).

Este script substitui o ``YouTubeDownloader`` real (bloqueado pelo IP do
sandbox) por um *stub* que entrega um WAV pré-baixado, mantendo todos os
demais componentes reais — transcrição com WhisperX e (se possível) diarização
com pyannote. Quando ``HF_TOKEN`` não estiver disponível, a diarização é
substituída por um stub determinístico com 2 falantes alternados, o que ainda
exercita o caminho de render do Markdown e a lógica de turnos.

Uso:
    uv run python scripts/e2e_validate.py /tmp/ami_2min.wav

Saída esperada:
- arquivo .md em data/transcripts/
- arquivo .ogg em data/processed/
- log em data/logs/
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Garantir que o pacote esteja no path quando executado pelo uv run
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationResult,
    DiarizedSpeakerSegment,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    DownloadedAudio,
    FetchedSubtitle,
    SubtitleTrack,
    YouTubeDownloader,
)
from yt_transcriber_bot.application.use_cases.transcribe_video import (
    TranscribeVideoDependencies,
    TranscribeVideoUseCase,
)
from yt_transcriber_bot.composition_root import build
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class StubYouTubeDownloader(YouTubeDownloader):
    """Devolve um WAV pré-baixado como se viesse do YouTube."""

    def __init__(self, video_id: VideoId, audio_path: Path, title: str) -> None:
        self._vid = video_id
        self._audio_path = audio_path
        self._title = title

    def fetch_metadata(self, video_id: VideoId) -> VideoMetadata:
        return VideoMetadata(
            video_id=self._vid,
            title=self._title,
            channel="AMI Corpus (E2E sandbox)",
            duration=Duration.from_seconds(120),
            upload_date=date(2005, 1, 1),
            original_language=Language("en"),
        )

    def list_subtitles(self, video_id: VideoId) -> tuple[SubtitleTrack, ...]:
        return ()  # nada de legenda — força transcrição real

    def fetch_subtitle(
        self, video_id: VideoId, track: SubtitleTrack
    ) -> FetchedSubtitle:
        raise NotImplementedError

    def download_audio(
        self, video_id: VideoId, dest_dir: Path
    ) -> DownloadedAudio:
        # Copia o arquivo original para dest_dir mantendo o container
        import shutil

        dest = dest_dir / f"{self._vid.value}.wav"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._audio_path, dest)
        return DownloadedAudio(
            audio_path=dest,
            container="wav",
            used_alternate_track=False,
            metadata=self.fetch_metadata(video_id),
        )


class StubDiarizationEngine(DiarizationEngine):
    """Fallback determinístico (2 falantes alternados em blocos de 30s).

    Usado quando ``HF_TOKEN`` não estiver disponível. Permite exercitar o
    caminho completo de render do Markdown sem internet/pyannote.
    """

    def diarize(
        self,
        audio_path: Path,
        *,
        device: str,
        hf_token: str,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> DiarizationResult:
        from contextlib import suppress

        # Descobre duração via ffprobe se possível, senão assume 120s
        dur = 120.0
        with suppress(Exception):
            import subprocess

            out = subprocess.check_output(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0",
                    str(audio_path),
                ],
                text=True,
            )
            dur = float(out.strip())

        block = 30.0
        segs = []
        t = 0.0
        i = 0
        while t < dur:
            end = min(t + block, dur)
            label = f"SPEAKER_{i % 2:02d}"
            segs.append(
                DiarizedSpeakerSegment(
                    start_seconds=t, end_seconds=end, speaker_label=label
                )
            )
            t = end
            i += 1
        return DiarizationResult(
            speaker_segments=tuple(segs), total_speakers=2
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E sandbox validator")
    parser.add_argument("audio", type=Path, help="WAV ou MP3 pré-baixado")
    parser.add_argument(
        "--video-id",
        default="j2p8p7cg0q8",
        help="Video ID (default: j2p8p7cg0q8 — link de teste do usuário)",
    )
    parser.add_argument(
        "--title",
        default="E2E sandbox sample (AMI corpus, primeiros 2 minutos)",
    )
    parser.add_argument(
        "--use-real-diarization",
        action="store_true",
        help="Usar pyannote real (exige HF_TOKEN)",
    )
    args = parser.parse_args()

    if not args.audio.exists():
        sys.stderr.write(f"Arquivo nao encontrado: {args.audio}\n")
        return 2

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # AppSettings minimal — não exigimos os secrets para este E2E
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "dummy")
    os.environ.setdefault("TELEGRAM_ALLOWED_USER_ID", "0")
    os.environ.setdefault("HF_TOKEN", "dummy")
    os.environ.setdefault("DEVICE", "cpu")
    os.environ.setdefault("WHISPER_MODEL", "tiny")  # rápido em CPU
    os.environ.setdefault("COMPUTE_TYPE", "int8")

    settings = AppSettings()

    # Constrói composition padrão e troca downloader/diarization
    composition = build(settings)

    video_id = VideoId(args.video_id)
    stub_downloader = StubYouTubeDownloader(video_id, args.audio, args.title)

    diarization_engine = composition.use_case._deps.diarization_engine
    if not args.use_real_diarization or not os.environ.get("HF_TOKEN_REAL"):
        diarization_engine = StubDiarizationEngine()

    # Re-monta o use case com o downloader/diarization stubados
    new_deps = TranscribeVideoDependencies(
        downloader=stub_downloader,
        converter=composition.use_case._deps.converter,
        gpu_detector=composition.use_case._deps.gpu_detector,
        transcription_engine=composition.use_case._deps.transcription_engine,
        diarization_engine=diarization_engine,
        renderer=composition.use_case._deps.renderer,
        settings=settings,
        repository=composition.repository,
    )
    use_case = TranscribeVideoUseCase(new_deps)

    job = Job.new(
        video_id=video_id,
        user_id=0,
        config_signature="e2e-sandbox",
    )

    logger = logging.getLogger("e2e")
    logger.info("Iniciando E2E com %s", args.audio)

    def step_progress(name: str, event: str) -> None:
        logger.info("[step] %s: %s", name, event)

    def transcribe_progress(fraction: float, label: str = "") -> None:
        logger.info("[transcribe] %s%% %s", int(fraction * 100), label)

    result = use_case.execute(
        job,
        progress_step=step_progress,
        progress_transcribe=transcribe_progress,
    )

    logger.info("Status final: %s", result.job.status)
    if result.failure_reason:
        logger.error("Falha: %s", result.failure_reason)
        return 1
    if result.canceled:
        logger.warning("Cancelado")
        return 1
    logger.info("MD: %s", result.md_path)
    logger.info("Audio: %s", result.audio_path)
    if result.md_path:
        content = result.md_path.read_text(encoding="utf-8")
        sys.stdout.write("\n----- MD GERADO -----\n")
        sys.stdout.write(content[:2000])
        sys.stdout.write(
            "\n----- (truncado) -----\n" if len(content) > 2000 else "\n----- fim -----\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
