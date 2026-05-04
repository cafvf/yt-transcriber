"""Fixtures globais de teste."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_project_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Evita que o ``.env`` local do desenvolvedor contamine a suíte.

    A aplicação, em runtime, descobre automaticamente o ``.env`` da raiz do
    projeto. Isso é desejável para execução real, mas em testes unitários faria
    valores locais como ``WHISPER_MODEL_PT`` ou ``SUMMARY_MODEL`` alterarem as
    expectativas. Por padrão, cada teste aponta para um ``.env`` isolado e
    inexistente. Testes que precisam validar leitura de dotenv podem criar esse
    arquivo ou sobrescrever ``YT_TRANSCRIBER_ENV_FILE`` explicitamente.
    """

    monkeypatch.setenv("YT_TRANSCRIBER_ENV_FILE", str(tmp_path / ".env"))
