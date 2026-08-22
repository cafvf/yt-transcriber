"""Read-only local fact collection for installed runtime preflight."""

from __future__ import annotations

import importlib.metadata
import platform

from yt_transcriber_bot.application.services.runtime_preflight import (
    REQUIRED_EXECUTABLES,
    REQUIRED_MODULES,
    RuntimePreflightFacts,
)
from yt_transcriber_bot.configuration.runtime_settings import (
    find_development_checkout_root,
    resolve_runtime_settings_source,
)
from yt_transcriber_bot.infrastructure.operational.health_probes import (
    find_executable,
    module_available,
    probe_executable_version,
)

_JS_EXECUTABLES = ("deno", "node")
_VERSIONED_EXECUTABLES = ("yt-dlp", *_JS_EXECUTABLES)


def _distribution_version() -> str | None:
    try:
        return importlib.metadata.version("yt-transcriber-bot")
    except importlib.metadata.PackageNotFoundError:
        return None


def collect_local_runtime_preflight() -> RuntimePreflightFacts:
    executable_names = (*REQUIRED_EXECUTABLES, *_JS_EXECUTABLES)
    executables = {name: find_executable(name) is not None for name in executable_names}
    versions = {
        name: probe_executable_version(name)
        for name in _VERSIONED_EXECUTABLES
        if executables.get(name, False)
    }
    modules = {name: module_available(name) for name in REQUIRED_MODULES}
    source = resolve_runtime_settings_source()
    version_parts = tuple(int(part) for part in platform.python_version_tuple())
    return RuntimePreflightFacts(
        python_version=(version_parts[0], version_parts[1], version_parts[2]),
        distribution_version=_distribution_version(),
        module_available=modules,
        executable_available=executables,
        executable_versions=versions,
        settings_source=source.kind.value,
        development_checkout_detected=find_development_checkout_root() is not None,
    )
