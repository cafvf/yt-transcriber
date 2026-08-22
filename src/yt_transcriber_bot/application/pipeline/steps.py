"""Steps concretos do pipeline de transcrição.

Cada step implementa o padrão *Chain of Responsibility*: recebe o
``PipelineContext``, faz seu trabalho e o muta. Steps coordenam adaptadores
externos (downloader, converter, engines) através das portas, mantendo o
pipeline agnóstico das implementações concretas.
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from yt_transcriber_bot.application.cancellation import OperationCanceledError
from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.operational_errors import (
    LanguageNotAllowedError,
    MediaDurationUnknownError,
    NoAudioAvailableError,
    PipelineRejectionError,
    VideoTooLongError,
)
from yt_transcriber_bot.application.pipeline.context import PipelineContext
from yt_transcriber_bot.application.pipeline.runner import PipelineStep
from yt_transcriber_bot.application.ports.audio_converter import AudioConverter
from yt_transcriber_bot.application.ports.canonical_markdown import CanonicalMarkdownWriter
from yt_transcriber_bot.application.ports.canonical_transcript import (
    CanonicalTranscriptRecord,
    CanonicalTranscriptStore,
    TranscriptRenderContext,
)
from yt_transcriber_bot.application.ports.diarization_engine import (
    DiarizationEngine,
    DiarizationRequest,
    assign_speakers_to_segments,
)
from yt_transcriber_bot.application.ports.gpu_detector import GpuDetector
from yt_transcriber_bot.application.ports.transcript_renderer import (
    TranscriptRenderer,
    TranscriptRenderRequest,
)
from yt_transcriber_bot.application.ports.transcription_engine import (
    OutOfMemoryError,
    ProcessingTarget,
    TranscribedSegment,
    TranscriptionEngine,
    TranscriptionRequest,
)
from yt_transcriber_bot.application.ports.youtube_downloader import (
    NoAudioStreamError,
    SubtitleTrack,
    YouTubeDownloader,
)
from yt_transcriber_bot.application.runtime_selection import (
    RuntimePlan,
    select_runtime,
    smaller_model_alternative,
)
from yt_transcriber_bot.application.services.text_integrity import (
    normalize_artifact_text,
    text_has_unresolved_corruption,
)
from yt_transcriber_bot.domain.entities.job import JobStatus
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import (
    Transcript,
    TranscriptSegment,
)
from yt_transcriber_bot.domain.specifications.concrete import (
    DurationWithinLimit,
    LanguageAllowed,
)
from yt_transcriber_bot.domain.value_objects.compute_type import (
    ComputeKind,
    ComputeType,
)
from yt_transcriber_bot.domain.value_objects.device import Device
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language, LanguageSource
from yt_transcriber_bot.domain.value_objects.provenance import ProcessingProvenance
from yt_transcriber_bot.domain.value_objects.slug import Slug

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Erros do pipeline
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Step 1 — fetch metadata + validar duração + idioma
# ----------------------------------------------------------------------


class FetchMetadataStep(PipelineStep):
    """Carrega metadados do YouTube e valida regras (duração, idioma)."""

    @property
    def name(self) -> str:
        return "fetch_metadata"

    def __init__(
        self,
        downloader: YouTubeDownloader,
        settings: AppSettings,
    ) -> None:
        self._dl = downloader
        self._settings = settings

    def execute(self, ctx: PipelineContext) -> None:
        ctx.job.transition_to(JobStatus.ACQUIRING)
        ctx.started_at = datetime.now(UTC)
        assert ctx.job.video_id is not None
        meta = self._dl.fetch_metadata(ctx.job.video_id)
        ctx.metadata = meta

        if meta.duration is None:
            raise MediaDurationUnknownError(
                "Não foi possível estabelecer a duração da mídia antes do processamento caro."
            )
        max_seconds = int(self._settings.media_processing.max_media_duration_min) * 60
        if not DurationWithinLimit(Duration(seconds=max_seconds)).is_satisfied_by(meta.duration):
            raise VideoTooLongError(
                f"Duração {meta.duration.to_human()} excede o limite de "
                f"{self._settings.media_processing.max_media_duration_min} min"
            )

        allowed = frozenset(Language(code=c) for c in self._settings.allowed_languages)
        if ctx.requested_language is not None:
            requested = ctx.requested_language
            if not LanguageAllowed(allowed).is_satisfied_by(requested):
                raise LanguageNotAllowedError(
                    f"Idioma informado '{requested.code}' fora da allowlist "
                    f"{sorted(self._settings.allowed_languages)}"
                )
            ctx.transcription_language = requested
            ctx.language_source = LanguageSource.REQUESTED
            if meta.original_language is not None and meta.original_language.code != requested.code:
                ctx.add_diagnostic(
                    f"Idioma dos metadados: {meta.original_language.code}; "
                    f"usando idioma informado pelo usuário: {requested.code}."
                )
            else:
                ctx.add_diagnostic(f"Idioma informado pelo usuário: {requested.code}.")
        elif meta.original_language is not None:
            if not LanguageAllowed(allowed).is_satisfied_by(meta.original_language):
                raise LanguageNotAllowedError(
                    f"Idioma '{meta.original_language.code}' fora da allowlist "
                    f"{sorted(self._settings.allowed_languages)}"
                )
            # Usado para escolher legendas e modelo, mas a transcrição por áudio
            # continua livre para detectar o idioma no WhisperX.
            ctx.transcription_language = meta.original_language
            ctx.language_source = LanguageSource.METADATA
            ctx.add_diagnostic(f"Idioma inferido dos metadados: {meta.original_language.code}.")
        else:
            ctx.add_diagnostic("Idioma original indeterminado; deixando o WhisperX detectar.")

        if meta.has_alternate_audio_tracks:
            ctx.add_diagnostic("Vídeo tem dublagens alternativas; usando faixa original.")


# ----------------------------------------------------------------------
# Step 2 — tentar legendas existentes do YouTube
# ----------------------------------------------------------------------


class TryYouTubeSubtitlesStep(PipelineStep):
    """Se o YT já tem legendas no idioma original, salta a transcrição."""

    @property
    def name(self) -> str:
        return "try_youtube_subtitles"

    def __init__(
        self,
        downloader: YouTubeDownloader,
        settings: AppSettings,
    ) -> None:
        self._dl = downloader
        self._settings = settings

    def execute(self, ctx: PipelineContext) -> None:
        assert ctx.job.video_id is not None
        if not self._settings.prefer_youtube_subtitles:
            ctx.add_diagnostic("Legendas do YouTube desabilitadas pela config.")
            return
        meta = ctx.metadata
        if meta is None:
            return
        target_language = ctx.requested_language or meta.original_language
        if target_language is None:
            return

        try:
            tracks = self._dl.list_subtitles(ctx.job.video_id)
        except OperationCanceledError:
            raise
        except Exception:
            logger.warning("listagem de legendas falhou; usando fallback de áudio")
            ctx.add_diagnostic("Falha ao listar legendas; seguindo para aquisição de áudio.")
            return

        chosen = self._pick_best(tracks, target_language)
        if chosen is None:
            ctx.add_diagnostic("Sem legendas elegíveis no idioma original.")
            return

        try:
            fetched = self._dl.fetch_subtitle(
                ctx.job.video_id,
                chosen,
                cancel_event=ctx.cancel_event,
            )
        except OperationCanceledError:
            raise
        except Exception:
            logger.warning("download da legenda falhou; usando fallback de áudio")
            ctx.add_diagnostic("Falha ao baixar legenda; seguindo para aquisição de áudio.")
            return

        if not fetched.segments:
            ctx.add_diagnostic("Legenda baixada vazia; ignorando.")
            return

        normalized_segments = tuple(
            (
                float(start),
                float(end),
                normalize_artifact_text(str(text)),
            )
            for start, end, text in fetched.segments
        )
        if _subtitle_segments_have_unresolved_corruption(normalized_segments):
            ctx.add_diagnostic(
                "Legenda do YouTube rejeitada por integridade; baixando áudio e usando WhisperX."
            )
            return

        if chosen.is_auto_generated:
            quality = assess_auto_subtitle_quality(normalized_segments)
            ctx.add_diagnostic(f"Qualidade da legenda automática: {quality.summary()}")
            if not quality.accepted:
                ctx.add_diagnostic(
                    "Legenda automática rejeitada por qualidade; baixando áudio e usando WhisperX."
                )
                return

        # FetchedSubtitle.segments == tuple[(start, end, text)]
        ctx.transcribed_segments = tuple(
            TranscribedSegment(
                start_seconds=start,
                end_seconds=end,
                text=text,
            )
            for start, end, text in normalized_segments
        )
        ctx.transcription_language = target_language
        ctx.transcription_confidence = None
        ctx.youtube_subtitle_used = True
        subtitle_kind = "auto" if chosen.is_auto_generated else "manual"
        source = "youtube_auto" if chosen.is_auto_generated else "youtube_manual"
        ctx.language_source = (
            LanguageSource.YOUTUBE_AUTO
            if chosen.is_auto_generated
            else LanguageSource.YOUTUBE_MANUAL
        )
        source = ctx.language_source.value
        ctx.transcript = Transcript(
            segments=tuple(
                TranscriptSegment(
                    start_seconds=segment.start_seconds,
                    end_seconds=max(segment.end_seconds, segment.start_seconds),
                    text=segment.text,
                    speaker_label="SPEAKER_00",
                )
                for segment in ctx.transcribed_segments
                if segment.text.strip() and segment.end_seconds > segment.start_seconds
            ),
            language=target_language,
            language_confidence=None,
            source=source,
            requested_language=ctx.requested_language,
            observed_language=None,
            observed_language_confidence=None,
            language_source=ctx.language_source,
        )
        ctx.processing_provenance = ProcessingProvenance(
            processing_path="youtube_subtitle",
            language_source=ctx.language_source,
        )
        ctx.add_diagnostic(
            f"Usando legendas do YouTube ({subtitle_kind}, idioma={target_language})."
        )

    @staticmethod
    def _pick_best(
        tracks: tuple[SubtitleTrack, ...],
        original_language: Language,
    ) -> SubtitleTrack | None:
        candidates = [
            t for t in tracks if t.language.code == original_language.code and not t.is_translated
        ]
        if not candidates:
            return None
        manual = [t for t in candidates if not t.is_auto_generated]
        if manual:
            return manual[0]
        return candidates[0]


def _subtitle_segments_have_unresolved_corruption(
    segments: tuple[tuple[float, float, str], ...],
) -> bool:
    return any(text_has_unresolved_corruption(text) for _, _, text in segments if text.strip())


@dataclass(frozen=True)
class SubtitleQualityReport:
    """Resultado heurístico da avaliação de legenda automática."""

    accepted: bool
    reason: str
    word_count: int
    collapse_ratio: float
    high_overlap_ratio: float

    def summary(self) -> str:
        return (
            f"{self.reason} "
            f"(palavras={self.word_count}, collapse={self.collapse_ratio:.2f}, "
            f"sobreposição={self.high_overlap_ratio:.2f})"
        )


def assess_auto_subtitle_quality(
    segments: tuple[tuple[float, float, str], ...],
) -> SubtitleQualityReport:
    """Aceita/rejeita legendas automáticas antes de pular o WhisperX.

    Legendas automáticas do YouTube podem vir como janela rolante: cada cue
    repete parte do anterior. Se essa repetição sobreviver ao parser, a
    transcrição fica poluída em grandes blocos. A heurística é conservadora:
    só rejeita quando há evidência clara de repetição/overlap excessivo.
    """
    texts = [str(text).strip() for _, _, text in segments if str(text).strip()]
    all_words = " ".join(texts).split()
    word_count = len(all_words)
    if not texts:
        return SubtitleQualityReport(False, "sem texto útil", 0, 0.0, 0.0)
    if word_count < 20:
        return SubtitleQualityReport(True, "aceita: legenda curta", word_count, 1.0, 0.0)

    collapsed_words = _collapse_adjacent_repeated_words(all_words)
    collapse_ratio = len(collapsed_words) / max(word_count, 1)
    high_overlap_ratio = _consecutive_high_overlap_ratio(texts)

    if collapse_ratio < 0.82:
        return SubtitleQualityReport(
            False,
            "rejeitada: repetição interna excessiva",
            word_count,
            collapse_ratio,
            high_overlap_ratio,
        )
    if high_overlap_ratio > 0.35:
        return SubtitleQualityReport(
            False,
            "rejeitada: sobreposição excessiva entre cues",
            word_count,
            collapse_ratio,
            high_overlap_ratio,
        )
    return SubtitleQualityReport(
        True,
        "aceita",
        word_count,
        collapse_ratio,
        high_overlap_ratio,
    )


def _word_key(token: str) -> str:
    import re

    return re.sub(r"[^\wÀ-ÿ]+", "", token, flags=re.UNICODE).lower()


def _words_equal(left: list[str], right: list[str]) -> bool:
    if len(left) != len(right):
        return False
    return [_word_key(w) for w in left] == [_word_key(w) for w in right]


def _collapse_adjacent_repeated_words(
    words: list[str],
    *,
    max_phrase_words: int = 20,
) -> list[str]:
    if len(words) < 4:
        return words
    i = 0
    out: list[str] = []
    while i < len(words):
        matched = False
        max_k = min(max_phrase_words, (len(words) - i) // 2)
        for k in range(max_k, 1, -1):
            phrase = words[i : i + k]
            next_phrase = words[i + k : i + 2 * k]
            if _words_equal(phrase, next_phrase):
                out.extend(phrase)
                i += 2 * k
                while i + k <= len(words) and _words_equal(phrase, words[i : i + k]):
                    i += k
                matched = True
                break
        if not matched:
            out.append(words[i])
            i += 1
    return out


def _consecutive_high_overlap_ratio(texts: list[str]) -> float:
    if len(texts) < 2:
        return 0.0
    high = 0
    total = 0
    for prev, cur in itertools.pairwise(texts):
        prev_words = prev.split()
        cur_words = cur.split()
        if not prev_words or not cur_words:
            continue
        total += 1
        max_k = min(len(prev_words), len(cur_words), 30)
        overlap = 0
        for k in range(max_k, 0, -1):
            if _words_equal(prev_words[-k:], cur_words[:k]):
                overlap = k
                break
        if overlap / max(len(cur_words), 1) >= 0.50:
            high += 1
    return high / max(total, 1)


# ----------------------------------------------------------------------
# Step 3 — baixar audio
# ----------------------------------------------------------------------


class DownloadAudioStep(PipelineStep):
    """Baixa o áudio bruto do YouTube usando a porta YouTubeDownloader."""

    @property
    def name(self) -> str:
        return "download_audio"

    def __init__(
        self,
        downloader: YouTubeDownloader,
        downloads_dir: Path,
    ) -> None:
        self._dl = downloader
        self._downloads_dir = downloads_dir

    def should_run(self, ctx: PipelineContext) -> bool:
        return not ctx.youtube_subtitle_used

    def execute(self, ctx: PipelineContext) -> None:
        assert ctx.job.video_id is not None
        try:
            result = self._dl.download_audio(
                ctx.job.video_id,
                dest_dir=self._downloads_dir,
                cancel_event=ctx.cancel_event,
            )
        except NoAudioStreamError as exc:
            raise NoAudioAvailableError(
                "A mídia não possui uma faixa de áudio elegível para transcrição."
            ) from exc
        ctx.raw_audio_path = result.audio_path
        ctx.audio_track_selection = result.track_selection


class UseTelegramAudioStep(PipelineStep):
    """Usa o arquivo privado já baixado do Telegram como entrada do pipeline."""

    @property
    def name(self) -> str:
        return "use_telegram_audio"

    def execute(self, ctx: PipelineContext) -> None:
        source_locator = ctx.source_locator
        if not source_locator:
            raise PipelineRejectionError("Arquivo de áudio Telegram indisponível.")
        path = Path(source_locator)
        if not path.is_file():
            raise PipelineRejectionError("Arquivo de áudio Telegram não encontrado localmente.")
        if ctx.job.source_duration_seconds is None or ctx.job.source_duration_seconds <= 0:
            raise MediaDurationUnknownError(
                "Não foi possível estabelecer a duração do áudio Telegram antes do ASR."
            )
        ctx.job.transition_to(JobStatus.ACQUIRING)
        ctx.started_at = datetime.now(UTC)
        ctx.raw_audio_path = path
        ctx.metadata = MediaMetadata(
            video_id=None,
            title=ctx.job.source_title or "Áudio do Telegram",
            channel="Telegram",
            duration=Duration.from_seconds(ctx.job.source_duration_seconds),
            upload_date=None,
            original_language=None,
            source_label="Telegram (mídia privada)",
        )
        ctx.processing_provenance = replace(ctx.processing_provenance, processing_path="audio_asr")


# ----------------------------------------------------------------------
# Step 4 — converter áudio para Opus/OGG
# ----------------------------------------------------------------------


class ConvertAudioStep(PipelineStep):
    """Converte para Opus/OGG mono no bitrate configurado."""

    @property
    def name(self) -> str:
        return "convert_audio"

    def __init__(
        self,
        converter: AudioConverter,
        processed_dir: Path,
        settings: AppSettings,
    ) -> None:
        self._conv = converter
        self._processed_dir = processed_dir
        self._settings = settings

    def should_run(self, ctx: PipelineContext) -> bool:
        return not ctx.youtube_subtitle_used

    def execute(self, ctx: PipelineContext) -> None:
        ctx.job.transition_to(JobStatus.CONVERTING)
        if ctx.raw_audio_path is None:
            raise RuntimeError("ConvertAudioStep sem raw_audio_path")
        if ctx.metadata is not None:
            slug = str(Slug.from_title(ctx.metadata.title))
        else:
            assert ctx.job.video_id is not None
            slug = ctx.job.video_id.value
        dest = self._processed_dir / f"{slug}-{ctx.job.job_id}.ogg"
        ctx.converted_audio_path = self._conv.convert_to_opus_mono(
            ctx.raw_audio_path,
            dest,
            bitrate_kbps=self._settings.audio_bitrate_kbps,
            sample_rate_hz=self._settings.audio_sample_rate_hz,
            cancel_event=ctx.cancel_event,
        ).path


# ----------------------------------------------------------------------
# Step 5 — escolher runtime (auto-detect GPU/CPU/modelo)
# ----------------------------------------------------------------------


class SelectRuntimeStep(PipelineStep):
    """Decide device/compute/modelo combinando settings + hardware."""

    @property
    def name(self) -> str:
        return "select_runtime"

    def __init__(
        self,
        gpu_detector: GpuDetector,
        settings: AppSettings,
    ) -> None:
        self._gpu = gpu_detector
        self._settings = settings

    def should_run(self, ctx: PipelineContext) -> bool:
        # Não precisa de runtime quando vamos só usar legenda do YT.
        return not ctx.youtube_subtitle_used

    def execute(self, ctx: PipelineContext) -> None:
        language = (
            ctx.requested_language
            or ctx.transcription_language
            or (ctx.metadata.original_language if ctx.metadata is not None else None)
        )
        plan = select_runtime(
            self._settings,
            self._gpu.detect(),
            language=language,
        )
        ctx.runtime_plan = plan
        ctx.add_diagnostic(f"Runtime escolhido: {plan.reason}")


# ----------------------------------------------------------------------
# Step 6 — transcrever
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptionStepProgress:
    on_progress: Callable[[float, str], None] | None = None


def _transcription_request(
    ctx: PipelineContext,
    plan: RuntimePlan,
    settings: AppSettings,
    progress: TranscriptionStepProgress,
) -> TranscriptionRequest:
    if ctx.converted_audio_path is None:
        raise RuntimeError("TranscribeStep sem áudio convertido")
    requested_language = ctx.requested_language
    return TranscriptionRequest(
        audio_path=ctx.converted_audio_path,
        processing_profile=plan.to_transcription_profile(),
        allowed_languages=tuple(Language(code=code) for code in settings.allowed_languages),
        requested_language=requested_language,
        progress=progress.on_progress,
        cancel_event=ctx.cancel_event,
    )


class TranscribeStep(PipelineStep):
    """Transcreve o áudio com retry automático em caso de OOM."""

    @property
    def name(self) -> str:
        return "transcribe"

    def __init__(
        self,
        engine: TranscriptionEngine,
        settings: AppSettings,
        progress: TranscriptionStepProgress | None = None,
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._progress = progress or TranscriptionStepProgress()

    def should_run(self, ctx: PipelineContext) -> bool:
        return not ctx.youtube_subtitle_used

    def execute(self, ctx: PipelineContext) -> None:
        ctx.job.transition_to(JobStatus.TRANSCRIBING)
        if ctx.converted_audio_path is None:
            raise RuntimeError("TranscribeStep sem converted_audio_path")
        if ctx.runtime_plan is None:
            raise RuntimeError("TranscribeStep sem runtime_plan")

        plan = ctx.runtime_plan
        fallback_used = False
        try:
            result = self._engine.transcribe(
                _transcription_request(ctx, plan, self._settings, self._progress)
            )
        except OutOfMemoryError:
            ctx.add_diagnostic("OOM durante transcrição; retentando com plano menor.")
            smaller = smaller_model_alternative(plan.model)
            if smaller is None:
                raise
            fallback_used = True
            new_plan = RuntimePlan(
                device=Device.cpu(),
                compute_type=ComputeType(kind=ComputeKind.INT8),
                model=smaller,
                reason=f"retry-after-OOM: usando {smaller.name} em CPU",
            )
            ctx.runtime_plan = new_plan
            result = self._engine.transcribe(
                _transcription_request(ctx, new_plan, self._settings, self._progress)
            )

        ctx.transcribed_segments = result.segments
        ctx.transcription_language = result.detected_language
        ctx.transcription_confidence = result.language_confidence
        ctx.observed_language = result.observed_language
        ctx.observed_language_confidence = result.observed_language_confidence
        ctx.language_source = result.language_source
        actual_plan = ctx.runtime_plan
        assert actual_plan is not None
        ctx.processing_provenance = replace(
            ctx.processing_provenance,
            processing_path="audio_asr",
            transcription_backend="whisperx",
            transcription_model=actual_plan.model.name,
            device=str(actual_plan.device),
            compute_type=str(actual_plan.compute_type),
            asr_fallback_used=fallback_used,
            language_source=ctx.language_source,
        )
        if ctx.requested_language:
            ctx.add_diagnostic(
                f"Idioma solicitado: {ctx.requested_language}; "
                "confiança do idioma efetivo não inferida a partir da detecção do ASR."
            )
        else:
            confidence = (
                f" (confiança={result.language_confidence:.2f})"
                if result.language_confidence is not None
                else ""
            )
            ctx.add_diagnostic(
                f"Idioma observado pelo ASR: {ctx.transcription_language}{confidence}."
            )


# ----------------------------------------------------------------------
# Step 7 — diarizar e juntar com segmentos
# ----------------------------------------------------------------------


class DiarizeStep(PipelineStep):
    """Identifies speakers and records the actual winning diarization provider."""

    @property
    def name(self) -> str:
        return "diarize"

    def __init__(
        self,
        engine: DiarizationEngine,
        settings: AppSettings,
        progress: TranscriptionStepProgress | None = None,
        diarization_model_name: str = "pyannote/speaker-diarization-community-1",
    ) -> None:
        self._engine = engine
        self._settings = settings
        self._progress = progress or TranscriptionStepProgress()
        self._diarization_model_name = diarization_model_name

    def should_run(self, ctx: PipelineContext) -> bool:
        return not ctx.youtube_subtitle_used

    def execute(self, ctx: PipelineContext) -> None:
        ctx.job.transition_to(JobStatus.DIARIZING)
        if ctx.converted_audio_path is None:
            raise RuntimeError("DiarizeStep sem converted_audio_path")

        target = (
            ctx.runtime_plan.processing_target()
            if ctx.runtime_plan is not None
            else ProcessingTarget.CPU
        )
        if self._progress.on_progress:
            self._progress.on_progress(0.10, "Preparando diarização...")

        diarization = self._engine.diarize(
            DiarizationRequest(
                audio_path=ctx.converted_audio_path,
                processing_target=target,
                progress=self._progress.on_progress,
                cancel_event=ctx.cancel_event,
            )
        )

        if self._progress.on_progress:
            self._progress.on_progress(0.75, "Associando falantes aos segmentos...")
        assigned = assign_speakers_to_segments(
            ctx.transcribed_segments,
            diarization,
        )

        segments: list[TranscriptSegment] = []
        for segment, label in assigned:
            if not segment.text.strip():
                continue
            end = max(segment.end_seconds, segment.start_seconds)
            if end <= segment.start_seconds:
                continue
            segments.append(
                TranscriptSegment(
                    start_seconds=segment.start_seconds,
                    end_seconds=end,
                    text=segment.text,
                    speaker_label=label or "UNKNOWN",
                )
            )

        if not segments:
            raise PipelineRejectionError("Nenhum segmento valido apos diarizacao")

        if self._progress.on_progress:
            self._progress.on_progress(0.90, "Diarização concluída.")

        observed = diarization.provenance
        actual_model = observed.model or self._diarization_model_name
        ctx.processing_provenance = replace(
            ctx.processing_provenance,
            diarization_backend=observed.backend,
            diarization_model=actual_model,
            diarization_fallback_used=observed.fallback_used,
        )
        if observed.fallback_used:
            ctx.add_diagnostic(
                "Fallback de diarização utilizado"
                + (f": backend efetivo={observed.backend}." if observed.backend else ".")
            )

        source = ctx.language_source.value if ctx.youtube_subtitle_used else "whisperx"
        ctx.transcript = Transcript(
            segments=tuple(segments),
            language=ctx.transcription_language,
            language_confidence=ctx.transcription_confidence,
            source=source,
            requested_language=ctx.requested_language,
            observed_language=ctx.observed_language,
            observed_language_confidence=ctx.observed_language_confidence,
            language_source=ctx.language_source,
        )


# ----------------------------------------------------------------------
# Step 8 — render Markdown
# ----------------------------------------------------------------------


class RenderMarkdownStep(PipelineStep):
    """Render approved Markdown and persist structured canonical evidence."""

    @property
    def name(self) -> str:
        return "render_md"

    def __init__(
        self,
        renderer: TranscriptRenderer,
        writer: CanonicalMarkdownWriter,
        transcripts_dir: Path,
        settings: AppSettings,
        diarization_model_name: str = "pyannote/speaker-diarization-community-1",
        snapshot_repository: CanonicalTranscriptStore | None = None,
        processing_fingerprint: str = "",
    ) -> None:
        self._renderer = renderer
        self._writer = writer
        self._transcripts_dir = transcripts_dir
        self._settings = settings
        self._diar_model_name = diarization_model_name
        self._snapshot_repository = snapshot_repository
        self._processing_fingerprint = processing_fingerprint

    def execute(self, ctx: PipelineContext) -> None:
        ctx.job.transition_to(JobStatus.RENDERING)
        if ctx.metadata is None or ctx.transcript is None:
            raise RuntimeError("RenderMarkdownStep sem metadata/transcript")
        if self._snapshot_repository is None:
            raise RuntimeError("Repositório canônico de transcrição não configurado")

        whisper_model = (
            ctx.runtime_plan.model.name
            if ctx.runtime_plan is not None
            else self._settings.whisper_model
        )
        slug = Slug.from_title(ctx.metadata.title)
        preferred_dest = self._transcripts_dir / f"{slug}.md"

        render_context = TranscriptRenderContext(
            rendered_at=datetime.now(UTC),
            whisper_model=whisper_model,
            diarization_model=(
                ctx.processing_provenance.diarization_model or self._diar_model_name
            ),
            transcription_source=ctx.transcript.source,
        )
        record = CanonicalTranscriptRecord(
            metadata=ctx.metadata,
            transcript=ctx.transcript,
            context=render_context,
            processing_fingerprint=self._processing_fingerprint,
            processing_provenance=ctx.processing_provenance,
        )
        rendered = self._renderer.render_transcript(
            TranscriptRenderRequest(
                record=record,
                speaker_aliases=ctx.job.speaker_renames,
            )
        )
        if ctx.youtube_subtitle_used and text_has_unresolved_corruption(rendered):
            ctx.add_diagnostic(
                "Markdown derivado de legenda rejeitado por integridade antes do envio."
            )
            raise PipelineRejectionError(
                "A legenda do YouTube permaneceu corrompida após renderização."
            )

        reference = ctx.job.job_id
        self._snapshot_repository.persist(reference, record)
        try:
            dest = self._writer.write_new(
                preferred_dest,
                rendered,
                collision_key=ctx.job.job_id,
            )
        except Exception:
            try:
                self._snapshot_repository.delete(reference)
            except Exception:
                logger.error(
                    "Rollback do snapshot canônico falhou; preservando a falha original de Markdown."
                )
            raise

        ctx.final_md_path = dest
        ctx.job.canonical_transcript_ref = reference
        ctx.job.md_path = str(dest)
        if ctx.converted_audio_path is not None:
            ctx.job.audio_path = str(ctx.converted_audio_path)
        ctx.finished_at = datetime.now(UTC)
