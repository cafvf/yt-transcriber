"""Read-only host/systemd preflight for PLAN-006 TASK-P06-005."""

from __future__ import annotations

import argparse
import json
import platform
import pwd
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

SUPPORTED_PYTHON = {(3, 11), (3, 12)}
REQUIRED_BINARIES = ("uv", "ffmpeg", "ffprobe", "systemctl", "journalctl")
_SECRET_ASSIGNMENT = re.compile(
    r"(?im)\b([A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|COOKIE)[A-Z0-9_]*)"
    r"\s*=\s*([^\s]+)"
)
_TELEGRAM_TOKEN = re.compile(r"\b\d{6,15}:[A-Za-z0-9_-]{20,}\b")
_HF_TOKEN = re.compile(r"\bhf_[A-Za-z0-9_-]{10,}\b")
_PRIVATE_IDENTIFIER_ASSIGNMENT = re.compile(r"(?i)\b(user_id|chat_id)\s*=\s*(-?\d{5,20})\b")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def sanitize_evidence_text(text: str) -> str:
    value = _SECRET_ASSIGNMENT.sub(lambda m: f"{m.group(1)}=<redacted>", text)
    value = _TELEGRAM_TOKEN.sub("<telegram-token-redacted>", value)
    value = _HF_TOKEN.sub("<hf-token-redacted>", value)
    return _PRIVATE_IDENTIFIER_ASSIGNMENT.sub(
        lambda m: f"{m.group(1)}=<private-identifier-redacted>",
        value,
    )


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), check=False, capture_output=True, text=True)


def _systemctl_value(service: str, prop: str) -> str:
    result = _run(["systemctl", "show", service, f"--property={prop}", "--value"])
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "<empty>"
        raise RuntimeError(f"systemctl show {prop} failed: {detail}")
    return result.stdout.strip()


def _environment_file_from_systemd(raw: str) -> Path | None:
    match = re.search(r"(/[^\s;]+)", raw)
    return Path(match.group(1)) if match else None


def _mode_is_restrictive(mode: int) -> bool:
    return stat.S_IMODE(mode) & 0o077 == 0


def _check_prerequisites() -> list[Check]:
    checks = [
        Check("linux", platform.system() == "Linux", platform.system()),
        Check(
            "python",
            sys.version_info[:2] in SUPPORTED_PYTHON,
            f"{sys.version_info.major}.{sys.version_info.minor}",
        ),
    ]
    for binary in REQUIRED_BINARIES:
        resolved = shutil.which(binary)
        checks.append(Check(f"binary:{binary}", resolved is not None, resolved or "not found"))
    return checks


def _check_service(service: str) -> tuple[list[Check], dict[str, str]]:
    props = {
        name: _systemctl_value(service, name)
        for name in (
            "User",
            "Group",
            "WorkingDirectory",
            "EnvironmentFiles",
            "ExecStart",
            "FragmentPath",
        )
    }
    user = props["User"]
    group = props["Group"]
    checks = [
        Check("service-user", bool(user) and user != "root", user or "<empty>"),
        Check("service-group", group != "root", group or "<default>"),
        Check(
            "working-directory",
            bool(props["WorkingDirectory"]) and Path(props["WorkingDirectory"]).is_dir(),
            props["WorkingDirectory"] or "<empty>",
        ),
        Check("exec-start", bool(props["ExecStart"]), props["ExecStart"] or "<empty>"),
        Check(
            "fragment-path",
            bool(props["FragmentPath"]) and Path(props["FragmentPath"]).is_file(),
            props["FragmentPath"] or "<empty>",
        ),
    ]
    env_path = _environment_file_from_systemd(props["EnvironmentFiles"])
    if env_path is None:
        checks.append(Check("environment-file", False, "not configured"))
    else:
        try:
            st = env_path.stat()
        except OSError as exc:
            checks.append(Check("environment-file", False, f"{env_path}: {exc}"))
        else:
            owner = pwd.getpwuid(st.st_uid).pw_name
            allowed_owners = {"root"}
            if user:
                allowed_owners.add(user)
            checks.append(
                Check(
                    "environment-file",
                    _mode_is_restrictive(st.st_mode) and owner in allowed_owners,
                    f"path={env_path} owner={owner} mode={stat.S_IMODE(st.st_mode):04o}",
                )
            )
    return checks, props


def build_report(service: str) -> dict[str, object]:
    checks = _check_prerequisites()
    props: dict[str, str] = {}
    try:
        service_checks, props = _check_service(service)
    except RuntimeError as exc:
        service_checks = [Check("systemd-service", False, sanitize_evidence_text(str(exc)))]
    checks.extend(service_checks)
    return {
        "schema_version": 1,
        "service": service,
        "passed": all(check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
        "service_properties": {
            key: sanitize_evidence_text(value)
            for key, value in props.items()
            if key != "EnvironmentFiles"
        },
        "environment_file_values_exposed": False,
    }


def write_report(report: dict[str, object], output: Path) -> None:
    parent_existed = output.parent.exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not parent_existed:
        output.parent.chmod(0o700)
    output.write_text(
        sanitize_evidence_text(json.dumps(report, indent=2, sort_keys=True)) + "\n",
        encoding="utf-8",
    )
    output.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only TASK-P06-005 host/systemd preflight.")
    parser.add_argument("--service", default="yt-transcriber-bot")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.service)
    print(sanitize_evidence_text(json.dumps(report, indent=2, sort_keys=True)))
    if args.output is not None:
        write_report(report, args.output)
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
