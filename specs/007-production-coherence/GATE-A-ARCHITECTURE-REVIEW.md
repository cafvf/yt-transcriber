# PLAN-007 Gate A — Architecture Review

## Scope

This review records the cumulative closure criteria for **GATE-P07-A — Truthful Canonical Semantics** after A1 and the brownfield convergence of A2+A3+A4+A5.

## Canonical contracts

- **P07-001 — AudioTrackSelection:** `ORIGINAL`, `DEFAULT`, `UNKNOWN`; alternative-track existence is metadata, never an `AUTO_DUB` success state.
- **P07-002 — MediaMetadata:** `MediaMetadata` is canonical; `VideoMetadata` is not an internal compatibility surface.
- **P07-003 — typed language:** domain/application use `Language` and `LanguageSource`; raw strings are converted only at external/infrastructure or persisted boundaries.
- **P07-004 — processing fingerprint:** `processing_fingerprint` is canonical in domain/application. Physical SQL `config_signature` is isolated compatibility only.
- **P07-005 — duration/artifact taxonomy:** `max_media_duration_min` is canonical internally and `MAX_MEDIA_DURATION_MIN` is the canonical environment name. `MAX_VIDEO_DURATION_MIN` remains only as documented external compatibility. Behavioral `artifact_policy` is removed from domain/application; a physical SQL column may remain isolated for compatibility.

## Permitted compatibility surfaces

- **COMPAT-001:** persisted Job status literal `downloading` maps to `ACQUIRING`.
- **COMPAT-002:** legacy snapshot/schema readers remain boundary-only compatibility.
- **COMPAT-003:** physical SQL representations such as `config_signature` and `artifact_policy` may remain isolated in persistence.
- **COMPAT-004:** external `MAX_VIDEO_DURATION_MIN` aliases `MAX_MEDIA_DURATION_MIN`, with the canonical environment variable taking precedence when both are present.

Compatibility requires a concrete need, documented legacy surface, automated test, boundary isolation, canonical use by new code, and a future removal condition/window.

## Architecture invariants

- Domain must not depend on application or infrastructure.
- Application must not depend on infrastructure.
- Tests, scripts, and conformance code are real API consumers.
- Bare rule strings, documentation, negative fixtures, and absence assertions are not API consumption by themselves; semantic/AST context is required.
- `**kwargs` mappings are indirect API consumers and their producers must use canonical keys.
- SQL physical legacy names must map explicitly to/from canonical domain names.

## Error-preservation invariants

The cumulative Gate A validation must preserve distinct rejection, failure, and cancellation semantics for YouTube acquisition, pipeline conversion/duration/language/cancellation/canonical-evidence paths, ASR/OOM/unsupported observed language, diarization, persistence/recovery, and observability/sanitization.

A job must never become `COMPLETED` without both the final Markdown evidence required by the workflow and a valid `canonical_transcript_ref` where that evidence is required.

## Validation policy

Diagnostics must execute every safely independent check and accumulate all findings before returning a failure code. Dependent checks may be `SKIPPED` with an explicit reason. Staging and commit are forbidden if any mandatory check fails or is unavailable.

The repository architecture auditor is `scripts/quality/gate_a_architecture_rules.py`, and its conformance test is `tests/conformance/test_gate_a_architecture_contract.py`.

## Gate A static-analysis scope

The blocking mypy scope for Gate A is the production package (`src`) plus the permanent Gate A architecture auditor (`scripts/quality/gate_a_architecture_rules.py`). A broader strict-mypy inventory over historical tests and operational scripts is collected as non-gating debt evidence because that wider surface had no clean pre-Gate baseline. This does not weaken the typed-boundary AST audit, focused/conformance tests, full pytest, or the requirement that production code and installed Gate A tooling are type-clean.

<!-- PLAN-007:GATE-A:ARCH-CLOSURE:2026-08-21 -->
## Final architecture closure — 2026-08-21

The canonical taxonomy described in this review is implemented in `cd5f71d` and reproduced cleanly in post-commit validation. The permanent architecture contract, typed-boundary checks, direct-call and `**kwargs` consumer audits, stale-expectation audit, and layer-dependency audit all passed in the final cumulative run.

Gate decision: **GATE-P07-A CLOSED / PASS**. See [`GATE-A-CLOSURE.md`](GATE-A-CLOSURE.md) for the complete evidence ledger.
