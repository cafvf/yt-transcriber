from __future__ import annotations

import ast
from pathlib import Path

from yt_transcriber_bot.configuration.runtime_settings import (
    PRODUCTION_ENV_FILE,
    RuntimeSettingsSourceKind,
    resolve_runtime_settings_source,
)

REPO = Path(__file__).resolve().parents[2]


def test_production_environment_file_policy_is_canonical() -> None:
    assert Path("/etc/yt-transcriber-bot/env") == PRODUCTION_ENV_FILE
    service = (REPO / "deploy/yt-transcriber-bot.service").read_text(encoding="utf-8")
    assert "EnvironmentFile=/etc/yt-transcriber-bot/env" in service
    assert "UMask=0077" in service


def test_installed_runtime_does_not_select_arbitrary_cwd_dotenv(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SUMMARY_MODEL=should-not-load\n", encoding="utf-8")
    installed = (
        tmp_path
        / "venv"
        / "lib"
        / "python3.12"
        / "site-packages"
        / "yt_transcriber_bot"
        / "configuration"
        / "runtime_settings.py"
    )
    source = resolve_runtime_settings_source(
        environ={},
        cwd=tmp_path,
        module_file=installed,
    )
    assert source.kind is RuntimeSettingsSourceKind.PROCESS_ENVIRONMENT
    assert source.env_file is None


def test_application_config_contains_no_runtime_filesystem_discovery() -> None:
    text = (REPO / "src/yt_transcriber_bot/application/config.py").read_text(encoding="utf-8")
    for forbidden in (
        "find_project_root",
        "resolve_settings_env_file",
        "get_forced_settings_env_file",
        "pyproject.toml",
        "Path.cwd()",
        "SETTINGS_ENV_FILE_ENV_VAR",
    ):
        assert forbidden not in text


def test_provider_credentials_is_single_configuration_declaration_owner() -> None:
    configuration = REPO / "src/yt_transcriber_bot/configuration"
    canonical = {
        "telegram_bot_token",
        "hf_token",
        "summary_api_key",
        "youtube_cookies_file",
        "youtube_cookies_browser",
    }
    owners: dict[str, list[str]] = {field: [] for field in canonical}
    for path in configuration.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            declared = {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
            for field in declared & canonical:
                owners[field].append(f"{path.name}:{node.name}")

    assert owners == {field: ["credentials.py:ProviderCredentials"] for field in canonical}


def test_runtime_entrypoint_uses_runtime_loader() -> None:
    text = (REPO / "src/yt_transcriber_bot/__main__.py").read_text(encoding="utf-8")
    assert "settings = load_runtime_settings()" in text
