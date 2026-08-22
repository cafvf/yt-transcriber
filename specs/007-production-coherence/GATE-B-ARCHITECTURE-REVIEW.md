# PLAN-007 — Gate B Architecture Review

Status: **CLOSED / PASS** — cumulative pre-commit and post-commit evidence completed on `2bc2041`.

## Error boundary

Gate B introduces one application-owned operational error vocabulary with stable `code`, `category`,
`retryable`, `safe_message`, and optional sanitized `technical_context`. Provider exception classes remain
adapter/application implementation details and are not persisted as behavioral API. Legacy JSONL records
are translated only by the filesystem store reader under COMPAT-005.

The top-level transcription use case retains distinct cancellation, deliberate rejection, and unexpected
failure branches. Each branch projects a safe message to `Job.error_message`/`failure_reason` while the
structured result retains the stable operational error. Telegram audit fields use the stable code/category
rather than provider exception names.

## Markdown ownership

`RenderMarkdownStep` renders structured canonical evidence but does not create directories, reserve names,
or write/replace/unlink Markdown files. It calls the existing `CanonicalMarkdownWriter` capability.
`FilesystemCanonicalMarkdownWriter` owns atomic replace and no-clobber creation. The structured transcript
snapshot is persisted first; if Markdown persistence fails, snapshot rollback is best-effort and the primary
Markdown failure is re-raised unchanged.

## Cancellation and fallback

YouTube subtitle listing/download remain best-effort optimization paths. Their broad fallback catches are
deliberate, but `OperationCanceledError` is re-raised before fallback. Provider text is not interpolated into
pipeline diagnostics.

## Reviewed application I/O inventory

The diagnostic inventory over-counted pure method names such as `dataclasses.replace`, `str.replace`,
search-index `replace`, and rename-service calls as filesystem I/O. Those are not I/O boundaries.

The remaining real pre-existing application-side filesystem observations are deliberately not wrapped in a
generic filesystem abstraction:

- `application/config.py` reads a candidate `pyproject.toml` only to identify a project root. This is
  configuration discovery and is scheduled for Gate C packaging/configuration convergence.
- `UseTelegramAudioStep` observes whether the already-downloaded private source path exists before ASR. The
  transport/download itself remains adapter-owned; introducing a generic filesystem port solely for this
  guard would add abstraction without a demonstrated application capability.

Gate B removes the direct directory creation in YouTube download/conversion steps because those adapters
already own destination writes. No new direct application filesystem dependency is introduced.

## Reviewed broad catches

- `PipelineRunner.run`: audit-and-rethrow containment; does not hide failure.
- `TryYouTubeSubtitlesStep.execute`: deliberate optional-provider fallback; cancellation bypasses it.
- `RenderMarkdownStep.execute`: rollback guard; re-raises the original persistence failure.
- sanitization helpers: defensive redaction boundary.
- `TranscriptSummaryService.summarize`: known generation errors are re-raised first; unexpected errors are
  wrapped as application `SummaryError`.
- `TranscribeVideoUseCase.execute`: approved top-level application containment.
- admission rollback, completion observer isolation, and queue worker containment preserve their existing
  failure/isolation responsibilities.

The Gate B architecture auditor blocks application→infrastructure imports, stale raw error contracts,
Markdown direct persistence, missing writer injection, and any `TranscribeVideoDependencies(...)` consumer
in `src/tests/scripts` that omits `markdown_writer`.

<!-- PLAN-007:GATE-B:ARCH-REVIEW:CLOSURE:2026-08-22 -->
## Closure note

The cumulative residual runner completed with **51 PASS, 0 FAIL**. Gate A and Gate B architecture audits, Ruff, mypy, focused behavior tests, complete conformance, explicit SQLite compatibility integration, the configured pytest suite, Gitleaks and pre-commit all passed before commit and were reproduced on committed bytes before publication.

Exact closure and publication evidence is recorded in [`GATE-B-CLOSURE.md`](GATE-B-CLOSURE.md).
