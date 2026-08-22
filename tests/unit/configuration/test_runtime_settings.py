from __future__ import annotations

from pathlib import Path

import pytest

from yt_transcriber_bot.configuration.runtime_settings import (
    PRODUCTION_ENV_FILE,
    RuntimeSettingsSource,
    RuntimeSettingsSourceKind,
    find_development_checkout_root,
    get_forced_settings_env_file,
    load_runtime_settings,
    resolve_runtime_settings_source,
)


@pytest.fixture
def clean_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "YT_TRANSCRIBER_ENV_FILE",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_USER_ID",
        "HF_TOKEN",
        "SUMMARY_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def _source_module(root: Path) -> Path:
    path = root / "src/yt_transcriber_bot/configuration/runtime_settings.py"
    path.parent.mkdir(parents=True)
    path.write_text("# synthetic source marker\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "yt-transcriber-bot"\n',
        encoding="utf-8",
    )
    return path


def test_production_env_path_is_stable() -> None:
    assert Path("/etc/yt-transcriber-bot/env") == PRODUCTION_ENV_FILE


def test_explicit_absolute_env_file_wins(clean_runtime_env: None, tmp_path: Path) -> None:
    env_file = tmp_path / "private.env"
    source = resolve_runtime_settings_source(
        environ={"YT_TRANSCRIBER_ENV_FILE": str(env_file)},
        cwd=tmp_path,
        module_file=tmp_path / "installed/runtime_settings.py",
    )
    assert source == RuntimeSettingsSource(
        RuntimeSettingsSourceKind.EXPLICIT_ENV_FILE,
        env_file.resolve(),
    )


def test_explicit_relative_env_file_preserves_cwd_resolution(
    clean_runtime_env: None, tmp_path: Path
) -> None:
    resolved = get_forced_settings_env_file(
        environ={"YT_TRANSCRIBER_ENV_FILE": "config/private.env"},
        cwd=tmp_path,
    )
    assert resolved == (tmp_path / "config/private.env").resolve()


def test_explicit_env_example_is_rejected(clean_runtime_env: None, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"\.env\.example"):
        get_forced_settings_env_file(
            environ={"YT_TRANSCRIBER_ENV_FILE": ".env.example"},
            cwd=tmp_path,
        )


def test_real_source_checkout_selects_development_dotenv(
    clean_runtime_env: None, tmp_path: Path
) -> None:
    module = _source_module(tmp_path)
    assert find_development_checkout_root(module) == tmp_path
    source = resolve_runtime_settings_source(
        environ={},
        cwd=tmp_path / "elsewhere",
        module_file=module,
    )
    assert source.kind is RuntimeSettingsSourceKind.DEVELOPMENT_DOTENV
    assert source.env_file == tmp_path / ".env"


def test_site_packages_inside_repo_does_not_become_source_checkout(
    clean_runtime_env: None, tmp_path: Path
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "yt-transcriber-bot"\n',
        encoding="utf-8",
    )
    installed = (
        tmp_path
        / ".venv/lib/python3.12/site-packages/yt_transcriber_bot/configuration/runtime_settings.py"
    )
    installed.parent.mkdir(parents=True)
    installed.write_text("# installed\n", encoding="utf-8")
    assert find_development_checkout_root(installed) is None


def test_installed_runtime_ignores_arbitrary_cwd_dotenv(
    clean_runtime_env: None, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text("SUMMARY_MODEL=wrong\n", encoding="utf-8")
    source = resolve_runtime_settings_source(
        environ={},
        cwd=tmp_path,
        module_file=tmp_path / "site-packages/pkg/runtime_settings.py",
    )
    assert source.kind is RuntimeSettingsSourceKind.PROCESS_ENVIRONMENT
    assert source.env_file is None


def test_process_environment_loads_without_dotenv(
    clean_runtime_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUMMARY_MODEL", "process-model")
    source = RuntimeSettingsSource(RuntimeSettingsSourceKind.PROCESS_ENVIRONMENT)
    settings = load_runtime_settings(source)
    assert settings.summary_model == "process-model"


def test_one_explicit_dotenv_drives_settings_and_credentials(
    clean_runtime_env: None, tmp_path: Path
) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text(
        "SUMMARY_MODEL=dotenv-model\n"
        "TELEGRAM_BOT_TOKEN=telegram-unit-test-value\n"
        "HF_TOKEN=unit-test-hf-value\n",
        encoding="utf-8",
    )
    source = RuntimeSettingsSource(
        RuntimeSettingsSourceKind.EXPLICIT_ENV_FILE,
        env_file,
    )
    settings = load_runtime_settings(source)
    assert settings.summary_model == "dotenv-model"
    assert settings.telegram_bot_token == "telegram-unit-test-value"
    assert settings.hf_token == "unit-test-hf-value"


def test_real_environment_overrides_explicit_dotenv_for_settings_and_credentials(
    clean_runtime_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "private.env"
    env_file.write_text(
        "SUMMARY_MODEL=dotenv-model\nHF_TOKEN=dotenv-hf-value\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SUMMARY_MODEL", "process-model")
    monkeypatch.setenv("HF_TOKEN", "process-hf-value")
    source = RuntimeSettingsSource(
        RuntimeSettingsSourceKind.EXPLICIT_ENV_FILE,
        env_file,
    )
    settings = load_runtime_settings(source)
    assert settings.summary_model == "process-model"
    assert settings.hf_token == "process-hf-value"


def test_effective_settings_report_describes_source_without_raw_secrets(
    clean_runtime_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from scripts.config.print_effective_settings import build_report_lines

    env_file = tmp_path / "private.env"
    raw_secret = "opaque-private-report-value-92817"
    env_file.write_text(
        f"SUMMARY_MODEL=dotenv-model\nHF_TOKEN={raw_secret}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SUMMARY_MODEL", "process-model")
    source = RuntimeSettingsSource(
        RuntimeSettingsSourceKind.EXPLICIT_ENV_FILE,
        env_file,
    )
    settings = load_runtime_settings(source)
    report = "\n".join(build_report_lines(settings, source))
    assert "Fonte runtime: explicit_env_file" in report
    assert "origem: ambiente real SUMMARY_MODEL (sobrescreve arquivo de ambiente)" in report
    assert raw_secret not in report
