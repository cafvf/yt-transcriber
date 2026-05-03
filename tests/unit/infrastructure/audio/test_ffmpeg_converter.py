"""Testes do ``FfmpegAudioConverter``.

Combina testes unitários (com runner mockado) e integração real com o
binário do ffmpeg. Testes de integração usam ``pytest.mark.integration``.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from yt_transcriber_bot.application.ports.audio_converter import AudioConversionError
from yt_transcriber_bot.infrastructure.audio.ffmpeg_converter import (
    CommandRunner,
    CompletedRun,
    FfmpegAudioConverter,
)

# ----------------------------------------------------------------------
# Runner falso
# ----------------------------------------------------------------------


class FakeRunner(CommandRunner):
    def __init__(
        self,
        responses: list[CompletedRun] | None = None,
        *,
        on_args: Callable[[tuple[str, ...]], None] | None = None,
    ) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._responses = list(responses or [])
        self._on_args = on_args

    def run(self, args: Sequence[str]) -> CompletedRun:
        captured = tuple(args)
        self.calls.append(captured)
        if self._on_args is not None:
            self._on_args(captured)
        if not self._responses:
            return CompletedRun(returncode=0, stdout="", stderr="")
        return self._responses.pop(0)


def _create_dummy_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)


# ======================================================================
# Validações de entrada
# ======================================================================


class TestConvertValidation:
    def test_missing_source_raises(self, tmp_path: Path) -> None:
        conv = FfmpegAudioConverter(runner=FakeRunner())
        with pytest.raises(AudioConversionError, match="origem"):
            conv.convert_to_opus_mono(tmp_path / "missing.m4a", tmp_path / "out.ogg")

    def test_invalid_bitrate_low(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        conv = FfmpegAudioConverter(runner=FakeRunner())
        with pytest.raises(AudioConversionError, match="bitrate"):
            conv.convert_to_opus_mono(src, tmp_path / "out.ogg", bitrate_kbps=8)

    def test_invalid_bitrate_high(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        conv = FfmpegAudioConverter(runner=FakeRunner())
        with pytest.raises(AudioConversionError, match="bitrate"):
            conv.convert_to_opus_mono(src, tmp_path / "out.ogg", bitrate_kbps=256)

    def test_invalid_sample_rate(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        conv = FfmpegAudioConverter(runner=FakeRunner())
        with pytest.raises(AudioConversionError, match="sample_rate"):
            conv.convert_to_opus_mono(src, tmp_path / "out.ogg", sample_rate_hz=44100)


# ======================================================================
# Comportamento via runner mockado
# ======================================================================


class TestConvertWithMockRunner:
    def test_builds_correct_ffmpeg_args(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        dest = tmp_path / "out.ogg"

        def writer(args: tuple[str, ...]) -> None:
            _create_dummy_file(dest, size=128)

        runner = FakeRunner(on_args=writer)
        conv = FfmpegAudioConverter(runner=runner)
        result = conv.convert_to_opus_mono(src, dest, bitrate_kbps=32, sample_rate_hz=16000)

        # Verificações de args
        args = runner.calls[0]
        assert args[0] == "ffmpeg"
        assert "-i" in args
        assert str(src) in args
        assert "-ac" in args
        assert "1" in args
        assert "-ar" in args
        assert "16000" in args
        assert "-c:a" in args
        assert "libopus" in args
        assert "-application" in args
        assert "voip" in args
        assert "-b:a" in args
        assert "32k" in args
        assert str(dest) in args

        # Resultado
        assert result.path == dest
        assert result.bitrate_kbps == 32
        assert result.sample_rate_hz == 16000
        assert result.channels == 1
        assert result.container == "ogg"
        assert result.size_bytes == 128

    def test_failure_propagates_stderr(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        runner = FakeRunner(responses=[CompletedRun(returncode=1, stdout="", stderr="boom")])
        conv = FfmpegAudioConverter(runner=runner)
        with pytest.raises(AudioConversionError, match="boom"):
            conv.convert_to_opus_mono(src, tmp_path / "out.ogg")

    def test_empty_output_raises(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        # Runner retorna 0 mas não cria o arquivo.
        runner = FakeRunner(responses=[CompletedRun(returncode=0, stdout="", stderr="")])
        conv = FfmpegAudioConverter(runner=runner)
        with pytest.raises(AudioConversionError, match="vazio"):
            conv.convert_to_opus_mono(src, tmp_path / "out.ogg")

    def test_overwrites_existing_destination(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        dest = tmp_path / "out.ogg"
        _create_dummy_file(dest, size=999)  # já existe

        def writer(args: tuple[str, ...]) -> None:
            _create_dummy_file(dest, size=42)

        runner = FakeRunner(on_args=writer)
        result = FfmpegAudioConverter(runner=runner).convert_to_opus_mono(src, dest)
        assert result.size_bytes == 42

    def test_creates_destination_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "in.m4a"
        _create_dummy_file(src)
        dest = tmp_path / "deep" / "dir" / "out.ogg"

        def writer(args: tuple[str, ...]) -> None:
            _create_dummy_file(dest, size=10)

        runner = FakeRunner(on_args=writer)
        FfmpegAudioConverter(runner=runner).convert_to_opus_mono(src, dest)
        assert dest.exists()


# ======================================================================
# Particionamento
# ======================================================================


class TestSplit:
    def test_no_split_when_under_threshold(self, tmp_path: Path) -> None:
        src = tmp_path / "in.ogg"
        _create_dummy_file(src, size=1000)
        runner = FakeRunner()
        result = FfmpegAudioConverter(runner=runner).split_for_telegram(
            src, tmp_path / "out", max_size_bytes=2000
        )
        assert result == (src,)
        assert runner.calls == []  # nenhum ffmpeg chamado

    def test_split_called_when_over_threshold(self, tmp_path: Path) -> None:
        src = tmp_path / "in.ogg"
        _create_dummy_file(src, size=10_000_000)
        out_dir = tmp_path / "split"

        responses = [
            # Resposta para ffprobe
            CompletedRun(
                returncode=0,
                stdout='{"format": {"duration": "300.0"}}',
                stderr="",
            ),
        ]

        def on_segment(args: tuple[str, ...]) -> None:
            # Quando o segment é chamado, criar dois arquivos de saída.
            if "-f" in args and "segment" in args:
                (out_dir / "in_part000.ogg").write_bytes(b"a")
                (out_dir / "in_part001.ogg").write_bytes(b"b")

        runner = FakeRunner(responses=responses, on_args=on_segment)
        result = FfmpegAudioConverter(runner=runner).split_for_telegram(
            src, out_dir, max_size_bytes=5_000_000
        )
        assert len(result) == 2
        assert all(p.exists() for p in result)

    def test_split_failure_raises(self, tmp_path: Path) -> None:
        src = tmp_path / "in.ogg"
        _create_dummy_file(src, size=10_000_000)
        responses = [
            CompletedRun(
                returncode=0,
                stdout='{"format": {"duration": "300.0"}}',
                stderr="",
            ),
            CompletedRun(returncode=1, stdout="", stderr="segment failed"),
        ]
        runner = FakeRunner(responses=responses)
        with pytest.raises(AudioConversionError, match="segment"):
            FfmpegAudioConverter(runner=runner).split_for_telegram(
                src, tmp_path / "out", max_size_bytes=5_000_000
            )

    def test_split_with_unknown_duration_raises(self, tmp_path: Path) -> None:
        src = tmp_path / "in.ogg"
        _create_dummy_file(src, size=10_000_000)
        responses = [
            CompletedRun(returncode=0, stdout='{"format": {}}', stderr=""),
        ]
        runner = FakeRunner(responses=responses)
        with pytest.raises(AudioConversionError, match="duração"):
            FfmpegAudioConverter(runner=runner).split_for_telegram(
                src, tmp_path / "out", max_size_bytes=5_000_000
            )


# ======================================================================
# Integração real com ffmpeg (executa o binário)
# ======================================================================


_FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.integration
@pytest.mark.skipif(not _FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe não disponíveis")
class TestFfmpegRealIntegration:
    """Geram um WAV de 3 segundos via ffmpeg e convertem para Opus."""

    def _make_wav(self, dest: Path, seconds: int = 3) -> None:
        # Gera senoide via lavfi (sem dependências externas)
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
                f"sine=frequency=440:duration={seconds}",
                str(dest),
            ],
            check=True,
        )

    def test_real_convert_produces_ogg(self, tmp_path: Path) -> None:
        src = tmp_path / "tone.wav"
        self._make_wav(src, seconds=2)
        dest = tmp_path / "tone.ogg"

        conv = FfmpegAudioConverter()
        result = conv.convert_to_opus_mono(src, dest, bitrate_kbps=32)

        assert result.path.exists()
        assert result.size_bytes > 0
        # Confirma que é OGG via ffprobe.
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_name,channels",
                "-of",
                "json",
                str(dest),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert "opus" in proc.stdout
        assert '"channels": 1' in proc.stdout

    def test_real_convert_compression_works(self, tmp_path: Path) -> None:
        src = tmp_path / "tone.wav"
        self._make_wav(src, seconds=3)
        dest = tmp_path / "tone.ogg"
        conv = FfmpegAudioConverter()
        result = conv.convert_to_opus_mono(src, dest, bitrate_kbps=24)
        # WAV de 3s @ 44.1kHz mono deve ser bem maior que o ogg comprimido.
        assert result.size_bytes < src.stat().st_size

    def test_real_probe_duration(self, tmp_path: Path) -> None:
        src = tmp_path / "tone.wav"
        self._make_wav(src, seconds=2)
        conv = FfmpegAudioConverter()
        # split_for_telegram com threshold gigante → não particiona
        result = conv.split_for_telegram(src, tmp_path / "out", max_size_bytes=10**9)
        assert result == (src,)
