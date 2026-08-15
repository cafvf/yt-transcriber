# Task Integration and Handoff Map

Version: **1.0.0**
Status: **Approved / Frozen**
Date: **2026-08-15**

## Purpose

This document prevents the task package from turning cross-cutting requirements into duplicate implementations. A concept may pass through several plans, but each stage has a distinct responsibility and later tasks consume earlier contracts instead of recreating them.

## Cross-plan ownership chains

| Concept | PLAN-001 | PLAN-002 | PLAN-003 | PLAN-004 | PLAN-005 | PLAN-006 |
|---|---|---|---|---|---|---|
| Authorization / privacy / disclosure | audience, privacy, sanitization guardrails | preserve private persisted semantics | credential/external-service boundaries | workflows consume guards | operator acceptance | docs/evidence only |
| Job lifecycle / recovery | security preconditions | state graph + durable request/source truth | provider/runtime seams only | execution/queue/recovery ownership + reliability assurance | status/cancel/delivery acceptance | real startup/restart rehearsal |
| Canonical transcript | private-data classification | structured+Markdown truth, explicit linkage, completion integrity | canonical store/renderer ports | derived/index collaborations | rename/summary/export/video/history acceptance | backup/recovery verification |
| Search | privacy/sanitization guardrails | canonical data only | store/port seams | index data + persistence/index/search split + search workflow | textual search acceptance | evidence/docs only |
| Summary / external text generation | untrusted input + disclosure controls | canonical/provenance truth | external capability + endpoint/credential boundary | application summary policy | summary acceptance | runtime/docs evidence |
| Operational policy | path/privacy/sanitization guards | artifact/reference truth | narrow capability seams | health/error/retention/cache policy vs I/O split | diagnostic/cache acceptance | host/service/recovery evidence |
| Compatibility | characterize current interface | persisted/public compatibility assurance | internal seam migration preserves external names | reversible workflow migration | functional regression | final current-doc/runtime conformance |

## Deliberate non-merges

The following remain separate throughout task execution:

- history browsing/retrieval versus textual search;
- canonical transcript storage versus lifecycle persistence;
- indexing transformation versus search query semantics;
- transcript export versus YouTube MP4 derivative;
- canonical transcript versus derived summary/export/video artifacts;
- application policy versus filesystem/network/subprocess mechanisms;
- processing fingerprint identity versus actual run provenance;
- provider-secret lifecycle versus provider-secret architectural boundary.

A task may reuse the same data or adapter, but it SHALL NOT merge these semantic responsibilities merely to reduce file count.

## Cross-cutting closure rules

### REQ-ARC-001

`TASK-P03-001` creates the architecture-test ratchet. Specific PLAN-003 tasks eliminate known violations. `TASK-P03-012` is the only `REQ-ARC-001` closure owner and removes the temporary exception manifest when the frozen requirement is actually true.

### REQ-ARC-012

`TASK-P03-003` establishes the port convention/inventory. Dedicated ASR, diarization, canonical-store and composition tasks create the real capabilities. `TASK-P03-011` removes obsolete generic `FileStorage`. After `REQ-ARC-001` closes in `TASK-P03-012`, `TASK-P03-013` is the only `REQ-ARC-012` closure owner.

### REQ-ARC-002

PLAN-004 moves workflows one at a time:

1. admission/dedup/reprocess;
2. execution/queue/cancel/recovery;
3. completed-history retrieval;
4. persistence/index/search separation and search orchestration;
5. edit/export/video orchestration;
6. summary policy/orchestration;
7. operational command orchestration.

`TASK-P04-014` closes the thin-Telegram requirement only after these migrations. It does not reimplement them.

## Failure-routing rule

When a closure, assurance or gate task finds a failed criterion:

1. identify the task that owns the missing behavior;
2. reopen that owner;
3. apply Red → Green → Refactor there;
4. rerun dependent evidence;
5. return to the closure/gate.

The closure/gate task MUST NOT add an alternate implementation just to make its own check pass.

## Operational evidence reuse

A real rehearsal may satisfy more than one frozen evidence obligation when it exercises the same contract on the same closure revision/environment.

| Evidence record | Producing task | Reused by |
|---|---|---|
| environment-gated integration-test execution/classification | `TASK-P06-001` | `TASK-P06-010`, `TASK-P06-011` |
| startup/restart reconciliation rehearsal | `TASK-P06-003` | `TASK-P06-010`, `TASK-P06-011` |
| systemd lifecycle + secret-file permission rehearsal | `TASK-P06-005` | `TASK-P06-010`, `TASK-P06-011` |
| real backup/restore rehearsal | `TASK-P06-006` | `TASK-P06-002`, `TASK-P06-010`, `TASK-P06-011` |
| upgrade/rollback rehearsal | `TASK-P06-007` | `TASK-P06-010`, `TASK-P06-011` |
| delivery-failed/manual recovery rehearsal | `TASK-P06-008` | `TASK-P06-010`, `TASK-P06-011` |
| command/help/current-doc conformance | `TASK-P06-009` | `TASK-P06-011` |

Evidence is rerun only when the prior record is incomplete, failed, belongs to a materially different environment, or a later change invalidates it.
