from __future__ import annotations

from dataclasses import replace

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.health_probe import (
    HealthEnvironmentProbe,
    HealthEnvironmentSnapshot,
)
from yt_transcriber_bot.application.services.healthcheck import HealthCheckService


class FakeProbe(HealthEnvironmentProbe):
    def __init__(
        self,
        *,
        model_ids: tuple[str, ...] | None = ("qwen3.5-9b",),
        model_error: str | None = None,
    ) -> None:
        self.model_ids = model_ids
        self.model_error = model_error

    def snapshot(self) -> HealthEnvironmentSnapshot:
        return HealthEnvironmentSnapshot(
            python_detail="CPython test",
            project_root_found=True,
            env_file_state="arquivo runtime encontrado.",
            executable_available={
                "ffmpeg": True,
                "ffprobe": True,
                "yt-dlp": True,
                "deno": True,
                "node": False,
            },
            module_available={
                "yt_dlp": True,
                "yt_dlp_ejs": True,
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
            operational_error_records=3,
            free_disk_mb=10_000,
            cookies_file_exists=None,
            model_ids=self.model_ids,
            model_probe_error=self.model_error,
            executable_versions={"yt-dlp": "2026.08.19", "deno": "deno 2.4.1"},
        )


def _settings(**kwargs: object) -> AppSettings:
    return AppSettings(
        _env_file=None,
        telegram_allowed_user_id=7,
        telegram_bot_token="1234567890:" + "x" * 35,
        hf_token="hf_" + "x" * 30,
        youtube_cookies_browser="firefox",
        summary_model="qwen3.5-9b",
        **kwargs,
    )


def test_healthcheck_policy_maps_injected_facts_without_host_io() -> None:
    settings = _settings()
    report = HealthCheckService(settings=settings, environment_probe=FakeProbe()).run()
    rendered = report.render(settings)
    assert report.overall_status == "ok"
    assert "Python" in rendered
    assert "SQLite" in rendered
    assert "Registro de erros operacionais" in rendered
    assert "LM Studio" in rendered


def test_healthcheck_reports_missing_summary_model() -> None:
    settings = _settings()
    report = HealthCheckService(
        settings=settings,
        environment_probe=FakeProbe(model_ids=("other",)),
    ).run()
    assert report.overall_status == "fail"
    assert "não aparece em /models" in report.render(settings)


def test_healthcheck_sanitizes_probe_error() -> None:
    settings = _settings(summary_api_key="secret-value")
    report = HealthCheckService(
        settings=settings,
        environment_probe=FakeProbe(model_error="boom secret-value"),
    ).run()
    assert "secret-value" not in report.render(settings)


# PLAN-007:C2-HEALTH-TESTS
def test_healthcheck_rejects_unsupported_javascript_runtime() -> None:
    settings = _settings()

    class OldRuntimeProbe(FakeProbe):
        def snapshot(self) -> HealthEnvironmentSnapshot:
            return replace(super().snapshot(), executable_versions={"deno": "deno 2.2.9"})

    report = HealthCheckService(settings=settings, environment_probe=OldRuntimeProbe()).run()
    assert report.overall_status == "fail"
    assert "abaixo do mínimo 2.3.0" in report.render(settings)
