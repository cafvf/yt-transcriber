# PLAN-007 Tasks

Version: **1.0.0**
Status: **Approved for execution**

## P07-A — Canonical taxonomy
- **TASK-P07-001:** replace ambiguous audio-track booleans with typed selection semantics and tests.
- **TASK-P07-002:** migrate internal `VideoMetadata` consumers to `MediaMetadata`; retain alias only
  with proven compatibility.
- **TASK-P07-003:** type pipeline language fields with `Language`/`LanguageSource`.
- **TASK-P07-004:** make `processing_fingerprint` canonical; isolate legacy signatures.
- **TASK-P07-005:** converge media-duration and artifact-policy terminology.
- **GATE-P07-A:** taxonomy/conformance + Ruff/mypy focused checks + compatibility ledger.

## P07-B — Error contract and boundaries
- **TASK-P07-006:** add stable error code/category/retryability/safe-message contract.
  Initial codes should cover `youtube.auth_required`, `youtube.video_unavailable`,
  `youtube.no_audio_stream`, `media.duration_exceeded`, `media.language_not_allowed`,
  `transcription.out_of_memory`, `diarization.unavailable`, `operation.cancelled`,
  `delivery.failed`, `internal.invariant_violation`.
- **TASK-P07-007:** normalize/sanitize provider exceptions at deliberate boundaries.
- **TASK-P07-008:** inject existing canonical Markdown writer into rendering.
- **TASK-P07-009:** review remaining governed application I/O exceptions without inventing generic
  abstractions.
- **GATE-P07-B:** hexagonal, port, composition, error and sanitization conformance.

## P07-C — Configuration, packaging and distribution
- **TASK-P07-010:** canonical private production env-file policy outside repository.
- **TASK-P07-011:** credential/config convergence without secret echoing.
- **TASK-P07-012:** move dev-only tooling such as pre-commit out of runtime dependencies.
- **TASK-P07-013:** health/preflight for yt-dlp-ejs + Deno/supported Node.
- **TASK-P07-014:** `uv build`, clean install, import/CLI/config/package-data/preflight smoke.
- **GATE-P07-C:** production install succeeds without source checkout/dev dependencies.

## P07-D — Documentation and onboarding
- **TASK-P07-015:** rewrite README as product front door: product, capabilities, limitations,
  prerequisites, install, credential table, private config, start, healthcheck, first transcription,
  systemd, update, backup, troubleshooting, development, deep docs.
- **TASK-P07-016:** reconcile installation/security/runbook/readiness docs; historical engineering evidence remains under `specs/`, not duplicated as obsolete public operator docs.
- **TASK-P07-017:** document user-relevant deprecations/removal policy.
- **GATE-P07-D:** documentation-to-implementation conformance.

## P07-E — Release gate
- **TASK-P07-018:** compile/import, Ruff lint/format, mypy, focused/conformance/integration/full pytest.
- **TASK-P07-019:** secret scanner, gitleaks, pre-commit, private-file inspection. A scanner that
  fails to execute is a failed gate.
- **TASK-P07-020:** build + clean-install distribution gate.
- **TASK-P07-021:** controlled real YouTube smoke when authorized:
  metadata → formats → original-track selection → short acquisition.
- **TASK-P07-022:** systemd/journal/health/status/SQLite operational gate when deployment changed.
- **TASK-P07-023:** archive extraction, expected file list, SHA-256, candidate/base revision, commands,
  exit codes and unexecuted checks.
- **GATE-P07-E:** PASS / PASS WITH RESERVATION / BLOCKED. Type/test/architecture/security/artifact/
  clean-install failures cannot be downgraded to reservations.

<!-- PLAN-007:GATE-A:TASK-STATUS:2026-08-21 -->
## Gate A execution ledger — 2026-08-21

| Task | Status | Canonical outcome |
| --- | --- | --- |
| P07-001 | **DONE** | `AudioTrackSelection` canonical semantics implemented and validated |
| P07-002 | **DONE** | `MediaMetadata` canonical entity implemented and validated |
| P07-003 | **DONE** | typed language values enforced in core/application boundaries |
| P07-004 | **DONE** | `processing_fingerprint` canonicalized; SQL compatibility isolated |
| P07-005 | **DONE** | duration/artifact taxonomy canonicalized; external compatibility isolated |

Gate-level closure evidence is recorded in [`GATE-A-CLOSURE.md`](GATE-A-CLOSURE.md).

<!-- PLAN-007:GATE-B:IMPLEMENTATION:2026-08-22 -->
## Gate B implementation ledger — 2026-08-22

| Task | Implementation |
| --- | --- |
| P07-006 | stable provider-neutral operational error taxonomy and structured records |
| P07-007 | provider exceptions mapped to safe application semantics; raw details confined to sanitized technical context |
| P07-008 | canonical Markdown writer injected into transcription rendering |
| P07-009 | direct application artifact-directory/write ownership removed from pipeline steps; remaining I/O reviewed by the Gate B auditor |

Gate closure is determined only by the cumulative runner and its post-commit reproduction; this ledger does not pre-claim PASS.

<!-- PLAN-007:GATE-B:TASK-CLOSURE:2026-08-22 -->
## Gate B task closure ledger — 2026-08-22

| Task | Status | Canonical outcome |
| --- | --- | --- |
| P07-006 | **DONE** | stable structured provider-neutral operational error contract |
| P07-007 | **DONE** | deliberate exception normalization and sanitized public/operator boundaries |
| P07-008 | **DONE** | canonical Markdown writer owns transcription Markdown persistence |
| P07-009 | **DONE** | governed application I/O converged without speculative generic filesystem abstraction |

Gate-level closure evidence is recorded in [`GATE-B-CLOSURE.md`](GATE-B-CLOSURE.md).

Next task group: **P07-C — Configuration, packaging and distribution (P07-010…014)**.

<!-- PLAN-007:GATE-C1:IMPLEMENTATION:2026-08-22 -->
## Gate C1 implementation ledger — 2026-08-22

| Task | C1 implementation |
| --- | --- |
| P07-010 | production env policy converged with `/etc/yt-transcriber-bot/env`; installed runtime no longer discovers arbitrary CWD `.env` or repository metadata; checkout `.env` remains development-only |
| P07-011 | `ProviderCredentials` retained as single configuration declaration owner; one selected dotenv source feeds settings and credentials while process environment keeps precedence |

C1 is an implementation sub-gate only. It does **not** close GATE-P07-C. P07-012, P07-013 and P07-014 remain open and cumulative Gate A/B/C evidence must pass before Gate C closure.

Detailed C1 review: [`GATE-C-CONFIGURATION-REVIEW.md`](GATE-C-CONFIGURATION-REVIEW.md).

<!-- PLAN-007:GATE-C2:IMPLEMENTATION:2026-08-22 -->
## Gate C2 implementation ledger — 2026-08-22

| Task | C2 implementation |
| --- | --- |
| P07-012 | `pre-commit` moved from production requirements to the dev dependency group; wheel metadata audited for dev-tool leakage |
| P07-013 | YouTube readiness evaluates `yt_dlp`, `yt_dlp_ejs` and Deno >= 2.3.0 or Node >= 22.0.0; health facts include executable versions |

C2 establishes the reusable readiness core. Installed `--preflight` and final clean-install/systemd proof remain P07-014 / C3 work.

Detailed C2 review: [`GATE-C-RUNTIME-READINESS-REVIEW.md`](GATE-C-RUNTIME-READINESS-REVIEW.md).

<!-- PLAN-007:GATE-C3:IMPLEMENTATION:2026-08-22 -->
## Gate C3 implementation ledger — 2026-08-22

| Task | C3 implementation |
| --- | --- |
| P07-014 | installed `yt-transcriber-bot --preflight`; systemd uses installed console script and `/var/lib` state directory; clean Python 3.12 wheel install is executed from unrelated CWD with no dev dependencies |

C3 performs the final distributable-runtime proof. Gate C closure documentation should be reconciled only after the committed post-install reproduction passes.

Detailed C3 proof contract: [`GATE-C-DISTRIBUTION-PROOF.md`](GATE-C-DISTRIBUTION-PROOF.md).

<!-- PLAN-007:GATE-C:TASK-CLOSURE:2026-08-22 -->
## Gate C task closure ledger — 2026-08-22

| Task | Status | Canonical outcome |
| --- | --- | --- |
| P07-010 | **DONE** | private production configuration boundary independent of arbitrary CWD/repository discovery |
| P07-011 | **DONE** | single credential declaration ownership with process-environment precedence and redacted diagnostics |
| P07-012 | **DONE** | dev-only tooling removed from production dependency metadata |
| P07-013 | **DONE** | version-aware yt-dlp/EJS + supported Deno/Node runtime readiness |
| P07-014 | **DONE** | installed console CLI, checkout-independent systemd contract, wheel build and clean Python 3.12 install/preflight proof |

Gate-level closure evidence is recorded in [`GATE-C-CLOSURE.md`](GATE-C-CLOSURE.md).

Next task group: **P07-D — Documentation and onboarding (P07-015…017)**.

<!-- PLAN-007:GATE-D:TASK-CLOSURE:2026-08-23 -->
## Gate D task closure ledger — 2026-08-23

| Task | Status | Canonical outcome |
| --- | --- | --- |
| P07-015 | **DONE** | README is the current product front door and distinguishes installed production from checkout development |
| P07-016 | **DONE** | installation/security/runbook/readiness agree with implementation; engineering history remains in `specs/`, not duplicated as obsolete operator-facing gate reports/patch notes |
| P07-017 | **DONE** | user-facing compatibility, deprecation and removal policy is explicit and current |

Canonical implementation: `7080afc9342f0bd94b0ab74aba3b1c60996c0bc9`.

Gate-level closure evidence is recorded in
[`GATE-D-CLOSURE.md`](GATE-D-CLOSURE.md).

Next and final task group: **P07-E — Release gate (P07-018…P07-023)**.

<!-- PLAN-007:GATE-E:TASK-CLOSURE:2026-08-23 -->
## Gate E task closure ledger — 2026-08-23

| Task | Status | Canonical outcome |
| --- | --- | --- |
| P07-018 | **DONE** | cumulative syntax/import/lint/format/type/architecture/test evidence passed for release candidate `2f2b99840830a555c29afcd56082b259dc971df4` |
| P07-019 | **DONE** | secret scanner, Gitleaks, private-artifact inspection and pre-commit passed |
| P07-020 | **DONE** | build, wheel inspection, clean installed origin/CLI and checkout-independent offline/read-only preflight passed |
| P07-021 | **DONE WITH RESERVATION** | real YouTube metadata/formats/acquisition passed; selected fixture did not expose identifiable multi-audio original-track candidates |
| P07-022 | **DONE WITH RESERVATION** | production migration/systemd/SQLite/status passed; LM Studio was intentionally offline during manual healthcheck |
| P07-023 | **DONE** | exact candidate/base, package/hashes/evidence, clean-tree and local/remote guards recorded |

Gate-level and PLAN-level closure evidence is recorded in
[`GATE-E-CLOSURE.md`](GATE-E-CLOSURE.md).

Final PLAN-007 decision: **CLOSED / PASS WITH RESERVATION**.
