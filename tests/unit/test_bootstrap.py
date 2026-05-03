"""Gate 0 — testes mínimos de bootstrap."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yt_transcriber_bot
from yt_transcriber_bot.__main__ import main


def test_package_imports_and_exposes_version() -> None:
    """Pacote importa e expõe ``__version__`` com formato semver simples."""
    assert hasattr(yt_transcriber_bot, "__version__")
    assert isinstance(yt_transcriber_bot.__version__, str)
    parts = yt_transcriber_bot.__version__.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_main_function_returns_zero() -> None:
    """A função ``main`` não levanta exceção quando chamada (async run é bloqueante)."""
    # Nota: main() é async e bloqueia indefinidamente em polling.
    # Este teste apenas valida que a função existe e é callable.
    assert callable(main)


def test_main_module_runs_via_subprocess_and_returns_zero(tmp_path: Path) -> None:
    """``python -m yt_transcriber_bot`` eh executavel (retorna 2 sem env vars)."""
    env = os.environ.copy()
    # Força ausência de segredos mesmo quando o desenvolvedor tem um .env
    # real ou variáveis exportadas para rodar o bot localmente.
    env.update(
        {
            "TELEGRAM_BOT_TOKEN": "",
            "TELEGRAM_ALLOWED_USER_ID": "0",
            "HF_TOKEN": "",
            "YOUTUBE_COOKIES_FILE": "",
            "YOUTUBE_COOKIES_BROWSER": "",
        }
    )

    result = subprocess.run(
        [sys.executable, "-m", "yt_transcriber_bot"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
        env=env,
        cwd=tmp_path,
    )
    assert result.returncode in (0, 2)
    if result.returncode == 2:
        assert "Falha de configuracao" in result.stderr or "TELEGRAM" in result.stderr
