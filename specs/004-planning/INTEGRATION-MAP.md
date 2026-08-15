# Plan Integration and Handoff Map

Version: **1.0.0**
Status: **Approved / Frozen**

This document prevents a concept that legitimately spans several plans from becoming several competing implementations.

| Concept | PLAN-001 | PLAN-002 | PLAN-003 | PLAN-004 | PLAN-005 | PLAN-006 |
|---|---|---|---|---|---|---|
| Authorization / Telegram audience | Define/test security policy | Preserve compatible request data | Composition/edge seams consume policy | Application workflows respect policy | UC acceptance | Host/current-doc evidence |
| Secrets | Lifecycle/least privilege/scanning | Exclude from provenance/persisted truth | Enforce edge-only credentials | Consume secret-free ports | Leakage regression | Host permissions/provisioning evidence |
| Private data / sanitization | Classify + one sanitizer policy | Data classifications/relationships | External disclosure seams | Logs/ops/summary consumers use policy | End-to-end privacy observability | Sanitized rehearsal evidence |
| Media/source truth | Characterize untrusted input | Own source identity, language/duration truth, media lifecycle | Expose neutral ports/runtime seams | Orchestrate workflows | UC acceptance | Runtime/operator docs |
| Job lifecycle | Characterize sensitive surfaces | Own legal graph + durable compatible state | Keep ports/domain boundaries clean | Own queue/cancel/recovery/delivery coordination | Functional acceptance | Startup/restart rehearsal |
| Canonical transcript | Protect as private data | Own canonical structured+Markdown semantics/linkage/atomicity | Define store/renderer capabilities | Consumers/derived workflows use capabilities | UC acceptance | Backup/restore integrity |
| Retention | Safe filesystem guardrails | Classify completed/volatile/canonical data | Provide narrow I/O seams | Own retention policy collaboration | Resource/application acceptance | Automatic retention rehearsal/evidence |
| Search/index | Private-data rules | Canonical/derived authority inputs | Persistence/search capability boundaries | Split indexing/search and refresh lifecycle | Search/rename/summary acceptance | Current docs/readiness |
| Summary/text generation | Input/private-data policy | Canonical/provenance truth | Trusted external endpoint, text-generation/tokenizer seams | Own chunk/prompt/reduction policy | Summary acceptance/resources | Runtime/docs evidence |
| Configuration | Secret/trust policy | Fingerprint + compatibility expectations | Truthful config taxonomy/composition ownership | Consumers depend on configured capabilities | Behavior acceptance | Install/runbook/current-doc convergence |
| Filesystem/cache/logs | Containment/permissions/sanitization primitives | Data ownership/retention classifications | Purpose-specific ports | Operational/cache/log policies | Functional/resource acceptance | Host permissions/evidence |
| Telegram adapter | Audience boundary characterization | Remove transport data from pure Job | Provider/composition edge only | Thin transport + move portable workflows | Command/UC responsiveness acceptance | Help/manual/interface conformance |
| Documentation | Specs/gate records only | Specs/gate records only | Specs/gate records only | Specs/gate records only | Acceptance evidence only | Converge current README/manual/runbook/roadmap/readiness; preserve history |

## Handoff rule

A later plan may **consume, adapt or verify** an earlier plan's output, but must not create a second source of truth for the same policy. If an earlier contract proves insufficient, the owning frozen REQ/plan must be amended through governance rather than worked around locally.

## Three-stage concepts

Some concerns intentionally have three layers:

- **Retention:** PLAN-002 classifies data → PLAN-004 owns application policy/I/O collaboration → PLAN-006 proves automatic host behavior.
- **Recovery:** PLAN-002 defines state/data truth → PLAN-004 owns application reconciliation coordination → PLAN-006 rehearses real restart/manual recovery.
- **Canonical evidence:** PLAN-002 defines persistence truth → PLAN-003 defines application capabilities → PLAN-004 migrates consumers → PLAN-005 proves operator workflows → PLAN-006 proves backup/restore.
- **Security:** PLAN-001 defines guardrails → PLAN-003 enforces provider/external seams → PLAN-004 consumes them → PLAN-005 tests observable behavior → PLAN-006 proves host controls.

These are integrations, not duplicate ownership.
