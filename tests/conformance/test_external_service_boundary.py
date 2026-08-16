# REQ-SEC-009 external-service disclosure boundary.

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION = ROOT / "src/yt_transcriber_bot/composition_root.py"
OPENAI = ROOT / "src/yt_transcriber_bot/infrastructure/summarization/openai_compatible_client.py"


def test_text_generation_endpoint_and_model_are_selected_from_trusted_settings() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert "base_url=settings.summary_base_url" in source
    assert "model=settings.summary_model" in source
    assert '"summary_base_url" in settings.model_fields_set' in source
    assert "require_transcript_disclosure_allowed()" in source


def test_composition_injects_shared_sanitization_into_outbound_adapters() -> None:
    source = COMPOSITION.read_text(encoding="utf-8")
    assert "sanitize_text(detail, settings)" in source
    assert source.count("error_sanitizer=error_sanitizer") >= 3


def test_openai_payload_builder_has_no_unrelated_private_fields() -> None:
    source = OPENAI.read_text(encoding="utf-8")
    for forbidden in (
        '"path":',
        '"logs":',
        '"cookies":',
        '"hf_token":',
        '"telegram_bot_token":',
    ):
        assert forbidden not in source
