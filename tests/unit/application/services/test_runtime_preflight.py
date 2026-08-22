from __future__ import annotations

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.runtime_preflight import (
    REQUIRED_MODULES,
    RuntimePreflightFacts,
    build_runtime_preflight,
)


def _settings() -> AppSettings:
    return AppSettings(
        _env_file=None,
        telegram_allowed_user_id=7,
        telegram_bot_token=("1" * 9) + ":" + ("x" * 35),
        hf_token="hf_" + ("x" * 30),
        summary_backend="disabled",
    )


def _facts(
    *,
    node_version: str | None = "v22.0.0",
    distribution_version: str | None = "0.1.3",
) -> RuntimePreflightFacts:
    modules = dict.fromkeys(REQUIRED_MODULES, True)
    return RuntimePreflightFacts(
        python_version=(3, 12, 7),
        distribution_version=distribution_version,
        module_available=modules,
        executable_available={
            "ffmpeg": True,
            "ffprobe": True,
            "yt-dlp": True,
            "deno": False,
            "node": node_version is not None,
        },
        executable_versions={
            "yt-dlp": "2026.08.19",
            "node": node_version,
        },
        settings_source="process_environment",
        development_checkout_detected=False,
    )


def test_runtime_preflight_passes_supported_installed_runtime() -> None:
    report = build_runtime_preflight(_settings(), _facts())
    assert report.passed is True
    assert report.network_access_performed is False
    assert report.filesystem_mutation_performed is False


def test_runtime_preflight_fails_without_supported_js_runtime() -> None:
    report = build_runtime_preflight(
        _settings(),
        _facts(node_version="v21.9.0"),
    )
    assert report.passed is False
    failed = {check.name: check for check in report.checks if not check.passed}
    assert "YouTube JavaScript runtime" in failed


def test_runtime_preflight_fails_without_distribution_metadata() -> None:
    report = build_runtime_preflight(
        _settings(),
        _facts(distribution_version=None),
    )
    assert report.passed is False


def test_runtime_preflight_output_never_contains_credential_values() -> None:
    settings = _settings()
    report = build_runtime_preflight(settings, _facts())
    rendered = report.render_json() + report.render_text()
    assert settings.telegram_bot_token not in rendered
    assert settings.hf_token not in rendered
    assert "configured with expected shape" in rendered
