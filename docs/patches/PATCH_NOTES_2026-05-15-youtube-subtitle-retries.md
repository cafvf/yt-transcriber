# Patch Notes — 2026-05-15 — YouTube subtitle retries

## Goal

Harden direct YouTube subtitle fetching against transient failures such as HTTP 429, while preserving the existing fallback to the audio pipeline after bounded retry exhaustion.

## What changed

- `YtDlpDownloader.fetch_subtitle(...)` now retries transient subtitle fetch failures before giving up.
- Retry policy is explicit and bounded:
  - max attempts: 3
  - backoff: 0.5s, then 1.0s
- Transient classification currently includes:
  - `HTTPError` with status `408, 425, 429, 500, 502, 503, 504`
  - `URLError`
  - `TimeoutError`
  - connection / OS-level transient failures
- Non-transient failures (for example `HTTP 404`) still fail immediately without retry.
- Regression tests cover:
  - 429 retry then success
  - transient failure exhaustion
  - no retry for non-transient HTTP errors

## Validation

- Unit tests for the downloader and real subtitle fetcher pass.
- Full repo test/lint/security gates pass.
- Fresh live validation artifact:
  - `.omx/benchmarks/subtitle-retry-validation-20260515T092800Z.json`

## Live result

The live environment still receives `HTTP 429 Too Many Requests` from YouTube subtitle fetches for `dQw4w9WgXcQ`, but the artifact confirms that the downloader now performs 3 bounded attempts before falling back.

## Follow-up

If 429 remains common in production, the next step is downloader-level provider hardening (e.g. alternate fetch strategy or cookie/runtime guidance), not reverting the bounded retry behavior.
