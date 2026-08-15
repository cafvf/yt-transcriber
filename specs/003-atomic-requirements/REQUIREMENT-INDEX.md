# Atomic Requirement Index

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **002-requirements v1.0.0**

Atomic requirements: **66**
Requirement-family coverage: **66/66**

The final count is not intentionally one-to-one with the 66 taxonomy families. Some inseparable family pairs remain consolidated (for example canonical structured transcript + canonical Markdown), while some broad families require more than one atomic obligation (for example diagnostics and resource behavior).

## A — Security, domain and data truth

| ID | Title | Families |
|---|---|---|
| [REQ-SEC-001](REQ-SEC-001.md) | Authorized operator and approved Telegram audience | SEC-AUTH |
| [REQ-SEC-002](REQ-SEC-002.md) | Provider-secret storage, privilege and incident lifecycle | SEC-SECRETS |
| [REQ-SEC-003](REQ-SEC-003.md) | Private-data classification and minimization | SEC-PRIVACY |
| [REQ-SEC-004](REQ-SEC-004.md) | Centralized sanitization of disclosure paths | SEC-SANITIZE |
| [REQ-SEC-005](REQ-SEC-005.md) | Untrusted input containment | SEC-INPUT |
| [REQ-SEC-006](REQ-SEC-006.md) | Dependency, model and tokenizer trust | SEC-SUPPLYCHAIN |
| [REQ-SEC-007](REQ-SEC-007.md) | Filesystem containment and restrictive permissions | SEC-FILES |
| [REQ-SEC-008](REQ-SEC-008.md) | Provider-secret architectural boundary | SEC-BOUNDARY |
| [REQ-SEC-009](REQ-SEC-009.md) | External-service disclosure boundary | SEC-EXTERNAL |
| [REQ-DOM-001](REQ-DOM-001.md) | Source-neutral media identity | DOMAIN-MEDIA |
| [REQ-DOM-002](REQ-DOM-002.md) | Explicit Job lifecycle state machine | DOMAIN-JOB |
| [REQ-DOM-003](REQ-DOM-003.md) | Truthful transcript and language semantics | DOMAIN-TRANSCRIPT |
| [REQ-DOM-004](REQ-DOM-004.md) | Canonical and derived artifact taxonomy | DOMAIN-ARTIFACT |
| [REQ-DOM-005](REQ-DOM-005.md) | Versioned processing fingerprint and run provenance | DOMAIN-PROVENANCE |
| [REQ-DATA-001](REQ-DATA-001.md) | Durable Job state and restart/delivery request context | DATA-JOB |
| [REQ-DATA-002](REQ-DATA-002.md) | Volatile media ownership and lifecycle | DATA-MEDIA |
| [REQ-DATA-003](REQ-DATA-003.md) | Dual canonical transcript persistence and explicit linkage | DATA-TRANSCRIPT, DATA-MARKDOWN |
| [REQ-DATA-004](REQ-DATA-004.md) | Canonical completion consistency and artifact-reference truth | DATA-INTEGRITY |
| [REQ-DATA-005](REQ-DATA-005.md) | Derived artifact association and authority | DATA-DERIVED |
| [REQ-DATA-006](REQ-DATA-006.md) | Bounded private operational logs | DATA-OPSLOG |
| [REQ-DATA-007](REQ-DATA-007.md) | Reconstructible cache lifecycle | DATA-CACHE |
| [REQ-DATA-008](REQ-DATA-008.md) | Backward-compatible persisted representations and migrations | DATA-COMPAT |
| [REQ-DATA-009](REQ-DATA-009.md) | Credential-free standard backup and restore integrity | DATA-BACKUP |
| [REQ-DATA-010](REQ-DATA-010.md) | Completed-Job retention policy and canonical preservation | DATA-RETENTION |
| [REQ-DATA-011](REQ-DATA-011.md) | Textual-search index data and lifecycle | DATA-SEARCH |

## B — Architecture reconvergence

| ID | Title | Families |
|---|---|---|
| [REQ-ARC-001](REQ-ARC-001.md) | Mechanically enforced dependency direction | ARCH-BOUNDARY |
| [REQ-ARC-002](REQ-ARC-002.md) | Application workflow ownership and thin Telegram transport | ARCH-APP, ARCH-TRANSPORT |
| [REQ-ARC-003](REQ-ARC-003.md) | Application-owned execution, queue, cancellation and recovery coordination | ARCH-EXECUTION |
| [REQ-ARC-004](REQ-ARC-004.md) | Runtime and hardware policy outside pure domain | ARCH-RUNTIME |
| [REQ-ARC-005](REQ-ARC-005.md) | Diarization capability, fallback and credential isolation | ARCH-DIAR |
| [REQ-ARC-006](REQ-ARC-006.md) | Canonical transcript store and renderer contracts | ARCH-TRANSCRIPT |
| [REQ-ARC-007](REQ-ARC-007.md) | Separated lifecycle persistence, indexing and search capabilities | ARCH-PERSIST |
| [REQ-ARC-008](REQ-ARC-008.md) | Application summary policy and infrastructure text-generation transport | ARCH-TEXTGEN |
| [REQ-ARC-009](REQ-ARC-009.md) | Operational policy separated from external I/O mechanisms | ARCH-OPS |
| [REQ-ARC-010](REQ-ARC-010.md) | Truthful configuration taxonomy and external compatibility | ARCH-CONFIG |
| [REQ-ARC-011](REQ-ARC-011.md) | Composition-root ownership of concrete providers and credentials | ARCH-COMPOSITION |
| [REQ-ARC-012](REQ-ARC-012.md) | Purpose-specific application-owned ports | ARCH-PORTS |
| [REQ-ARC-013](REQ-ARC-013.md) | Backend-neutral ASR contract | ARCH-ASR |

## C — Cross-cutting non-functional constraints

| ID | Title | Families |
|---|---|---|
| [REQ-NFR-001](REQ-NFR-001.md) | Deterministic lifecycle reliability and failure isolation | NFR-RELIABILITY |
| [REQ-NFR-002](REQ-NFR-002.md) | Bounded resource consumption and external waits | NFR-RESOURCE |
| [REQ-NFR-003](REQ-NFR-003.md) | Actionable privacy-aware observability | NFR-OBS |
| [REQ-NFR-004](REQ-NFR-004.md) | Supported runtime portability and environment-gated evidence | NFR-PORTABILITY |
| [REQ-NFR-005](REQ-NFR-005.md) | Cohesive, testable and reversible baseline refactoring | NFR-MAINTAIN |
| [REQ-NFR-006](REQ-NFR-006.md) | External behavior and data compatibility during baseline repair | NFR-COMPAT |
| [REQ-NFR-007](REQ-NFR-007.md) | Non-blocking Telegram transport responsiveness | NFR-RESOURCE |

## D — Current functional contract reconnection

| ID | Title | Families |
|---|---|---|
| [REQ-FUNC-001](REQ-FUNC-001.md) | Submit supported media and explicitly reprocess as a new Job | FUNC-SOURCE |
| [REQ-FUNC-002](REQ-FUNC-002.md) | Process media through truthful subtitle, ASR and diarization paths | FUNC-PROCESS |
| [REQ-FUNC-003](REQ-FUNC-003.md) | Primary and derivative delivery outcomes | FUNC-DELIVERY |
| [REQ-FUNC-004](REQ-FUNC-004.md) | Observe queue/status and cancel scoped work | FUNC-CONTROL |
| [REQ-FUNC-005](REQ-FUNC-005.md) | Browse and retrieve completed history | FUNC-HISTORY |
| [REQ-FUNC-006](REQ-FUNC-006.md) | Rename and merge speakers from canonical evidence | FUNC-EDIT |
| [REQ-FUNC-007](REQ-FUNC-007.md) | Generate a derived summary from canonical evidence | FUNC-SUMMARY |
| [REQ-FUNC-008](REQ-FUNC-008.md) | Generate transcript exports from canonical evidence | FUNC-EXPORT |
| [REQ-FUNC-009](REQ-FUNC-009.md) | Inspect runtime health safely | FUNC-DIAG |
| [REQ-FUNC-010](REQ-FUNC-010.md) | Inspect the latest relevant operational error | FUNC-DIAG |
| [REQ-FUNC-011](REQ-FUNC-011.md) | Safely clear reconstructible cache | FUNC-MAINT |
| [REQ-FUNC-012](REQ-FUNC-012.md) | Command, help and documentation conformance | FUNC-INTERFACE |
| [REQ-FUNC-013](REQ-FUNC-013.md) | Text-search completed history | FUNC-SEARCH |
| [REQ-FUNC-014](REQ-FUNC-014.md) | Generate YouTube MP4 with selectable subtitles | FUNC-VIDEO |

## E — Operational closure and evidence

| ID | Title | Families |
|---|---|---|
| [REQ-OPS-001](REQ-OPS-001.md) | Source-valid startup and restart reconciliation | OPS-STARTUP |
| [REQ-OPS-002](REQ-OPS-002.md) | Automatic completed-Job retention execution | OPS-RETENTION |
| [REQ-OPS-003](REQ-OPS-003.md) | Private host installation and systemd service lifecycle | OPS-SERVICE |
| [REQ-OPS-004](REQ-OPS-004.md) | Credential-free backup and validated restore procedure | OPS-BACKUP |
| [REQ-OPS-005](REQ-OPS-005.md) | Versioned upgrade and rollback procedure | OPS-UPGRADE |
| [REQ-OPS-006](REQ-OPS-006.md) | Manual artifact recovery after delivery failure | OPS-RECOVERY |
| [REQ-OPS-007](REQ-OPS-007.md) | Reproducible host/staging readiness evidence | OPS-EVIDENCE |
