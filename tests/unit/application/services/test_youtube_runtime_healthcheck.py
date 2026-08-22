from __future__ import annotations

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.health_probe import (
    HealthEnvironmentProbe,
    HealthEnvironmentSnapshot,
)
from yt_transcriber_bot.application.services.healthcheck import HealthCheckService


class _Probe(HealthEnvironmentProbe):
    def __init__(self, *, node: bool, deno: bool, ejs: bool) -> None:
        self._node = node
        self._deno = deno
        self._ejs = ejs

    def snapshot(self) -> HealthEnvironmentSnapshot:
        return HealthEnvironmentSnapshot(
            python_detail="CPython test",
            project_root_found=True,
            env_file_state="arquivo runtime encontrado.",
            executable_available={
                "ffmpeg": True,
                "ffprobe": True,
                "yt-dlp": True,
                "node": self._node,
                "deno": self._deno,
            },
            module_available={
                "yt_dlp": True,
                "yt_dlp_ejs": self._ejs,
                "telegram": True,
                "sqlalchemy": True,
                "whisperx": True,
                "pyannote.audio": True,
                "transformers": True,
            },
            directory_writable={
                "base_dir": True,
                "downloads": True,
                "processed": True,
                "transcripts": True,
                "logs": True,
                "summaries": True,
                "video_exports": True,
                "models": True,
            },
            sqlite_error=None,
            operational_error_log_writable=True,
            operational_error_records=0,
            free_disk_mb=10_000,
            cookies_file_exists=None,
            model_ids=("qwen3.5-9b",),
            model_probe_error=None,
            executable_versions={
                "node": "v22.0.0" if self._node else None,
                "deno": "deno 2.3.0" if self._deno else None,
            },
        )


def _settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        telegram_allowed_user_id=7,
        telegram_bot_token="1234567890:" + "x" * 35,
        hf_token="hf_" + "x" * 30,
        youtube_cookies_browser="firefox",
        summary_model="qwen3.5-9b",
    )


def test_healthcheck_accepts_node_plus_ejs_for_youtube() -> None:
    settings = _settings()
    report = HealthCheckService(
        settings=settings,
        environment_probe=_Probe(node=True, deno=False, ejs=True),
    ).run()

    rendered = report.render(settings)
    assert report.overall_status == "ok"
    assert "Runtime JS do YouTube" in rendered
    assert "node" in rendered
    assert "yt-dlp EJS" in rendered


def test_healthcheck_fails_without_youtube_js_runtime() -> None:
    settings = _settings()
    report = HealthCheckService(
        settings=settings,
        environment_probe=_Probe(node=False, deno=False, ejs=True),
    ).run()

    assert report.overall_status == "fail"
    assert "Runtime JS do YouTube" in report.render(settings)


def test_healthcheck_fails_without_ytdlp_ejs() -> None:
    settings = _settings()
    report = HealthCheckService(
        settings=settings,
        environment_probe=_Probe(node=True, deno=False, ejs=False),
    ).run()

    assert report.overall_status == "fail"
    assert "yt-dlp EJS" in report.render(settings)
