from __future__ import annotations

from yt_transcriber_bot.application.ports.health_probe import HealthEnvironmentSnapshot
from yt_transcriber_bot.application.services.youtube_runtime_readiness import (
    assess_youtube_runtime,
    parse_runtime_version,
)


def _facts(
    *,
    deno: bool = False,
    deno_version: str | None = None,
    node: bool = False,
    node_version: str | None = None,
    ejs: bool = True,
) -> HealthEnvironmentSnapshot:
    return HealthEnvironmentSnapshot(
        python_detail="CPython test",
        project_root_found=False,
        env_file_state="process environment",
        executable_available={
            "ffmpeg": True,
            "ffprobe": True,
            "yt-dlp": True,
            "deno": deno,
            "node": node,
        },
        module_available={"yt_dlp": True, "yt_dlp_ejs": ejs},
        directory_writable={},
        sqlite_error=None,
        operational_error_log_writable=True,
        operational_error_records=0,
        free_disk_mb=1000,
        cookies_file_exists=None,
        model_ids=None,
        model_probe_error=None,
        executable_versions={"deno": deno_version, "node": node_version, "yt-dlp": "2026.08.19"},
    )


def test_version_parser_accepts_vendor_outputs() -> None:
    assert parse_runtime_version("deno 2.3.0") == (2, 3, 0)
    assert parse_runtime_version("v22.12.1") == (22, 12, 1)


def test_supported_deno_is_ready() -> None:
    assert assess_youtube_runtime(_facts(deno=True, deno_version="deno 2.3.0")).status == "ok"


def test_supported_node_is_ready_when_deno_is_old() -> None:
    result = assess_youtube_runtime(
        _facts(deno=True, deno_version="deno 2.2.9", node=True, node_version="v22.0.0")
    )
    assert result.status == "ok"
    assert result.runtimes[0].supported is False
    assert result.runtimes[1].supported is True


def test_old_or_unparseable_runtimes_fail() -> None:
    result = assess_youtube_runtime(
        _facts(deno=True, deno_version="deno 2.2.9", node=True, node_version="node unknown")
    )
    assert result.status == "fail"
    assert "abaixo do mínimo 2.3.0" in result.detail
    assert "versão não identificável" in result.detail


def test_missing_ejs_fails_even_with_supported_runtime() -> None:
    result = assess_youtube_runtime(_facts(deno=True, deno_version="deno 2.4.1", ejs=False))
    assert result.status == "fail"
    assert "yt-dlp-ejs ausente" in result.detail
