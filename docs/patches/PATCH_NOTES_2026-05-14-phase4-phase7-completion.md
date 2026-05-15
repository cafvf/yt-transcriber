# Patch Notes — 2026-05-14 — Phase 4/7 completion

## Summary

Completed the remaining Phase 4 mojibake hardening and Phase 7 repository hygiene/documentation consistency track without starting Phase 5 performance work.

## Changes

- Added a sanitized warning when normalized artifact text still contains Unicode replacement characters after mojibake repair.
- Added integration-style regression coverage proving Markdown rendering and derived exports use central mojibake normalization.
- Updated architecture documentation to match the current `src/yt_transcriber_bot` module layout and current composition root.
- Removed duplicate patch notes from `docs/` and `deploy/`; `docs/patches/` is now the canonical patch-note location.
- Added tests that prevent future duplicate patch notes outside `docs/patches/` and guard architecture-documentation path drift.
- Clarified README/manual wording: deduplication applies to in-flight/queued same video+language jobs; completed-video reprocessing remains explicit via `/redo <link>`.

## Validation

- Targeted guard suite: `uv run pytest tests/unit/infrastructure/text/test_normalization.py tests/unit/infrastructure/rendering/test_markdown_renderer.py tests/unit/infrastructure/exporting/test_transcript_exporter.py tests/unit/test_patch_notes_location.py tests/unit/test_documentation_consistency.py -q`
- Repo hygiene spot checks: no stale architecture names, no patch notes directly under `docs/` or `deploy/`, no tracked `*:Zone.Identifier` files.

## Not included

- Phase 5 performance benchmarks/refactors remain intentionally untouched.
- Real Telegram/YouTube/ML end-to-end verification still requires local credentials and runtime setup.
