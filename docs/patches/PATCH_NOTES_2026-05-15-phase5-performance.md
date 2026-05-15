# Patch Notes — 2026-05-15 — Phase 5 performance hardening

## Summary

Implemented the Phase 5 measurement-first performance pass with a repeatable fake/non-ML benchmark harness, regression guards, and two measured low-risk hotspot optimizations.

## Changes

- Added `scripts/perf/benchmark_pipeline_fake.py` to benchmark:
  - fake pipeline overhead;
  - Markdown rendering;
  - subtitle parse/dedup;
  - summary chunk preparation;
  - snapshot-backed history title listing;
  - `/rename` multi-speaker workflow.
- Added a smoke test that runs the benchmark script and validates its JSON output contract.
- Optimized history title lookup for `/list` by loading snapshot metadata directly and by batching title prefetch before formatting rows.
- Optimized Markdown rendering by avoiding an extra normalization pass when accumulating readable speaker turns and by paragraphizing already-normalized turn text.
- Added regression coverage ensuring:
  - `/list` prefers batch metadata lookup when available;
  - renderer does not re-normalize accumulated turn text unnecessarily.

## Benchmark evidence

Command used:

- `uv run python scripts/perf/benchmark_pipeline_fake.py --output /tmp/yt-transcriber-benchmark-phase5.json --iterations 7`

Median timings in this environment:

- `markdown_render_legacy_reference`: **5.552 ms**
- `markdown_render`: **3.716 ms**
  - improvement: **33.1%**
- `snapshot_history_titles_legacy_reference`: **3.768 ms**
- `snapshot_history_titles`: **2.093 ms**
  - improvement: **44.5%**
- `pipeline_fake`: **5.005 ms**
- `summary_chunk_prep`: **4.167 ms**
- `rename_workflow`: **4.605 ms**

The benchmark script also records `subtitle_parse_dedupe` timings for future profiling, but this phase intentionally avoided refactoring that path because the measured hotspots above were enough for a low-risk pass.

## Validation

- `uv run pytest tests/unit/infrastructure/rendering/test_markdown_renderer.py tests/unit/infrastructure/telegram/test_bot_adapter_commands.py tests/unit/application/services/test_rename_speakers.py tests/unit/performance/test_benchmark_smoke.py`
- `uv run python scripts/perf/benchmark_pipeline_fake.py --output /tmp/yt-transcriber-benchmark-phase5.json --iterations 7`

## Not included

- No Telegram/YouTube/WhisperX/pyannote end-to-end runtime profiling.
- No broad progress-reporter refactor because the benchmark harness did not justify that risk in this pass.
