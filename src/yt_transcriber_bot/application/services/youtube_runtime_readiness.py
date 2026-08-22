"""Deterministic YouTube JavaScript-runtime readiness policy."""

from __future__ import annotations

import re
from dataclasses import dataclass

from yt_transcriber_bot.application.ports.health_probe import HealthEnvironmentSnapshot

DENO_MINIMUM_VERSION = (2, 3, 0)
NODE_MINIMUM_VERSION = (22, 0, 0)


@dataclass(frozen=True, slots=True)
class JavaScriptRuntimeStatus:
    name: str
    present: bool
    raw_version: str | None
    parsed_version: tuple[int, int, int] | None
    minimum_version: tuple[int, int, int]
    supported: bool


@dataclass(frozen=True, slots=True)
class YouTubeRuntimeReadiness:
    status: str
    detail: str
    runtimes: tuple[JavaScriptRuntimeStatus, ...]


_VERSION_PATTERN = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)")


def parse_runtime_version(raw: str | None) -> tuple[int, int, int] | None:
    if not raw:
        return None
    match = _VERSION_PATTERN.search(raw)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def _runtime_status(
    facts: HealthEnvironmentSnapshot, *, name: str, minimum: tuple[int, int, int]
) -> JavaScriptRuntimeStatus:
    present = facts.executable_available.get(name, False)
    raw = facts.executable_versions.get(name)
    parsed = parse_runtime_version(raw)
    return JavaScriptRuntimeStatus(
        name, present, raw, parsed, minimum, present and parsed is not None and parsed >= minimum
    )


def _fmt(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def assess_youtube_runtime(facts: HealthEnvironmentSnapshot) -> YouTubeRuntimeReadiness:
    runtimes = (
        _runtime_status(facts, name="deno", minimum=DENO_MINIMUM_VERSION),
        _runtime_status(facts, name="node", minimum=NODE_MINIMUM_VERSION),
    )
    if not facts.module_available.get("yt_dlp", False):
        return YouTubeRuntimeReadiness("fail", "módulo yt_dlp ausente.", runtimes)
    if not facts.module_available.get("yt_dlp_ejs", False):
        return YouTubeRuntimeReadiness(
            "fail", "yt-dlp-ejs ausente; a instalação PyPI deve usar yt-dlp[default].", runtimes
        )
    supported = [runtime for runtime in runtimes if runtime.supported]
    if supported:
        detail = ", ".join(
            f"{runtime.name} {runtime.raw_version or _fmt(runtime.parsed_version or runtime.minimum_version)}"
            for runtime in supported
        )
        return YouTubeRuntimeReadiness("ok", "runtime JS suportado: " + detail + ".", runtimes)
    details: list[str] = []
    for runtime in runtimes:
        minimum = _fmt(runtime.minimum_version)
        if not runtime.present:
            details.append(f"{runtime.name} ausente (mínimo {minimum})")
        elif runtime.parsed_version is None:
            details.append(f"{runtime.name} com versão não identificável (mínimo {minimum})")
        else:
            details.append(
                f"{runtime.name} {_fmt(runtime.parsed_version)} abaixo do mínimo {minimum}"
            )
    return YouTubeRuntimeReadiness(
        "fail", "nenhum runtime JS suportado; " + "; ".join(details) + ".", runtimes
    )
