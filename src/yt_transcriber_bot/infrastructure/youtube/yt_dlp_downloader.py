"""Implementação de ``YouTubeDownloader`` usando ``yt-dlp``.

Estratégia para auto-dub: o YouTube atualmente devolve em ``formats`` uma
lista onde cada áudio pode ter um campo ``language`` (ex.: ``en``, ``pt-orig``).
A faixa "original" tem o sufixo ``-orig`` no campo ``language`` ou aparece
como ``original=True``. Quando há mais de uma faixa, escolhemos sempre a
original e marcamos ``used_alternate_track=True`` para que o orquestrador
possa avisar o usuário.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

from yt_transcriber_bot.application.ports.youtube_downloader import (
    AgeRestrictedError,
    DownloadedAudio,
    FetchedSubtitle,
    MembersOnlyError,
    NoAudioStreamError,
    SubtitleTrack,
    VideoUnavailableError,
    YouTubeDownloader,
    YouTubeError,
)
from yt_transcriber_bot.domain.entities.video_metadata import VideoMetadata
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


class _YDLLike(Protocol):
    """Subconjunto da interface do ``yt_dlp.YoutubeDL`` que usamos."""

    def extract_info(self, url: str, download: bool = ...) -> dict[str, Any]: ...

    def __enter__(self) -> _YDLLike: ...

    def __exit__(self, *args: object) -> None: ...


class _YDLFactory(Protocol):
    def __call__(self, params: dict[str, Any]) -> _YDLLike: ...


class _SubtitleFetcher(Protocol):
    def __call__(self, url: str, ext: str) -> str: ...


# Formatos deliberadamente permissivos. O yt-dlp também faz seleção de
# formato durante chamadas de metadados; em alguns vídeos ou configurações
# globais isso pode falhar antes do download real. Para metadados/legendas,
# não precisamos de uma escolha estrita de mídia; para áudio, preferimos
# audio-only, mas aceitamos um formato muxado como fallback porque o ffmpeg
# extrairá o áudio no passo seguinte.
_METADATA_FORMAT = "bestaudio/best[acodec!=none]/best/worst"
_AUDIO_FORMAT = (
    # Preferir progressivos pequenos como fallback prático do YouTube.
    # Em alguns vídeos recentes, seletores audio-only como ``bestaudio``
    # aparecem em ``--list-formats``, mas falham no download por restrições
    # transitórias do extractor/cliente. Para transcrição, um MP4 progressivo
    # com áudio é aceitável porque o ffmpeg extrai o áudio no passo seguinte.
    "18/22/"
    "best[ext=mp4][acodec!=none][vcodec!=none]/"
    "worst[acodec!=none][vcodec!=none]/"
    "best[acodec!=none][vcodec!=none]/"
    "bestaudio/"
    "best[acodec!=none]/"
    "best/"
    "worst"
)
_FORMAT_UNAVAILABLE_MARKERS = (
    "requested format is not available",
    "no video formats found",
    "no suitable formats",
)

logger = logging.getLogger(__name__)


class YtDlpDownloader(YouTubeDownloader):
    """Adapter que envolve ``yt_dlp.YoutubeDL`` por trás da porta ``YouTubeDownloader``.

    Recebe uma factory para permitir testes sem depender do binário/rede.
    """

    def __init__(
        self,
        *,
        ydl_factory: _YDLFactory,
        subtitle_fetcher: _SubtitleFetcher,
        cookies_file: str | None = None,
        cookies_browser: str | None = None,
    ) -> None:
        self._ydl_factory = ydl_factory
        self._subtitle_fetcher = subtitle_fetcher
        self._cookies_file = cookies_file or None
        self._cookies_browser = cookies_browser or None

    # ------------------------------------------------------------------
    # Common params
    # ------------------------------------------------------------------

    def _common_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
            # Evita que um ~/.config/yt-dlp/config ou /etc/yt-dlp.conf do usuário
            # injete um seletor de formato incompatível com o fluxo do bot.
            "ignoreconfig": True,
        }
        if self._cookies_file:
            params["cookiefile"] = self._cookies_file
        if self._cookies_browser:
            params["cookiesfrombrowser"] = (self._cookies_browser,)
        return params

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def fetch_metadata(self, video_id: VideoId) -> VideoMetadata:
        info = self._extract_info(
            video_id,
            download=False,
            extra_params={
                "format": _METADATA_FORMAT,
                "ignore_no_formats_error": True,
            },
        )
        return self._build_metadata(video_id, info)

    def _extract_info(
        self, video_id: VideoId, *, download: bool, extra_params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        params = self._common_params()
        params["skip_download"] = not download
        if extra_params:
            params.update(extra_params)
        try:
            with self._ydl_factory(params) as ydl:
                info = ydl.extract_info(video_id.canonical_url(), download=download)
        except Exception as exc:  # pragma: no cover - mapeamento de mensagens
            # Em chamadas sem download, formato indisponível não deveria bloquear
            # a obtenção de metadados. Tentamos uma segunda chamada ainda mais
            # permissiva antes de propagar o erro.
            if not download and self._looks_like_format_unavailable(exc):
                retry_params = dict(params)
                retry_params.update(
                    {
                        "format": "best/worst",
                        "ignore_no_formats_error": True,
                    }
                )
                try:
                    with self._ydl_factory(retry_params) as ydl:
                        info = ydl.extract_info(video_id.canonical_url(), download=False)
                except Exception as retry_exc:  # pragma: no cover - mapeamento de mensagens
                    raise self._map_exception(retry_exc) from retry_exc
            else:
                raise self._map_exception(exc) from exc
        if info is None:
            raise VideoUnavailableError("yt-dlp retornou metadados vazios")
        return info

    @staticmethod
    def _map_exception(exc: Exception) -> YouTubeError:
        msg = str(exc).lower()
        if "members-only" in msg or "members only" in msg or "join this channel" in msg:
            return MembersOnlyError(str(exc))
        if "age" in msg and "restrict" in msg:
            return AgeRestrictedError(str(exc))
        if any(s in msg for s in ("private video", "video unavailable", "removed", "geo")):
            return VideoUnavailableError(str(exc))
        return YouTubeError(str(exc))

    @staticmethod
    def _looks_like_format_unavailable(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(marker in msg for marker in _FORMAT_UNAVAILABLE_MARKERS)

    @staticmethod
    def _build_metadata(video_id: VideoId, info: dict[str, Any]) -> VideoMetadata:
        title = str(info.get("title") or "").strip()
        if not title:
            raise YouTubeError("metadados sem título")
        channel = str(info.get("uploader") or info.get("channel") or "").strip()
        if not channel:
            raise YouTubeError("metadados sem canal")

        duration_raw = info.get("duration") or 0
        duration = Duration.from_seconds(int(duration_raw))

        upload_date_raw = info.get("upload_date")
        upload_dt: date | None
        if upload_date_raw and re.match(r"^\d{8}$", str(upload_date_raw)):
            upload_dt = datetime.strptime(str(upload_date_raw), "%Y%m%d").date()
        else:
            upload_dt = None

        original_language = YtDlpDownloader._infer_original_language(info)
        alt_languages, has_alt = YtDlpDownloader._collect_alternate_languages(info)

        return VideoMetadata(
            video_id=video_id,
            title=title,
            channel=channel,
            duration=duration,
            upload_date=upload_dt,
            original_language=original_language,
            has_alternate_audio_tracks=has_alt,
            alternate_languages=alt_languages,
        )

    @staticmethod
    def _infer_original_language(info: dict[str, Any]) -> Language:
        # Prioridade 1: faixa de áudio com sufixo ``-orig`` ou flag ``original=True``.
        formats = info.get("formats") or []
        if isinstance(formats, list):
            for fmt in formats:
                if not isinstance(fmt, dict):
                    continue
                lang = str(fmt.get("language") or "").lower()
                if lang.endswith("-orig") or fmt.get("original") is True:
                    base = lang.split("-")[0]
                    if re.match(r"^[a-z]{2}$", base):
                        return Language(code=base)

        # Prioridade 2: campo ``language`` no nível do vídeo.
        top_lang = str(info.get("language") or "").lower()
        if re.match(r"^[a-z]{2}$", top_lang):
            return Language(code=top_lang)

        # Fallback: en.
        return Language.en()

    @staticmethod
    def _collect_alternate_languages(
        info: dict[str, Any],
    ) -> tuple[tuple[Language, ...], bool]:
        formats = info.get("formats") or []
        langs: set[str] = set()
        original_seen = False
        if isinstance(formats, list):
            for fmt in formats:
                if not isinstance(fmt, dict):
                    continue
                lang = str(fmt.get("language") or "").lower()
                if not lang:
                    continue
                if lang.endswith("-orig") or fmt.get("original") is True:
                    original_seen = True
                    continue
                base = lang.split("-")[0]
                if re.match(r"^[a-z]{2}$", base):
                    langs.add(base)
        # Se há outras faixas + a original (sufixo -orig), há auto-dub.
        has_alt = original_seen and bool(langs)
        return tuple(Language(code=c) for c in sorted(langs)), has_alt

    # ------------------------------------------------------------------
    # Subtitles
    # ------------------------------------------------------------------

    def list_subtitles(self, video_id: VideoId) -> tuple[SubtitleTrack, ...]:
        info = self._extract_info(
            video_id,
            download=False,
            extra_params={
                "writesubtitles": True,
                "writeautomaticsub": True,
                "format": _METADATA_FORMAT,
                "ignore_no_formats_error": True,
            },
        )
        tracks: list[SubtitleTrack] = []
        manual = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}

        for lang_code, entries in manual.items():
            track = self._pick_best_track(lang_code, entries, is_auto=False)
            if track:
                tracks.append(track)
        for lang_code, entries in auto.items():
            track = self._pick_best_track(lang_code, entries, is_auto=True)
            if track:
                tracks.append(track)
        return tuple(tracks)

    @staticmethod
    def _pick_best_track(lang_code: str, entries: object, *, is_auto: bool) -> SubtitleTrack | None:
        if not isinstance(entries, list) or not entries:
            return None
        # Aceitar apenas códigos ISO-639-1 simples (ignorar variantes regionais "pt-BR").
        base = lang_code.split("-")[0].lower()
        if not re.match(r"^[a-z]{2}$", base):
            return None
        # Detectar tradução: o yt-dlp marca automatic_captions traduzidos
        # com lang_code do tipo ``pt-en`` ou via ``name`` contendo "from English".
        is_translated = "-" in lang_code and not lang_code.endswith("-orig")
        # Preferir vtt → srt.
        chosen = None
        for ext in ("vtt", "srt", "ttml"):
            for entry in entries:
                if isinstance(entry, dict) and entry.get("ext") == ext:
                    chosen = entry
                    break
            if chosen:
                break
        if not chosen:
            chosen = entries[0] if isinstance(entries[0], dict) else None
        if not chosen:
            return None
        url = str(chosen.get("url") or "") or None
        ext = str(chosen.get("ext") or "vtt")
        return SubtitleTrack(
            language=Language(code=base),
            is_auto_generated=is_auto,
            is_translated=is_translated,
            url=url,
            ext=ext,
        )

    def fetch_subtitle(self, video_id: VideoId, track: SubtitleTrack) -> FetchedSubtitle:
        if track.url is None:
            raise YouTubeError("Pista de legenda sem URL")
        raw = self._subtitle_fetcher(track.url, track.ext)
        segments = _parse_subtitle(raw, track.ext)
        return FetchedSubtitle(
            language=track.language,
            is_auto_generated=track.is_auto_generated,
            segments=segments,
        )

    # ------------------------------------------------------------------
    # Audio download
    # ------------------------------------------------------------------

    def download_audio(self, video_id: VideoId, dest_dir: Path) -> DownloadedAudio:
        dest_dir.mkdir(parents=True, exist_ok=True)
        last_exc: Exception | None = None

        # 1) Tentativa rápida com seletor progressivo-first. Isto resolve a maior
        # parte dos casos e mantém compatibilidade com o comportamento anterior.
        try:
            info = self._download_audio_with_selector(video_id, dest_dir, _AUDIO_FORMAT)
        except Exception as exc:  # pragma: no cover - mapeamento de mensagens
            mapped = self._map_exception(exc)
            if isinstance(mapped, MembersOnlyError | AgeRestrictedError | VideoUnavailableError):
                raise mapped from exc
            last_exc = exc
            info = self._download_audio_via_discovered_formats(video_id, dest_dir, last_exc)

        downloaded = self._validated_downloaded_path(info, dest_dir, video_id)
        ext = downloaded.suffix.lstrip(".").lower()
        used_alt = bool(
            (info.get("language") or "").lower().endswith("-orig") or info.get("original") is True
        )
        metadata = self._build_metadata(video_id, info)
        return DownloadedAudio(
            audio_path=downloaded,
            container=ext,
            used_alternate_track=used_alt or metadata.has_alternate_audio_tracks,
            metadata=metadata,
        )

    def _download_audio_with_selector(
        self, video_id: VideoId, dest_dir: Path, format_selector: str | None
    ) -> dict[str, Any]:
        self._cleanup_previous_downloads(dest_dir, video_id)
        outtmpl = str(dest_dir / f"{video_id.value}.%(ext)s")
        params = self._common_params()
        params.update(
            {
                "skip_download": False,
                "outtmpl": outtmpl,
                "noprogress": True,
                "overwrites": True,
            }
        )
        if format_selector:
            params["format"] = format_selector
        try:
            with self._ydl_factory(params) as ydl:
                info = ydl.extract_info(video_id.canonical_url(), download=True)
        except Exception:
            self._cleanup_previous_downloads(dest_dir, video_id)
            raise
        if info is None:
            raise VideoUnavailableError("yt-dlp retornou info vazia no download")
        return info

    def _download_audio_via_discovered_formats(
        self, video_id: VideoId, dest_dir: Path, initial_exc: Exception
    ) -> dict[str, Any]:
        """Fallback robusto: listar formatos e baixar por ``format_id`` concreto.

        A correção importante aqui é evitar o fallback ``format=None``. Quando o
        seletor padrão do yt-dlp quebra com ``Requested format is not available``,
        deixar o yt-dlp escolher sozinho apenas repete a mesma falha. Em vez disso,
        fazemos uma listagem explícita de formatos e tentamos IDs concretos.
        """
        last_exc: Exception = initial_exc
        listing_info: dict[str, Any] = {}

        try:
            listing_info = self._list_formats_info(video_id)
        except Exception as exc:  # pragma: no cover - mapeamento de mensagens
            last_exc = exc
            logger.warning("falha ao listar formatos com listformats=True: %s", exc)

        candidate_ids = self._select_audio_candidate_format_ids(listing_info)
        if not candidate_ids:
            # Candidatos conhecidos do YouTube. Eles não substituem a listagem
            # real, mas ajudam quando o extractor retorna metadados incompletos
            # embora formatos progressivos usuais ainda estejam disponíveis.
            candidate_ids = ("18", "22", "140", "139", "251", "250", "249")

        logger.info("tentando %d formato(s) concreto(s) para %s", len(candidate_ids), video_id.value)
        for format_id in candidate_ids:
            try:
                info = self._download_audio_with_selector(video_id, dest_dir, format_id)
                # Alguns casos de erro geram arquivo inexistente/vazio sem exceção
                # forte do yt-dlp. Validamos aqui para passar ao próximo candidato.
                self._validated_downloaded_path(info, dest_dir, video_id)
                logger.info("download via formato %s funcionou para %s", format_id, video_id.value)
                return info
            except Exception as exc:  # pragma: no cover - mapeamento de mensagens
                mapped = self._map_exception(exc)
                if isinstance(mapped, MembersOnlyError | AgeRestrictedError | VideoUnavailableError):
                    raise mapped from exc
                last_exc = exc
                logger.warning("formato %s falhou para %s: %s", format_id, video_id.value, exc)
                continue

        diagnostic = self._format_download_diagnostic(video_id, listing_info, last_exc)
        raise YouTubeError(diagnostic) from last_exc

    def _list_formats_info(self, video_id: VideoId) -> dict[str, Any]:
        """Obtém formatos disponíveis sem aplicar seletor de download.

        ``listformats=True`` espelha ``yt-dlp -F`` e evita a etapa em que o
        selector padrão tenta escolher mídia para download. Isso torna o fallback
        realmente independente do seletor que acabou de falhar.
        """
        params = self._common_params()
        params.update(
            {
                "skip_download": True,
                "listformats": True,
                "simulate": True,
                "ignore_no_formats_error": True,
            }
        )
        with self._ydl_factory(params) as ydl:
            info = ydl.extract_info(video_id.canonical_url(), download=False)
        if info is None:
            raise VideoUnavailableError("yt-dlp retornou info vazia ao listar formatos")
        return info

    @staticmethod
    def _format_download_diagnostic(
        video_id: VideoId, listing_info: dict[str, Any], last_exc: Exception
    ) -> str:
        formats = listing_info.get("formats") or []
        format_count = len(formats) if isinstance(formats, list) else 0
        available_ids: list[str] = []
        if isinstance(formats, list):
            for item in formats:
                if isinstance(item, dict) and item.get("format_id") is not None:
                    fid = str(item.get("format_id"))
                    acodec = str(item.get("acodec") or "?")
                    vcodec = str(item.get("vcodec") or "?")
                    ext = str(item.get("ext") or "?")
                    available_ids.append(f"{fid}:{ext}:a={acodec}:v={vcodec}")
        sample = ", ".join(available_ids[:20]) or "nenhum formato com ID retornado"
        return (
            "Não foi possível baixar áudio do YouTube depois de listar e tentar formatos concretos. "
            f"video_id={video_id.value}; formatos_listados={format_count}; "
            f"amostra={sample}; último_erro={last_exc}. "
            "Diagnóstico local recomendado: uv run yt-dlp -F -vU "
            f"{video_id.canonical_url()}"
        )

    def _validated_downloaded_path(
        self, info: dict[str, Any], dest_dir: Path, video_id: VideoId
    ) -> Path:
        downloaded = self._extract_downloaded_path(info, dest_dir, video_id)
        if not downloaded.exists() or downloaded.stat().st_size == 0:
            raise NoAudioStreamError(f"Arquivo de áudio inválido: {downloaded}")
        return downloaded

    @staticmethod
    def _select_audio_candidate_format_ids(info: dict[str, Any]) -> tuple[str, ...]:
        formats = info.get("formats") or []
        if not isinstance(formats, list):
            return ()

        def has_audio(fmt: dict[str, Any]) -> bool:
            acodec = str(fmt.get("acodec") or "").lower()
            return bool(acodec) and acodec != "none"

        def has_video(fmt: dict[str, Any]) -> bool:
            vcodec = str(fmt.get("vcodec") or "").lower()
            return bool(vcodec) and vcodec != "none"

        def format_id(fmt: dict[str, Any]) -> str | None:
            raw = fmt.get("format_id")
            return str(raw) if raw not in (None, "") else None

        def is_original(fmt: dict[str, Any]) -> bool:
            lang = str(fmt.get("language") or "").lower()
            return lang.endswith("-orig") or fmt.get("original") is True

        def ext_rank(fmt: dict[str, Any]) -> int:
            ext = str(fmt.get("ext") or "").lower()
            order = {"m4a": 0, "mp4": 1, "webm": 2, "opus": 3}
            return order.get(ext, 9)

        def size_value(fmt: dict[str, Any]) -> float:
            for key in ("filesize", "filesize_approx"):
                value = fmt.get(key)
                if isinstance(value, int | float) and value > 0:
                    return float(value)
            return float("inf")

        def abr_value(fmt: dict[str, Any]) -> float:
            value = fmt.get("abr") or fmt.get("tbr") or 0
            return float(value) if isinstance(value, int | float) else 0.0

        def height_value(fmt: dict[str, Any]) -> float:
            value = fmt.get("height") or 10_000
            return float(value) if isinstance(value, int | float) else 10_000.0

        audio_only: list[dict[str, Any]] = []
        progressive: list[dict[str, Any]] = []
        any_audio: list[dict[str, Any]] = []
        for item in formats:
            if not isinstance(item, dict) or not has_audio(item) or not format_id(item):
                continue
            any_audio.append(item)
            if has_video(item):
                progressive.append(item)
            else:
                audio_only.append(item)

        # Audio-only primeiro, com preferência por faixa original. Entre candidatos
        # equivalentes, prefira m4a/mp4 e bitrate razoável. Se esses falharem por
        # restrição do YouTube, os progressivos pequenos entram logo depois.
        audio_only.sort(key=lambda f: (not is_original(f), ext_rank(f), -abr_value(f), size_value(f)))
        progressive.sort(
            key=lambda f: (
                0 if format_id(f) == "18" else 1 if format_id(f) == "22" else 2,
                ext_rank(f),
                height_value(f),
                size_value(f),
            )
        )
        any_audio.sort(key=lambda f: (ext_rank(f), size_value(f), -abr_value(f)))

        selected: list[str] = []
        for group in (audio_only, progressive, any_audio):
            for fmt in group:
                fid = format_id(fmt)
                if fid and fid not in selected:
                    selected.append(fid)
        return tuple(selected[:24])

    @staticmethod
    def _cleanup_previous_downloads(dest_dir: Path, video_id: VideoId) -> None:
        for candidate in dest_dir.glob(f"{video_id.value}.*"):
            if candidate.is_file():
                try:
                    candidate.unlink()
                except OSError:
                    pass

    @staticmethod
    def _extract_downloaded_path(info: dict[str, Any], dest_dir: Path, video_id: VideoId) -> Path:
        requested = info.get("requested_downloads") or []
        if isinstance(requested, list) and requested:
            first = requested[0]
            if isinstance(first, dict):
                filepath = first.get("filepath") or first.get("_filename")
                if isinstance(filepath, str):
                    return Path(filepath)
        # Fallback: procurar arquivos com o video_id no nome.
        candidates = sorted(
            p
            for p in dest_dir.glob(f"{video_id.value}.*")
            if p.is_file() and p.suffix.lower() not in {".part", ".ytdl"}
        )
        if candidates:
            return candidates[0]
        raise NoAudioStreamError("Não foi possível localizar o arquivo baixado")


# ----------------------------------------------------------------------
# Parsing de legendas (VTT/SRT)
# ----------------------------------------------------------------------


_TIMESTAMP_PATTERN = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+):(\d+)[.,](\d+)")


def _parse_subtitle(content: str, ext: str) -> tuple[tuple[float, float, str], ...]:
    """Parser tolerante para VTT/SRT que aceita variações comuns do YouTube.

    Observação importante: legendas automáticas do YouTube em VTT costumam
    funcionar como uma "janela rolante". Cues consecutivos repetem parte do
    texto anterior e, se concatenados ingenuamente, geram transcrições com
    frases duplicadas duas ou três vezes. Por isso, depois do parsing bruto,
    fazemos uma normalização conservadora por sobreposição de palavras.
    """
    if not content.strip():
        return ()
    lines = content.splitlines()
    blocks: list[tuple[float, float, list[str]]] = []
    current_start: float | None = None
    current_end: float | None = None
    current_text: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        # Cabeçalhos / metadados
        if not line or line.startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:")):
            if current_start is not None and current_end is not None and current_text:
                blocks.append((current_start, current_end, current_text))
                current_text = []
                current_start = None
                current_end = None
            continue
        match = _TIMESTAMP_PATTERN.search(line)
        if match:
            if current_start is not None and current_end is not None and current_text:
                blocks.append((current_start, current_end, current_text))
                current_text = []
            current_start = _hms_to_seconds(
                match.group(1), match.group(2), match.group(3), match.group(4)
            )
            current_end = _hms_to_seconds(
                match.group(5), match.group(6), match.group(7), match.group(8)
            )
            continue
        if line.isdigit():
            # Numeração SRT
            continue
        # Texto da legenda; remover tags simples como <c> e timestamps inline do VTT.
        cleaned = re.sub(r"<[^>]+>", "", line).strip()
        cleaned = _normalize_subtitle_text(cleaned)
        if cleaned:
            current_text.append(cleaned)

    if current_start is not None and current_end is not None and current_text:
        blocks.append((current_start, current_end, current_text))

    parsed = tuple((s, e, _normalize_subtitle_text(" ".join(t))) for s, e, t in blocks if t)
    return _dedupe_subtitle_segments(parsed)


def _hms_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0


def _normalize_subtitle_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _word_key(token: str) -> str:
    return re.sub(r"[^\wÀ-ÿ]+", "", token, flags=re.UNICODE).lower()


def _tokens_equal(left: list[str], right: list[str]) -> bool:
    if len(left) != len(right):
        return False
    return [_word_key(t) for t in left] == [_word_key(t) for t in right]


def _collapse_adjacent_repeated_phrases(text: str, *, max_phrase_words: int = 18) -> str:
    """Remove repetições imediatas de frases dentro do mesmo cue.

    Ex.: "A B C A B C D" -> "A B C D". O limite evita falsos positivos
    em repetições discursivas longas e preserva interjeições naturais.
    """
    words = text.split()
    if len(words) < 4:
        return text
    i = 0
    out: list[str] = []
    while i < len(words):
        matched = False
        max_k = min(max_phrase_words, (len(words) - i) // 2)
        for k in range(max_k, 1, -1):
            phrase = words[i : i + k]
            next_phrase = words[i + k : i + 2 * k]
            if _tokens_equal(phrase, next_phrase):
                out.extend(phrase)
                i += 2 * k
                while i + k <= len(words) and _tokens_equal(phrase, words[i : i + k]):
                    i += k
                matched = True
                break
        if not matched:
            out.append(words[i])
            i += 1
    return " ".join(out)


def _strip_prefix_overlap(previous_text: str, current_text: str, *, max_overlap_words: int = 40) -> str:
    """Remove do cue atual a parte que já apareceu no final do contexto anterior."""
    prev_words = previous_text.split()
    cur_words = current_text.split()
    max_k = min(max_overlap_words, len(prev_words), len(cur_words))
    for k in range(max_k, 0, -1):
        if _tokens_equal(prev_words[-k:], cur_words[:k]):
            return " ".join(cur_words[k:]).strip()
    return current_text


def _dedupe_subtitle_segments(
    segments: tuple[tuple[float, float, str], ...],
) -> tuple[tuple[float, float, str], ...]:
    """Deduplica legendas com sobreposição preservando timestamps úteis."""
    cleaned: list[tuple[float, float, str]] = []
    rolling_context = ""
    for start, end, raw_text in segments:
        text = _collapse_adjacent_repeated_phrases(_normalize_subtitle_text(raw_text))
        text = _strip_prefix_overlap(rolling_context, text)
        text = _collapse_adjacent_repeated_phrases(_normalize_subtitle_text(text))
        if not text:
            continue
        cleaned.append((start, end, text))
        # Manter só uma janela de contexto para reduzir custo e falsos positivos.
        rolling_words = (rolling_context + " " + text).split()[-80:]
        rolling_context = " ".join(rolling_words)
    return tuple(cleaned)
