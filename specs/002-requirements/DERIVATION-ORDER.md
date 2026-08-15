# Atomic Requirement Derivation Order

Version: **1.0.0**
Status: Approved derivation-order basis; atomic requirements are authored in `../003-atomic-requirements/`.

## Gate 0 — Evidence and vocabulary

Before the first atomic requirement:

- use `EVIDENCE-INVENTORY.md` as the classified inventory required by `QUALITY.md`;
- use frozen `001-use-cases` for behavioral scope;
- use current code/tests only as brownfield evidence, never as automatic normative intent.

## Recommended derivation order

1. **Foundational SEC invariants** — authorization, secret/privacy classification, untrusted-input handling, filesystem safety, sanitization, supply-chain trust.
2. **DOMAIN foundations** — MediaSource, Job lifecycle, transcript/artifact/provenance semantics.
3. **Core DATA truth** — Job, media/staging, transcript snapshot, Markdown, ops logs, cache, compatibility; then canonical `DATA-INTEGRITY`.
4. **Core ARCH boundaries** — dependency direction, ports, application ownership and configuration boundary.
5. **Specialized ARCH boundaries** — transport, execution/queue, runtime, ASR, diarization, transcript, persistence/search, text generation, operational I/O, composition; co-derive `SEC-BOUNDARY`/`SEC-EXTERNAL` details where needed.
6. **Remaining DATA contracts** — derivatives, search, retention, backup with integrity constraints already stable.
7. **NFR constraints** — reliability, resource bounds, observability, portability, maintainability, compatibility.
8. **Core FUNC** — source, processing, delivery, control.
9. **Transcript-consuming FUNC** — history, search, rename, summary, export, video derivative.
10. **Diagnostic/maintenance FUNC** — health, last error, cache.
11. **OPS** — startup, retention, service lifecycle, backup/restore, upgrade/rollback, manual recovery, evidence.
12. **FUNC-INTERFACE / conformance** — final command/help/docs/alias consistency against the stabilized contract.

## Why SEC is not a single first-and-done phase

Security constrains everything from the start, but some atomic boundary requirements need the corresponding architecture vocabulary. For example, the invariant “provider credentials do not become application business payload” is foundational, while its exact acceptance contract for diarization is derived together with `ARCH-DIAR` and `ARCH-COMPOSITION`.

## Why DATA-INTEGRITY precedes workflow refactors

Current code can write Markdown, fail to persist the canonical structured snapshot, and still continue toward delivery. Current retention can also remove an artifact while durable Job paths remain stale. Atomic lifecycle/workflow requirements therefore need canonical-data integrity semantics before large responsibility moves are planned.

This order is for specification derivation, not a one-to-one implementation sequence.
