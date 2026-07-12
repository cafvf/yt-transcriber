"""Testes do serviço de /healthcheck."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.services.healthcheck import HealthCheckService


def _settings(tmp_path: Path, **kwargs: object) -> AppSettings:
    values: dict[str, object] = {
        "telegram_bot_token": "dummy-telegram-token-for-tests",
        "telegram_allowed_user_id": 42,
        "hf_token": "alpha-bravo-charlie",
        "base_dir": tmp_path / "data",
        "models_dir": tmp_path / "models",
        "db_path": tmp_path / "data" / "jobs.db",
        "summary_model": "qwen/qwen3.5-9b",
    }
    values.update(kwargs)
    return AppSettings(**values)


def test_healthcheck_reports_ok_when_core_dependencies_and_model_are_available(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)

    def models_probe(url: str, headers: dict[str, str], timeout_s: float) -> dict[str, Any]:
        assert url.endswith("/models")
        assert timeout_s == settings.healthcheck_lmstudio_timeout_s
        return {"data": [{"id": "qwen/qwen3.5-9b"}]}

    service = HealthCheckService(
        settings=settings,
        models_probe=models_probe,
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
    )

    report = service.run()
    rendered = report.render(settings)

    assert report.overall_status in {"ok", "warn"}
    assert "LM Studio" in rendered
    assert "qwen/qwen3.5-9b" in rendered
    assert "dummy-telegram-token-for-tests" not in rendered
    assert "alpha-bravo-charlie" not in rendered


def test_healthcheck_fails_when_summary_model_is_absent_from_lm_studio(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_model="modelo-ausente")
    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "outro-modelo"}]},
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
    )

    report = service.run()
    rendered = report.render(settings)

    assert report.overall_status == "fail"
    assert "modelo-ausente" in rendered
    assert "não aparece em /models" in rendered


def test_healthcheck_sanitizes_summary_api_key_from_lm_studio_error(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_api_key="secret-api-key-123456")

    def broken_probe(*_args: object) -> dict[str, Any]:
        raise RuntimeError("authorization: Bearer dummy-bearer-token-for-tests")

    service = HealthCheckService(
        settings=settings,
        models_probe=broken_probe,
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
    )

    rendered = service.run().render(settings)

    assert "secret-api-key-123456" not in rendered
    assert "[REDACTED]" in rendered


def test_healthcheck_includes_extended_operational_checks(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "qwen/qwen3.5-9b"}]},
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
    )

    rendered = service.run().render(settings)

    assert "Python" in rendered
    assert "ffprobe" in rendered
    assert "Registro de erros operacionais" in rendered
    assert "Orçamento de sumarização" in rendered
    assert "Tokenizer de sumarização" in rendered
    assert "trust_remote_code=false" in rendered
    assert "Thinking da LLM" in rendered


def test_healthcheck_fails_when_huggingface_token_is_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_tokenizer_backend="hf")
    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "qwen/qwen3.5-9b"}]},
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: name != "transformers",
    )

    rendered = service.run().render(settings)

    assert "Healthcheck: problemas encontrados" in rendered
    assert "SUMMARY_TOKENIZER_BACKEND=hf exige transformers" in rendered


def test_healthcheck_does_not_expose_cookie_file_path(tmp_path: Path) -> None:
    cookies_path = tmp_path / "private" / "youtube-cookies.txt"
    cookies_path.parent.mkdir(parents=True)
    cookies_path.write_text("# " + "Netscape HTTP Cookie File\n", encoding="utf-8")
    settings = _settings(tmp_path, youtube_cookies_file=str(cookies_path))
    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "qwen/qwen3.5-9b"}]},
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
    )

    rendered = service.run().render(settings)

    assert "Cookies YouTube" in rendered
    assert "arquivo configurado existe" in rendered
    assert str(cookies_path) not in rendered


def test_healthcheck_render_does_not_expose_configured_local_paths(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "qwen/qwen3.5-9b"}]},
        executable_finder=lambda name: f"/private/bin/{name}",
        module_checker=lambda name: True,
    )

    rendered = service.run().render(settings)

    assert str(settings.base_dir) not in rendered
    assert str(settings.db_path) not in rendered
    assert str(settings.logs_dir()) not in rendered
    assert "/private/bin" not in rendered


def test_healthcheck_reports_tokenizer_remote_code_opt_in_safely(tmp_path: Path) -> None:
    settings = _settings(tmp_path, summary_tokenizer_trust_remote_code=True)
    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "qwen/qwen3.5-9b"}]},
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
    )

    rendered = service.run().render(settings)

    assert "trust_remote_code=true" in rendered
    assert "revise a origem do tokenizer" in rendered


def test_healthcheck_uses_injected_sqlite_probe(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    calls: list[Path] = []

    def sqlite_probe(path: Path) -> None:
        calls.append(path)

    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "qwen/qwen3.5-9b"}]},
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
        sqlite_probe=sqlite_probe,
    )

    rendered = service.run().render(settings)

    assert calls == [settings.db_path]
    assert "SQLite: acessível" in rendered


def test_healthcheck_reports_injected_sqlite_probe_failure(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    def sqlite_probe(_path: Path) -> None:
        raise RuntimeError(f"boom at {settings.db_path}")

    service = HealthCheckService(
        settings=settings,
        models_probe=lambda *_args: {"data": [{"id": "qwen/qwen3.5-9b"}]},
        executable_finder=lambda name: f"/usr/bin/{name}",
        module_checker=lambda name: True,
        sqlite_probe=sqlite_probe,
    )

    rendered = service.run().render(settings)

    assert "SQLite" in rendered
    assert "falha ao acessar o banco SQLite" in rendered
    assert str(settings.db_path) not in rendered
