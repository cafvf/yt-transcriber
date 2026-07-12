"""SQLite health probe adapter."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteHealthProbe:
    """Executa uma checagem leve de leitura/escrita no banco SQLite configurado."""

    def __call__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            conn.execute("SELECT 1")
            conn.execute("CREATE TEMP TABLE IF NOT EXISTS healthcheck_ping(x INTEGER)")
            conn.execute("INSERT INTO healthcheck_ping(x) VALUES (1)")
            conn.execute("DELETE FROM healthcheck_ping")
