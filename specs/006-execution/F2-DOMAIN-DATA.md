# F2 — Domain and data truth

Status: **Verified / Closed**
Date: **2026-08-15**
Base revision: `246931f747d7077e3271687c68219ff6df54ede9`
Task scope: `TASK-P02-001` through `TASK-P02-013`
Predecessor: F1 / PLAN-001 **Verified / Closed**

## Purpose

F2 makes the existing product truthful before architectural extraction. It
changes domain semantics and persistence compatibility without introducing a new
product capability. New ASR backends, expanded language support, translation,
semantic search, Obsidian integration, statistics, and checkpoint resume remain
out of scope.

## Implemented task mapping

### TASK-P02-001 — Source-neutral media identity

- `MediaSource` remains the canonical source-neutral identity.
- YouTube identity uses canonical URL/video id semantics.
- Telegram media uses its private transport reference and never fabricates a
  YouTube `video_id`.
- Acquisition/staging locators are application request context, not media
  identity.

### TASK-P02-002 — Explicit Job state machine

- New semantic state is `acquiring`.
- The legal transition graph is enforced in `Job.transition_to`.
- Same-state assignment is idempotent and does not update timestamp/error.
- Persisted legacy literal `downloading` decodes as `acquiring`.
- Terminal states cannot reopen.

### TASK-P02-003 — Truthful transcript and language facts

- Canonical transcript segments require positive spans.
- Language and confidence may be unknown rather than fabricated.
- Requested/forced language is stored separately from observed ASR language.
- Forced language does not inherit detector confidence.
- Unsupported observed ASR language without explicit request fails explicitly;
  it is no longer silently mapped to the first allowed language.
- YouTube metadata no longer falls back to English when language is unknown.

### TASK-P02-004 — Artifact taxonomy

- Added explicit canonical/derived/volatile/log/cache artifact classes.
- Structured transcript snapshot and Markdown are both canonical evidence with
  distinct machine/human roles.

### TASK-P02-005 — Processing fingerprint and actual provenance

- `application.services.config_signature` is the single fingerprint owner.
- Fingerprint is versioned and includes output-significant source policy, ASR,
  audio, language constraint, diarization/normalization/schema policy.
- Credentials, local paths, queue/retention/log/progress settings are excluded.
- Snapshot v2 records actual processing provenance separately from request-time
  fingerprint, including ASR model/runtime/fallback and language source when
  known.

### TASK-P02-006 — Volatile media lifecycle and truthful duration

- Unknown/malformed YouTube duration remains `None`, not zero.
- Pipeline rejects media whose duration cannot be established before expensive
  ASR/diarization.
- Telegram audio requires a positive known/probed duration before processing.
- Volatile acquisition/converted/log artifacts remain separate from canonical
  transcript evidence.

### TASK-P02-007 — Job state and request/delivery context

- Telegram `chat_id` is no longer a `Job` domain field.
- Acquisition/staging locator is also kept in `JobRequestContext` rather than the
  domain aggregate.
- Physical SQLite `requested_chat_id` and `source_url` columns remain readable
  for compatibility and back the application request context.

### TASK-P02-008 — Canonical structured transcript and explicit linkage

- Snapshot schema v2 is the machine-canonical transcript evidence.
- Markdown remains the human-canonical representation.
- `Job.canonical_transcript_ref` explicitly links a job to its structured
  snapshot. Legacy SQLite rows are backfilled once from the historical Markdown
  naming convention during migration; runtime structured consumers no longer
  reconstruct a missing reference from `md_path`.
- Snapshot persistence is no longer best-effort during successful rendering.

### TASK-P02-009 — Backward-compatible migration

- Existing SQLite databases gain `canonical_transcript_ref` non-destructively;
  legacy rows with known Markdown paths are explicitly backfilled during migration.
- Existing context columns remain physical compatibility columns.
- Legacy persisted `downloading` remains readable.
- Snapshot v1 remains readable with provenance/language-source facts marked
  unknown when absent.
- New snapshots write schema v2.

### TASK-P02-010 — Retention preserves canonical evidence

- Retention acts only on explicit volatile/log classes.
- Structured snapshot and Markdown are never retention candidates.
- Stale volatile references are reconciled after cleanup/refusal while canonical
  references remain intact.

### TASK-P02-011 — Completion consistency and artifact truth

- Structured snapshot is persisted before Markdown success is advertised.
- Markdown is written atomically.
- Markdown failure rolls back the just-written snapshot best-effort.
- Canonical job references are set only after both canonical representations are
  successfully persisted.
- Use-case success requires explicit canonical structured linkage.

### TASK-P02-012 — Compatibility assurance

- Existing command/environment compatibility remains under F0 conformance.
- Persisted state/snapshot compatibility has dedicated F2 regression coverage.
- Internal compatibility names (`VideoMetadata`, `compute_config_signature`,
  `transcription_signature`) delegate to the new canonical semantics rather than
  maintaining duplicate mechanisms.

### TASK-P02-013 — PLAN-002 exit gate

The PLAN-002 exit gate is **satisfied**.

Local operator evidence on 2026-08-15 confirmed that the final applied F2 tree is
green across formatting, unit/conformance tests, SQLite/integration tests,
typing, compilation, pre-commit, and security scanning.

## Closure evidence

### Targeted F2 regression evidence

After compatibility corrections found during the first full-suite pass:

```text
7 focused regressions passed
2 zero-duration domain-contract tests passed
368 F2-targeted tests passed
3 targeted tests deselected by default markers
```

After final typing corrections:

```text
76 affected tests passed
3 affected integration tests deselected by default markers
mypy: Success — no issues found in 105 source files
```

### Default test suite

```text
804 tests collected
757 selected by the default suite
47 integration tests deselected by the default marker policy
757 passed
```

No default-suite regression remained at closure.

### Integration inventory and execution

The integration inventory increased intentionally from the F1 baseline of 46 to
**47** because F2 added one SQLite migration regression for explicit canonical
snapshot-reference backfill.

```text
47 / 804 tests classified as integration
47 integration tests passed
757 tests deselected during the integration-only run
```

No previously classified integration test disappeared silently.

### Coverage

Two coverage views were recorded because the repository default pytest policy
excludes integration tests.

Default-suite branch-aware coverage remained:

```text
79%
757 passed
47 integration tests deselected
```

The more representative combined measurement executed default and integration
tests in one coverage process:

```text
804 passed
5954 statements covered
1011 statements missing
1420 branches covered
574 branches missing
TOTAL COVERAGE: 82.31%
```

The combined measurement also confirmed that low default-only coverage in the
SQLite repository was a measurement artifact rather than an untested persistence
surface:

```text
job_repository.py: 92.58% combined coverage
```

F2 therefore closes with **82.31% combined branch-aware coverage** as the current
quality baseline.

No rigid `coverage fail_under` threshold is introduced in F2. Coverage will be
raised progressively in subsequent phases, with the F2 combined result serving
as the reference point. Future phases should avoid unexplained regression and
prefer adding meaningful decision/invariant coverage over tests written only to
inflate the percentage.

### Static and security gates

```text
Ruff check --fix: green
Ruff check: green
Ruff format --check: green
205 files formatted/checked

mypy:
Success — no issues found in 105 source files

compileall:
green

pre-commit:
secret/token guard — Passed
Gitleaks complementary hook — Passed

project secret scanner:
no obvious secret found

Gitleaks:
31 commits scanned
~2.74 MB scanned
no leaks found

git diff --check:
green
```

## Closure decision

`TASK-P02-001` through `TASK-P02-013` are complete and PLAN-002/F2 is
**Verified / Closed**.

F2 establishes a truthful domain/data foundation without authorizing future
product features. The approved next execution phase is **F3 — hexagonal
boundaries/provider seams**. F3 may proceed only within its frozen task scope;
new ASR backends, expanded multilingual capability, translation, semantic
search, Obsidian integration, statistics, and checkpoint resume remain frozen.
