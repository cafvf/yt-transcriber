from __future__ import annotations

from types import SimpleNamespace

from yt_transcriber_bot.infrastructure.operational import local_runtime_preflight


def test_local_preflight_collects_read_only_facts(monkeypatch) -> None:
    monkeypatch.setattr(
        local_runtime_preflight,
        "find_executable",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr(
        local_runtime_preflight,
        "probe_executable_version",
        lambda name: {
            "yt-dlp": "2026.08.19",
            "deno": "deno 2.3.0",
            "node": "v22.0.0",
        }.get(name),
    )
    monkeypatch.setattr(
        local_runtime_preflight,
        "module_available",
        lambda _name: True,
    )
    monkeypatch.setattr(
        local_runtime_preflight,
        "_distribution_version",
        lambda: "0.1.3",
    )
    monkeypatch.setattr(
        local_runtime_preflight,
        "resolve_runtime_settings_source",
        lambda: SimpleNamespace(kind=SimpleNamespace(value="process_environment")),
    )
    monkeypatch.setattr(
        local_runtime_preflight,
        "find_development_checkout_root",
        lambda: None,
    )
    monkeypatch.setattr(
        local_runtime_preflight.platform,
        "python_version_tuple",
        lambda: ("3", "12", "7"),
    )

    facts = local_runtime_preflight.collect_local_runtime_preflight()

    assert facts.python_version == (3, 12, 7)
    assert facts.distribution_version == "0.1.3"
    assert facts.settings_source == "process_environment"
    assert facts.development_checkout_detected is False
    assert facts.executable_versions["deno"] == "deno 2.3.0"
