from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path("scripts/ops/upgrade_rollback_rehearsal.py")


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("upgrade_rollback_rehearsal_test", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_preflight_requires_clean_worktree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = _load()
    monkeypatch.setattr(
        script,
        "_run_ok",
        lambda command, cwd=None: script.CommandResult(tuple(command), 0, " M dirty", ""),
    )
    with pytest.raises(RuntimeError, match="clean worktree"):
        script._require_clean_worktree(tmp_path)


def test_preflight_binds_backup_to_source_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = _load()
    monkeypatch.setattr(script, "_require_clean_worktree", lambda _app: None)
    monkeypatch.setattr(
        script,
        "_resolve_ref",
        lambda _app, ref: {"old": "aaa", "new": "bbb", "HEAD": "bbb"}[ref],
    )
    monkeypatch.setattr(script, "_require_upgrade_relation", lambda *_args: None)
    monkeypatch.setattr(script, "_backup_revision", lambda _backup: "wrong")

    with pytest.raises(RuntimeError, match="does not match source revision"):
        script.build_preflight(
            app_dir=tmp_path,
            backup_dir=tmp_path / "backup",
            from_ref="old",
            to_ref="new",
        )


def test_preflight_report_is_non_mutating(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = _load()
    monkeypatch.setattr(script, "_require_clean_worktree", lambda _app: None)
    monkeypatch.setattr(
        script,
        "_resolve_ref",
        lambda _app, ref: {"old": "aaa", "new": "bbb", "HEAD": "bbb"}[ref],
    )
    monkeypatch.setattr(script, "_require_upgrade_relation", lambda *_args: None)
    monkeypatch.setattr(script, "_backup_revision", lambda _backup: "aaa")

    report = script.build_preflight(
        app_dir=tmp_path,
        backup_dir=tmp_path / "backup",
        from_ref="old",
        to_ref="new",
    )

    assert report["source_revision"] == "aaa"
    assert report["target_revision"] == "bbb"
    assert report["backup_revision"] == "aaa"
    assert report["production_mutated"] is False


def test_rehearsal_requires_explicit_execute(tmp_path: Path) -> None:
    script = _load()
    args = type(
        "Args",
        (),
        {
            "execute": False,
            "app_dir": tmp_path,
            "backup_dir": tmp_path / "backup",
            "from_ref": "old",
            "to_ref": "new",
            "service": "yt-transcriber-bot",
            "output_dir": tmp_path / "out",
        },
    )()

    with pytest.raises(RuntimeError, match="explicit --execute"):
        script.run_rehearsal(args)


def test_preflight_output_is_private(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = _load()
    monkeypatch.setattr(
        script,
        "build_preflight",
        lambda **_kwargs: {"production_mutated": False},
    )
    args = type(
        "Args",
        (),
        {
            "app_dir": tmp_path,
            "backup_dir": tmp_path / "backup",
            "from_ref": "old",
            "to_ref": "new",
            "output_dir": tmp_path / "evidence",
        },
    )()
    path = script.run_preflight(args)

    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert json.loads(path.read_text(encoding="utf-8"))["production_mutated"] is False
