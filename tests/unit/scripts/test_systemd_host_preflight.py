from __future__ import annotations

import importlib.util
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path("scripts/ops/systemd_host_preflight.py")


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("systemd_host_preflight", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_sanitizer_redacts_reusable_credentials() -> None:
    module = _load()
    text = (
        "TELEGRAM_BOT_TOKEN=123456789:DUMMYabcdefghijklmnop "
        "HF_TOKEN=hf_DUMMYabcdefghij "
        "SUMMARY_API_KEY=DUMMY-summary-key"
    )
    sanitized = module.sanitize_evidence_text(text)
    assert "DUMMYabcdefghijklmnop" not in sanitized
    assert "hf_DUMMYabcdefghij" not in sanitized
    assert "DUMMY-summary-key" not in sanitized


@pytest.mark.parametrize(
    ("mode", "expected"),
    [(0o600, True), (0o400, True), (0o640, False), (0o644, False), (0o666, False)],
)
def test_secret_env_mode_contract(mode: int, expected: bool) -> None:
    module = _load()
    assert module._mode_is_restrictive(stat.S_IFREG | mode) is expected


def test_environment_file_parser_accepts_systemd_rendering() -> None:
    module = _load()
    assert module._environment_file_from_systemd(
        "/etc/yt-transcriber-bot/env (ignore_errors=no)"
    ) == Path("/etc/yt-transcriber-bot/env")


def test_service_contract_rejects_root_and_permissive_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load()
    work = tmp_path / "app"
    work.mkdir()
    unit = tmp_path / "service"
    unit.write_text("[Service]\n", encoding="utf-8")
    env = tmp_path / "env"
    env.write_text("TOKEN=placeholder\n", encoding="utf-8")
    env.chmod(0o644)

    values = {
        "User": "root",
        "Group": "root",
        "WorkingDirectory": str(work),
        "EnvironmentFiles": f"{env} (ignore_errors=no)",
        "ExecStart": "{ path=/usr/bin/uv ; argv[]=/usr/bin/uv run python -m x ; }",
        "FragmentPath": str(unit),
    }
    monkeypatch.setattr(module, "_systemctl_value", lambda _service, prop: values[prop])
    monkeypatch.setattr(module.pwd, "getpwuid", lambda _uid: type("P", (), {"pw_name": "root"})())

    checks, _ = module._check_service("demo")
    by_name = {check.name: check for check in checks}
    assert not by_name["service-user"].passed
    assert not by_name["service-group"].passed
    assert not by_name["environment-file"].passed


def test_report_never_exposes_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load()
    monkeypatch.setattr(
        module,
        "_check_prerequisites",
        lambda: [module.Check("linux", True, "Linux")],
    )
    monkeypatch.setattr(
        module,
        "_check_service",
        lambda _service: (
            [module.Check("service-user", True, "bot")],
            {"User": "bot", "EnvironmentFiles": "/etc/x SECRET_TOKEN=dont-print-this"},
        ),
    )
    report = module.build_report("demo")
    assert report["environment_file_values_exposed"] is False
    assert "EnvironmentFiles" not in report["service_properties"]
    assert "dont-print-this" not in str(report)


def test_sanitizer_redacts_private_numeric_identifiers() -> None:
    module = _load()
    text = "Iniciando bot. user_id=123456789\nchat_id=-1001234567890\njobs=13 pid=180326"
    sanitized = module.sanitize_evidence_text(text)
    assert "user_id=123456789" not in sanitized
    assert "chat_id=-1001234567890" not in sanitized
    assert "user_id=<private-identifier-redacted>" in sanitized
    assert "chat_id=<private-identifier-redacted>" in sanitized
    assert "jobs=13" in sanitized
    assert "pid=180326" in sanitized


def test_write_report_preserves_existing_parent_mode_and_writes_valid_json(
    tmp_path: Path,
) -> None:
    import json

    module = _load()
    parent = tmp_path / "shared"
    parent.mkdir()
    parent.chmod(0o777)
    output = parent / "preflight.json"
    report = {"passed": True, "checks": []}

    module.write_report(report, output)

    assert stat.S_IMODE(parent.stat().st_mode) == 0o777
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_write_report_protects_parent_created_by_helper(tmp_path: Path) -> None:
    module = _load()
    parent = tmp_path / "new-private-evidence"
    output = parent / "preflight.json"

    module.write_report({"passed": True}, output)

    assert stat.S_IMODE(parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
