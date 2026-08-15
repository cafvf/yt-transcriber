# PLAN-005 — Functional and non-functional reconnection

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **003-atomic-requirements v1.0.0**
Prerequisite plans: **PLAN-004** *(earlier gates inherited transitively)*
Approved: **2026-08-15**

## Goal

Reconnect every frozen operator workflow to the repaired architecture and close bounded-resource, privacy-aware observability and async-responsiveness behavior before host/deployment closure.

This plan is the **application/product acceptance layer**. It verifies that earlier structural changes preserve the frozen UCs without reimplementing the same underlying domain/data/port obligations.

## Primary requirement scope

- `REQ-FUNC-001` — Submit supported media and explicitly reprocess as a new Job
- `REQ-FUNC-002` — Process media through truthful subtitle, ASR and diarization paths
- `REQ-FUNC-003` — Primary and derivative delivery outcomes
- `REQ-FUNC-004` — Observe queue/status and cancel scoped work
- `REQ-FUNC-005` — Browse and retrieve completed history
- `REQ-FUNC-006` — Rename and merge speakers from canonical evidence
- `REQ-FUNC-007` — Generate a derived summary from canonical evidence
- `REQ-FUNC-008` — Generate transcript exports from canonical evidence
- `REQ-FUNC-009` — Inspect runtime health safely
- `REQ-FUNC-010` — Inspect the latest relevant operational error
- `REQ-FUNC-011` — Safely clear reconstructible cache
- `REQ-FUNC-013` — Text-search completed history
- `REQ-FUNC-014` — Generate YouTube MP4 with selectable subtitles
- `REQ-NFR-002` — Bounded resource consumption and external waits
- `REQ-NFR-003` — Actionable privacy-aware observability
- `REQ-NFR-007` — Non-blocking Telegram transport responsiveness

## Implementation approach

1. Re-run submission/dedup/reprocess, subtitle/ASR/diarization, delivery, queue/cancel, history, search, rename, summary, export, video, health, last-error and cache workflows against the new application seams.
2. Keep history retrieval and textual search as separate capabilities and acceptance suites.
3. Keep transcript export and YouTube video derivative as separate capabilities/failure models.
4. Verify successful summary and speaker-alias changes explicitly refresh textual-search state without changing canonical transcript authority.
5. Enforce finite queue/media/duration/token/log/cache/artifact/external-wait limits and preserve sequential expensive processing.
6. Ensure long synchronous work initiated by Telegram handlers runs off the event loop or through asynchronous capabilities.
7. Verify diagnostics remain actionable, sanitized and private after architectural decomposition.
8. Exercise application-level portions of `SS-001` startup reconciliation and `SS-002` retention sufficiently to make host rehearsal in PLAN-006 a verification step rather than a first discovery of semantics.

## Ownership boundary and handoff

PLAN-005 owns **frozen functional/NFR acceptance**, not host/service evidence. It consumes earlier domain/data/architecture implementations and does not create alternate implementations merely to pass acceptance tests.

It hands off to PLAN-006:

- environment-specific integration evidence;
- real service/startup/restart/retention/backup/rollback/recovery rehearsals;
- command/help/manual/current-documentation convergence and final readiness record.

## Migration and compatibility constraints

- Do not use functional reconnection as an excuse to add semantic search, translation, selective redo, checkpoint resume or new media sources.
- Do not relax canonical evidence requirements to make a derived workflow pass.
- Do not mutate completed Jobs when a derived send/generation fails.
- Do not duplicate application policy inside Telegram test fixtures as a long-term workaround.

## Exit gate

- All 12 frozen operator UCs have executable acceptance evidence.
- Application-level `SS-001`/`SS-002` behavior is covered; host evidence remains explicitly deferred to PLAN-006.
- All current command behaviors/aliases remain compatible except approved private-chat hardening.
- Resource-limit and event-loop responsiveness tests pass.
- Primary versus derived delivery lifecycle tests pass.
- Current environment-gated integration contracts retain or receive explicit equivalent evidence and are classified for PLAN-006 execution.

## Not tasks

The numbered approach above defines migration order and design constraints, not a task checklist. Concrete files, red tests, implementation increments, commits and task ownership are defined in `../005-tasks/`.
