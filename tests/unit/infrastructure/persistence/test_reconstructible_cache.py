from __future__ import annotations

from pathlib import Path

from yt_transcriber_bot.infrastructure.persistence.filesystem.reconstructible_cache import (
    FilesystemReconstructibleCache,
)


def test_cache_cleanup_is_contained_and_preserves_canonical_data(tmp_path: Path) -> None:
    cache = tmp_path / "models"
    cache.mkdir()
    (cache / "model.bin").write_bytes(b"x")
    nested = cache / "tokenizer"
    nested.mkdir()
    (nested / "tokenizer.json").write_text("{}", encoding="utf-8")
    canonical = [
        tmp_path / "data/jobs.db",
        tmp_path / "data/transcripts/video.md",
        tmp_path / "data/summaries/video.summary.md",
    ]
    for item in canonical:
        item.parent.mkdir(parents=True, exist_ok=True)
        item.write_text("keep", encoding="utf-8")
    result = FilesystemReconstructibleCache((cache,)).clear()
    assert result.failures == 0
    assert not any(cache.iterdir())
    assert all(item.read_text(encoding="utf-8") == "keep" for item in canonical)
