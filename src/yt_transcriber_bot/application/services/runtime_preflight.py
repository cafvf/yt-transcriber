"""Pure installed-runtime preflight policy.

This module evaluates already-collected local facts. It performs no network
access, filesystem mutation, database initialization, model loading or provider
startup.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.health_probe import HealthEnvironmentSnapshot
from yt_transcriber_bot.application.services.youtube_runtime_readiness import (
    assess_youtube_runtime,
)

SUPPORTED_PYTHON = {(3, 11), (3, 12)}
REQUIRED_MODULES = (
    "torch",
    "torchaudio",
    "whisperx",
    "pyannote.audio",
    "faster_whisper",
    "yt_dlp",
    "yt_dlp_ejs",
    "telegram",
    "sqlalchemy",
)
REQUIRED_EXECUTABLES = ("ffmpeg", "ffprobe", "yt-dlp")


@dataclass(frozen=True, slots=True)
class RuntimePreflightFacts:
    python_version: tuple[int, int, int]
    distribution_version: str | None
    module_available: Mapping[str, bool]
    executable_available: Mapping[str, bool]
    executable_versions: Mapping[str, str | None]
    settings_source: str
    development_checkout_detected: bool


@dataclass(frozen=True, slots=True)
class RuntimePreflightCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class RuntimePreflightReport:
    passed: bool
    checks: tuple[RuntimePreflightCheck, ...]
    settings_source: str
    development_checkout_detected: bool
    network_access_performed: bool = False
    filesystem_mutation_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
            "settings_source": self.settings_source,
            "development_checkout_detected": self.development_checkout_detected,
            "network_access_performed": self.network_access_performed,
            "filesystem_mutation_performed": self.filesystem_mutation_performed,
        }

    def render_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=True)

    def render_text(self) -> str:
        lines = ["YT Transcriber Bot — runtime preflight"]
        for check in self.checks:
            marker = "OK" if check.passed else "FAIL"
            lines.append(f"[{marker}] {check.name}: {check.detail}")
        lines.append(f"settings source: {self.settings_source}")
        lines.append(
            "development checkout detected: "
            + ("yes" if self.development_checkout_detected else "no")
        )
        lines.append("result: PASS" if self.passed else "result: FAIL")
        return "\n".join(lines)


def _youtube_snapshot(facts: RuntimePreflightFacts) -> HealthEnvironmentSnapshot:
    return HealthEnvironmentSnapshot(
        python_detail="runtime preflight",
        project_root_found=facts.development_checkout_detected,
        env_file_state=facts.settings_source,
        executable_available=dict(facts.executable_available),
        module_available=dict(facts.module_available),
        directory_writable={},
        sqlite_error=None,
        operational_error_log_writable=True,
        operational_error_records=0,
        free_disk_mb=None,
        cookies_file_exists=None,
        model_ids=None,
        model_probe_error=None,
        executable_versions=dict(facts.executable_versions),
    )


def build_runtime_preflight(
    settings: AppSettings,
    facts: RuntimePreflightFacts,
) -> RuntimePreflightReport:
    checks: list[RuntimePreflightCheck] = []
    python_minor = facts.python_version[:2]
    checks.append(
        RuntimePreflightCheck(
            "python",
            python_minor in SUPPORTED_PYTHON,
            ".".join(str(part) for part in facts.python_version),
        )
    )
    checks.append(
        RuntimePreflightCheck(
            "installed distribution metadata",
            bool(facts.distribution_version),
            facts.distribution_version or "not installed",
        )
    )

    credentials = settings.credentials.status()
    telegram_ok = credentials.telegram_token_configured and credentials.telegram_token_shape_ok
    hf_ok = credentials.hf_token_configured and credentials.hf_token_shape_ok
    checks.extend(
        (
            RuntimePreflightCheck(
                "Telegram bot token",
                telegram_ok,
                "configured with expected shape" if telegram_ok else "missing or invalid shape",
            ),
            RuntimePreflightCheck(
                "Telegram allowed user",
                settings.telegram_allowed_user_id > 0,
                "configured" if settings.telegram_allowed_user_id > 0 else "missing or invalid",
            ),
            RuntimePreflightCheck(
                "Hugging Face token",
                hf_ok,
                "configured with expected shape" if hf_ok else "missing or invalid shape",
            ),
        )
    )

    for module in REQUIRED_MODULES:
        available = facts.module_available.get(module, False)
        checks.append(
            RuntimePreflightCheck(
                f"module:{module}",
                available,
                "available" if available else "missing",
            )
        )

    for executable in REQUIRED_EXECUTABLES:
        available = facts.executable_available.get(executable, False)
        checks.append(
            RuntimePreflightCheck(
                f"binary:{executable}",
                available,
                "available" if available else "missing",
            )
        )

    youtube = assess_youtube_runtime(_youtube_snapshot(facts))
    checks.append(
        RuntimePreflightCheck(
            "YouTube JavaScript runtime",
            youtube.status == "ok",
            youtube.detail,
        )
    )

    return RuntimePreflightReport(
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
        settings_source=facts.settings_source,
        development_checkout_detected=facts.development_checkout_detected,
    )
