# Patch notes — adaptive summary timeouts

Date: 2026-05-04

## Context

Long `/summary` executions on a local LM Studio backend can time out even when
the prompt fits the model context window. The runtime cost is driven not only by
context size, but also by prompt ingestion time and output generation time.

## Changes

- Added per-request `max_tokens` support to `ChatCompletionRequest`.
- Added `ChatCompletionTimeoutError` to distinguish timeout failures from other
  OpenAI-compatible API errors.
- Added separate output budgets:
  - `SUMMARY_PARTIAL_MAX_TOKENS` for map-step summaries.
  - `SUMMARY_FINAL_MAX_TOKENS` for single-pass summaries and final synthesis.
- Increased conservative defaults for local LM Studio use:
  - `SUMMARY_MAX_INPUT_TOKENS=6000`.
  - `SUMMARY_MAX_CHARS_PER_CHUNK=18000`.
  - `SUMMARY_CHARS_PER_TOKEN=2.5`.
  - `SUMMARY_TIMEOUT_S=600`.
- Added `SUMMARY_TIMEOUT_SPLIT_RETRIES` to retry timed-out summary chunks by
  subdividing them into smaller chunks.
- Added adaptive splitting for single-pass timeout fallback and map-step timeout
  fallback.
- Added adaptive grouped synthesis when the final synthesis times out.
- Added Telegram progress text for chunk/synthesis subdivision events.

## Tests

Added/updated unit tests for:

- per-request `max_tokens` override in the OpenAI-compatible client;
- specific timeout error reporting;
- partial/final token budgets in the summarizer;
- final token budget in single-pass summary;
- adaptive split after single-pass timeout;
- propagation when adaptive split is disabled;
- summary config defaults as sensible ranges rather than brittle exact values.

Validated with:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest \
  tests/unit/infrastructure/summarization/test_openai_compatible_client.py \
  tests/unit/infrastructure/summarization/test_transcript_summarizer.py \
  tests/unit/application/test_config.py \
  -q
```

Result in the patch environment: `56 passed`.

The Telegram adapter test could not be collected in the patch environment
because `slugify` was not installed there. Run the full suite with `uv run
pytest` in the project environment.
