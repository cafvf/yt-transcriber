from __future__ import annotations

import tomllib
from pathlib import Path


def test_youtube_dependency_requires_known_good_ytdlp_with_default_extras() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert "yt-dlp[default]>=2026.7.4,<2027.0.0" in dependencies
