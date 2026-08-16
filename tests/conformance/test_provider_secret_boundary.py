# PLAN-003 provider-secret architectural boundary.
#
# The application-facing capability surface must never transport provider
# credentials. Concrete infrastructure adapters may own provider authentication
# internally, supplied by the composition edge.

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from yt_transcriber_bot.application.ports.diarization_engine import DiarizationEngine
from yt_transcriber_bot.infrastructure.diarization.pyannote_diarization import (
    PyannoteDiarizationEngine,
)
from yt_transcriber_bot.infrastructure.diarization.whisperx_diarization import (
    WhisperXDiarizationEngine,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"
APPLICATION_ROOT = PACKAGE_ROOT / "application"
PORTS_ROOT = APPLICATION_ROOT / "ports"
DOMAIN_ROOT = PACKAGE_ROOT / "domain"


def _is_credential_name(name: str) -> bool:
    normalized = name.lower()
    exact = {
        "token",
        "secret",
        "password",
        "cookie",
        "cookies",
        "api_key",
        "apikey",
        "authorization",
    }
    suffixes = (
        "_token",
        "_secret",
        "_password",
        "_cookie",
        "_cookies",
        "_api_key",
        "_apikey",
    )
    return normalized in exact or normalized.endswith(suffixes)


def _function_arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ]
    if node.args.vararg is not None:
        args.append(node.args.vararg)
    if node.args.kwarg is not None:
        args.append(node.args.kwarg)
    return [arg.arg for arg in args if arg.arg not in {"self", "cls"}]


def test_application_ports_do_not_transport_provider_credentials() -> None:
    violations: list[str] = []

    for path in PORTS_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for argument in _function_arguments(node):
                    if _is_credential_name(argument):
                        relative = path.relative_to(PACKAGE_ROOT).as_posix()
                        violations.append(f"{relative}:{node.name}:{argument}")

    assert not violations, f"credential-shaped application port arguments: {violations!r}"


def test_domain_does_not_define_provider_credential_fields() -> None:
    violations: list[str] = []

    for path in DOMAIN_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and _is_credential_name(node.target.id)
            ):
                relative = path.relative_to(PACKAGE_ROOT).as_posix()
                violations.append(f"{relative}:{node.target.id}")

    assert not violations, f"credential-shaped domain fields: {violations!r}"


def test_application_runtime_does_not_forward_provider_credentials() -> None:
    violations: list[str] = []

    for path in APPLICATION_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg and _is_credential_name(keyword.arg):
                    relative = path.relative_to(PACKAGE_ROOT).as_posix()
                    violations.append(f"{relative}:{keyword.arg}")

    assert not violations, f"provider credentials forwarded by application calls: {violations!r}"


def test_diarization_credentials_are_adapter_constructor_owned() -> None:
    port_params = inspect.signature(DiarizationEngine.diarize).parameters
    whisper_public = inspect.signature(WhisperXDiarizationEngine.diarize).parameters
    pyannote_public = inspect.signature(PyannoteDiarizationEngine.diarize).parameters

    assert "hf_token" not in port_params
    assert "hf_token" not in whisper_public
    assert "hf_token" not in pyannote_public

    whisper_ctor = inspect.signature(WhisperXDiarizationEngine.__init__).parameters
    pyannote_ctor = inspect.signature(PyannoteDiarizationEngine.__init__).parameters

    assert "hf_token" in whisper_ctor
    assert "hf_token" in pyannote_ctor
