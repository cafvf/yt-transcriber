"""Runtime configuration-source resolution for installed and development execution.

Production services inject ``/etc/yt-transcriber-bot/env`` through systemd's
``EnvironmentFile``. The application consumes the process environment and does
not need permission to open that root-owned file itself.

A repository ``.env`` remains a development convenience only when this module
is actually executing from ``<checkout>/src/yt_transcriber_bot/...``. Arbitrary
CWD does not opt an installed package into dotenv discovery.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

SETTINGS_ENV_FILE_ENV_VAR = "YT_TRANSCRIBER_ENV_FILE"
PROJECT_NAME = "yt-transcriber-bot"
PRODUCTION_ENV_FILE = Path("/etc/yt-transcriber-bot/env")

if TYPE_CHECKING:
    from yt_transcriber_bot.application.config import AppSettings


class RuntimeSettingsSourceKind(StrEnum):
    """How runtime settings are supplied to the installed process."""

    EXPLICIT_ENV_FILE = "explicit_env_file"
    DEVELOPMENT_DOTENV = "development_dotenv"
    PROCESS_ENVIRONMENT = "process_environment"


@dataclass(frozen=True, slots=True)
class RuntimeSettingsSource:
    """Resolved runtime settings source without containing secret values."""

    kind: RuntimeSettingsSourceKind
    env_file: Path | None = None


def _is_runtime_env_file(path: Path) -> bool:
    return path.name != ".env.example"


def get_forced_settings_env_file(
    *,
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> Path | None:
    """Resolve the operator-selected env file, preserving relative-path behavior."""

    env = os.environ if environ is None else environ
    value = env.get(SETTINGS_ENV_FILE_ENV_VAR, "").strip()
    if not value:
        return None

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (cwd or Path.cwd()) / path
    resolved = path.resolve()
    if not _is_runtime_env_file(resolved):
        raise ValueError(
            "YT_TRANSCRIBER_ENV_FILE aponta para .env.example. "
            "Esse arquivo é apenas template; escolha um arquivo runtime privado."
        )
    return resolved


def find_development_checkout_root(module_file: Path | None = None) -> Path | None:
    """Return a checkout only when this module itself lives under ``repo/src``."""

    module_path = (module_file or Path(__file__)).expanduser().resolve()
    try:
        candidate = module_path.parents[3]
    except IndexError:
        return None

    expected_module = (
        candidate / "src" / "yt_transcriber_bot" / "configuration" / "runtime_settings.py"
    )
    if expected_module.resolve() != module_path:
        return None

    pyproject = candidate / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        content = pyproject.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if f'name = "{PROJECT_NAME}"' not in content and f"name = '{PROJECT_NAME}'" not in content:
        return None
    return candidate


def resolve_runtime_settings_source(
    *,
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    module_file: Path | None = None,
) -> RuntimeSettingsSource:
    """Resolve settings without an implicit installed-runtime CWD fallback."""

    forced = get_forced_settings_env_file(environ=environ, cwd=cwd)
    if forced is not None:
        return RuntimeSettingsSource(
            kind=RuntimeSettingsSourceKind.EXPLICIT_ENV_FILE,
            env_file=forced,
        )

    checkout = find_development_checkout_root(module_file)
    if checkout is not None:
        return RuntimeSettingsSource(
            kind=RuntimeSettingsSourceKind.DEVELOPMENT_DOTENV,
            env_file=checkout / ".env",
        )

    return RuntimeSettingsSource(kind=RuntimeSettingsSourceKind.PROCESS_ENVIRONMENT)


def load_runtime_settings(
    source: RuntimeSettingsSource | None = None,
    **values: Any,
) -> AppSettings:
    """Build ``AppSettings`` from one already-resolved runtime source."""

    from yt_transcriber_bot.application.config import AppSettings

    resolved = source or resolve_runtime_settings_source()
    constructor_values = dict(values)
    if "_env_file" not in constructor_values:
        constructor_values["_env_file"] = resolved.env_file
    return AppSettings(**constructor_values)
