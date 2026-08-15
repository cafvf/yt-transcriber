"""Regression checks for repository-facing documentation consistency."""

from __future__ import annotations

import re
from pathlib import Path

from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.models import JobModel


def _entrypoint_commands() -> set[str]:
    source = Path("src/yt_transcriber_bot/__main__.py").read_text(encoding="utf-8")
    commands: set[str] = set()
    commands.update(re.findall(r'CommandHandler\("([^"]+)"', source))
    for list_literal in re.findall(r"CommandHandler\(\[([^\]]+)\]", source):
        commands.update(re.findall(r'"([^"]+)"', list_literal))
    return commands


def _manual_quick_reference() -> str:
    manual = Path("docs/03-manual-de-uso.md").read_text(encoding="utf-8")
    start = manual.index("## Referência rápida de comandos")
    end = manual.index("## Funcionalidades planejadas")
    return manual[start:end]


def test_architecture_doc_uses_current_module_names() -> None:
    doc = Path("docs/02-arquitetura.md").read_text(encoding="utf-8")

    stale_names = (
        "bootstrap.py",
        "process_video.py",
        "VideoSource",
        "SubtitleSource",
        "ArtifactStore",
        "MessageGateway",
        "QueueRepository",
        "SpeakerMapRepository",
    )
    for name in stale_names:
        assert name not in doc

    current_paths = (
        "composition_root.py",
        "application/config.py",
        "application/use_cases/transcribe_video.py",
        "application/ports/youtube_downloader.py",
        "infrastructure/telegram/bot_adapter.py",
        "infrastructure/logging/execution_audit.py",
    )
    for path in current_paths:
        assert path in doc


def test_readme_and_manual_distinguish_inflight_dedup_from_redo() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    manual = Path("docs/03-manual-de-uso.md").read_text(encoding="utf-8")

    for doc in (readme, manual):
        assert "em processamento ou na fila" in doc
        assert "/redo <link>" in doc
        assert "concluído" in doc or "concluída" in doc
        assert "não pede confirmação inline" in doc or "reprocessa imediatamente" in doc


def test_manual_current_command_reference_matches_entrypoint() -> None:
    commands = _entrypoint_commands()
    manual_commands = _manual_quick_reference()

    expected = {
        "start",
        "help",
        "status",
        "healthcheck",
        "lasterror",
        "queue",
        "fila",
        "clearqueue",
        "cancelqueue",
        "limparfila",
        "cancelall",
        "cancelartudo",
        "cancel",
        "redo",
        "pt",
        "en",
        "transcribe",
        "list",
        "search",
        "last",
        "rename",
        "summary",
        "text",
        "export",
        "json",
        "srt",
        "vtt",
        "video_subs",
        "videosubs",
        "clearcache",
    }
    assert commands == expected
    for command in commands:
        assert re.search(rf"/{re.escape(command)}\b", manual_commands), command


def test_future_commands_are_not_documented_as_current() -> None:
    commands = _entrypoint_commands()
    help_text_source = Path(
        "src/yt_transcriber_bot/infrastructure/telegram/bot_adapter.py"
    ).read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    manual_future = (
        Path("docs/03-manual-de-uso.md")
        .read_text(encoding="utf-8")
        .split("## Funcionalidades planejadas", maxsplit=1)[1]
    )
    future_doc = Path("docs/06-funcionalidades-futuras.md").read_text(encoding="utf-8")

    assert "text" in commands
    assert "/text [n]" in help_text_source
    assert "/text [n]" in readme
    assert "/text [n]" not in manual_future

    assert "translate" not in commands
    assert "/translate" not in help_text_source
    assert "/translate" in readme
    assert "/translate" in manual_future
    assert "/translate" in future_doc

    assert "search" in commands
    assert "/search" in help_text_source
    assert "/search <texto>" in readme
    assert "/search <texto>" not in manual_future
    assert "/search semantic <texto>" in future_doc

    assert "Upload de áudio" not in manual_future
    assert "Aceita links do YouTube, áudio, mensagens de voz e documentos de áudio" in readme


def test_sqlite_schema_docs_match_current_models_and_mark_future_tables() -> None:
    model_columns = {column.name for column in JobModel.__table__.columns}
    expected_columns = {
        "job_id",
        "video_id",
        "status",
        "requested_by_user_id",
        "requested_at",
        "updated_at",
        "error_message",
        "source_url",
        "source_type",
        "canonical_reference",
        "source_title",
        "source_duration_seconds",
        "requested_chat_id",
        "requested_language",
        "artifact_policy",
        "config_signature",
        "canonical_transcript_ref",
        "speaker_renames_json",
        "md_path",
        "audio_path",
        "log_path",
    }
    assert model_columns == expected_columns

    contract = Path("docs/01-contrato-funcional.md").read_text(encoding="utf-8")
    architecture = Path("docs/02-arquitetura.md").read_text(encoding="utf-8")

    for column in expected_columns:
        assert f"`{column}`" in architecture

    assert "Não existem, nesta versão, tabelas ORM separadas `speakers` ou `queue`" in contract
    assert "Ainda não há tabelas separadas `speakers` ou `queue`" in architecture
    assert "Persiste as atribuições no próprio job, em `speaker_renames_json`" in contract
    assert "registro em `speakers`" not in contract
    assert "`queue` — fila persistente" not in contract
    assert "### 5.2 Tabela `speakers`" not in architecture
    assert "### 5.3 Tabela `queue`" not in architecture


def test_docs_identify_current_queue_as_in_memory_and_restart_recovery_as_implemented() -> None:
    docs = {
        "README.md": Path("README.md").read_text(encoding="utf-8"),
        "docs/01-contrato-funcional.md": Path("docs/01-contrato-funcional.md").read_text(
            encoding="utf-8"
        ),
        "docs/02-arquitetura.md": Path("docs/02-arquitetura.md").read_text(encoding="utf-8"),
        "docs/03-manual-de-uso.md": Path("docs/03-manual-de-uso.md").read_text(encoding="utf-8"),
        "docs/09-production-readiness.md": Path("docs/09-production-readiness.md").read_text(
            encoding="utf-8"
        ),
        "docs/10-recovery-semantics-adr.md": Path("docs/10-recovery-semantics-adr.md").read_text(
            encoding="utf-8"
        ),
    }

    for path, doc in docs.items():
        assert "restart" in doc or "reinício" in doc, path

    for path in (
        "README.md",
        "docs/01-contrato-funcional.md",
        "docs/02-arquitetura.md",
        "docs/09-production-readiness.md",
    ):
        assert "em memória" in docs[path], path

    manual = docs["docs/03-manual-de-uso.md"]
    assert "jobs `pending` com payload mínimo persistido" in manual
    assert "não tem fila durável nem recuperação automática após restart" not in manual

    adr = docs["docs/10-recovery-semantics-adr.md"]
    for field in ("source_url", "requested_chat_id", "requested_language", "artifact_policy"):
        assert field in adr


def test_docs_identify_delivery_failed_as_implemented() -> None:
    docs = {
        "README.md": Path("README.md").read_text(encoding="utf-8"),
        "docs/01-contrato-funcional.md": Path("docs/01-contrato-funcional.md").read_text(
            encoding="utf-8"
        ),
        "docs/02-arquitetura.md": Path("docs/02-arquitetura.md").read_text(encoding="utf-8"),
        "docs/03-manual-de-uso.md": Path("docs/03-manual-de-uso.md").read_text(encoding="utf-8"),
        "docs/06-funcionalidades-futuras.md": Path("docs/06-funcionalidades-futuras.md").read_text(
            encoding="utf-8"
        ),
        "docs/07-glossario-e-decisoes.md": Path("docs/07-glossario-e-decisoes.md").read_text(
            encoding="utf-8"
        ),
        "docs/09-production-readiness.md": Path("docs/09-production-readiness.md").read_text(
            encoding="utf-8"
        ),
    }

    for path, doc in docs.items():
        assert "delivery_failed" in doc, path
        assert "/lasterror" in doc, path

    all_docs = "\n".join(docs.values())
    stale_delivery_claims = (
        "não vira estado durável dedicado",
        "sem estado `delivery_failed`",
        "ainda não promove a falha de entrega para um estado",
        "Pode haver job concluído com artefato não entregue sem estado `delivery_failed`",
    )
    for claim in stale_delivery_claims:
        assert claim not in all_docs

    ledger = docs["docs/09-production-readiness.md"]
    assert "JobStatus.DELIVERING" in ledger
    assert "JobStatus.DELIVERY_FAILED" in ledger
    assert "transcribe_delivery" in ledger


def test_production_readiness_ledger_tracks_phase_zero_scope() -> None:
    ledger = Path("docs/09-production-readiness.md")
    assert ledger.exists()
    doc = ledger.read_text(encoding="utf-8")

    for phrase in (
        "Phase 0",
        "Fila durável e restart recovery",
        "speakers",
        "queue",
        "/search",
        "/text",
        "/translate",
        "/redo <link>",
        "delivery_failed",
    ):
        assert phrase in doc
