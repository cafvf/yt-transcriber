# REQ-ARC-011 composition-root ownership conformance.

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from yt_transcriber_bot.composition_root import build, build_runtime

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "yt_transcriber_bot"
APPLICATION_ROOT = PACKAGE_ROOT / "application"
ENTRYPOINT = PACKAGE_ROOT / "__main__.py"
COMPOSITION_ROOT = PACKAGE_ROOT / "composition_root.py"

_PROVIDER_CONSTRUCTORS = {
    "FfprobeAudioDurationInspector",
    "OpenAICompatibleChatClient",
    "PTBBotClient",
    "PyannoteDiarizationEngine",
    "TelegramBotAdapter",
    "WhisperXDiarizationEngine",
    "WhisperXTranscriptionEngine",
    "YtDlpDownloader",
}


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def test_builders_require_explicit_keyword_only_credentials() -> None:
    for builder in (build, build_runtime):
        parameter = inspect.signature(builder).parameters["credentials"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_entrypoint_delegates_concrete_provider_graph_to_composition_root() -> None:
    source = ENTRYPOINT.read_text(encoding="utf-8")
    assert "build_runtime" in source
    assert "settings.credentials" in source
    assert "settings.telegram_bot_token" not in source
    assert "yt_transcriber_bot.infrastructure" not in source
    for fragment in (
        "Application.builder()",
        "PTBBotClient(",
        "TelegramBotAdapter(",
        "FfprobeAudioDurationInspector(",
        "TelegramAudiencePolicy(",
    ):
        assert fragment not in source


def test_composition_root_receives_credentials_explicitly_for_providers() -> None:
    source = COMPOSITION_ROOT.read_text(encoding="utf-8")
    assert "settings.credentials" not in source
    for fragment in (
        "credentials.telegram_bot_token",
        "credentials.hf_token",
        "credentials.summary_api_key",
        "credentials.youtube_cookies_file",
        "credentials.youtube_cookies_browser",
        "models_probe=probe_openai_compatible_models",
        "executable_finder=find_executable",
        "module_checker=module_available",
        "disk_usage=local_disk_usage",
        "sqlite_probe=SqliteHealthProbe()",
    ):
        assert fragment in source


def test_application_and_entrypoint_do_not_construct_known_providers() -> None:
    violations: list[str] = []
    paths = [ENTRYPOINT, *sorted(APPLICATION_ROOT.rglob("*.py"))]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _called_name(node)
            if name in _PROVIDER_CONSTRUCTORS:
                relative = path.relative_to(PACKAGE_ROOT).as_posix()
                violations.append(f"{relative}:{node.lineno}:{name}")
    assert not violations, f"concrete providers constructed inward: {violations!r}"


def test_runtime_summary_injects_composition_selected_tokenizer() -> None:
    tree = ast.parse(
        COMPOSITION_ROOT.read_text(encoding="utf-8"),
        filename=str(COMPOSITION_ROOT),
    )
    service_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "TranscriptSummaryService"
    ]
    tokenizer_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "make_text_tokenizer"
    ]
    assert len(service_calls) == 1
    assert len(tokenizer_calls) == 1
    assert "tokenizer" in {
        keyword.arg for keyword in service_calls[0].keywords if keyword.arg is not None
    }
