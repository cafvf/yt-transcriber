"""Conformance checks for PLAN-001 security guardrails."""

from __future__ import annotations

from pathlib import Path


def test_entrypoint_blocks_unsupported_audience_before_product_handlers() -> None:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text(encoding="utf-8")

    guard = "MessageHandler(runtime.denied_audience_filter, on_unsupported_message)"
    first_product_handler = 'CommandHandler("start", on_start)'
    assert guard in source
    assert source.index(guard) < source.index(first_product_handler)
    assert "raise ApplicationHandlerStop" in source


def test_callback_audience_check_precedes_answer_and_adapter_dispatch() -> None:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text(encoding="utf-8")
    start = source.index("async def on_callback")
    end = source.index("application.add_handler", start)
    callback = source[start:end]

    check = "if not audience.allows"
    assert callback.index(check) < callback.index("await query.answer()")
    assert callback.index(check) < callback.index("await adapter.handle_callback_query")


def test_security_example_keeps_remote_code_disabled_and_credentials_inert() -> None:
    example = Path(".env.example").read_text(encoding="utf-8")

    assert "SUMMARY_TOKENIZER_TRUST_REMOTE_CODE=false" in example
    assert "REPLACE_ME_TELEGRAM_BOT_TOKEN" in example
    assert "hf_REPLACE_ME" in example
    assert "sk-" not in example


def test_security_policy_marks_sanitized_material_private_and_standard_backup_secret_free() -> None:
    policy = Path("docs/08-seguranca-e-segredos.md").read_text(encoding="utf-8").lower()

    assert "sanitizado" in policy
    assert "privado" in policy
    assert "backup padrão" in policy
    assert ".env" in policy
    assert "cookies" in policy
    assert "não deve carregar" in policy
    assert "exclu" in policy
    assert "revogar" in policy
    assert "rotacion" in policy


def test_locked_install_remains_the_reproducible_ci_authority() -> None:
    assert Path("uv.lock").is_file()
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "uv sync --locked --dev" in ci
