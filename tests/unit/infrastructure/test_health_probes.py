from __future__ import annotations

from types import SimpleNamespace

from yt_transcriber_bot.infrastructure.operational import health_probes


def test_probe_executable_version_returns_first_nonempty_line(monkeypatch) -> None:
    monkeypatch.setattr(health_probes, "find_executable", lambda _name: "/usr/bin/fake")
    monkeypatch.setattr(
        health_probes.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="\n deno 2.4.1\nv8 13.0\n"),
    )
    assert health_probes.probe_executable_version("deno") == "deno 2.4.1"


def test_probe_executable_version_returns_none_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(health_probes, "find_executable", lambda _name: None)
    assert health_probes.probe_executable_version("deno") is None


def test_probe_executable_version_returns_none_on_command_failure(monkeypatch) -> None:
    monkeypatch.setattr(health_probes, "find_executable", lambda _name: "/usr/bin/fake")
    monkeypatch.setattr(
        health_probes.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="boom"),
    )
    assert health_probes.probe_executable_version("node") is None
