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


def test_healthcheck_reports_ok_when_core_dependencies_and_model_are_available(tmp_path: Path) -> None:
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
