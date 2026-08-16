from __future__ import annotations

import ast
from pathlib import Path


def test_p04_admission_workflow_is_application_owned_and_transport_free() -> None:
    path = Path("src/yt_transcriber_bot/application/workflows/admission.py")
    source = path.read_text(encoding="utf-8")

    assert "yt_transcriber_bot.infrastructure" not in source
    assert "telegram.ext" not in source
    assert "TelegramBotAdapter" not in source


def test_telegram_adapter_delegates_admission_instead_of_owning_legacy_rules() -> None:
    path = Path("src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    adapter = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TelegramBotAdapter"
    )
    method_names = {
        node.name
        for node in adapter.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "_validate_incoming_media" not in method_names
    assert "_is_already_queued" not in method_names
    assert "_create_persisted_job" not in method_names
    assert "admit_youtube_submission" in source
    assert "prepare_validated_media_submission" in source
    assert "commit_media_submission" in source
