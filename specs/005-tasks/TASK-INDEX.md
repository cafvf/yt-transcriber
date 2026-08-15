# Task Index

Version: **1.0.0**
Status: **Approved / Frozen**

| Task | Plan | Primary REQ | Supports | Role | Title |
|---|---|---|---|---|---|
| `TASK-P01-000` | PLAN-001 | — | Constitution II; `000-baseline/QUALITY.md` | support / characterization | Capture clean execution baseline and frozen-interface characterization |
| `TASK-P01-001` | PLAN-001 | `REQ-SEC-001` | — | change owner | Authorized operator and approved Telegram audience |
| `TASK-P01-002` | PLAN-001 | `REQ-SEC-002` | — | change owner | Provider-secret storage, privilege and incident lifecycle |
| `TASK-P01-003` | PLAN-001 | `REQ-SEC-003` | — | change owner | Private-data classification and minimization |
| `TASK-P01-004` | PLAN-001 | `REQ-SEC-004` | — | change owner | Centralized sanitization of disclosure paths |
| `TASK-P01-005` | PLAN-001 | `REQ-SEC-005` | — | change owner | Untrusted input containment |
| `TASK-P01-006` | PLAN-001 | `REQ-SEC-006` | — | change owner | Dependency, model and tokenizer trust |
| `TASK-P01-007` | PLAN-001 | `REQ-SEC-007` | — | change owner | Filesystem containment and restrictive permissions |
| `TASK-P01-008` | PLAN-001 | — | — | plan gate | PLAN-001 exit-gate verification |
| `TASK-P02-001` | PLAN-002 | `REQ-DOM-001` | — | change owner | Source-neutral media identity |
| `TASK-P02-002` | PLAN-002 | `REQ-DOM-002` | — | change owner | Explicit Job lifecycle state machine |
| `TASK-P02-003` | PLAN-002 | `REQ-DOM-003` | — | change owner | Truthful transcript and language semantics |
| `TASK-P02-004` | PLAN-002 | `REQ-DOM-004` | — | change owner | Canonical and derived artifact taxonomy |
| `TASK-P02-005` | PLAN-002 | `REQ-DOM-005` | — | change owner | Versioned processing fingerprint and run provenance |
| `TASK-P02-006` | PLAN-002 | `REQ-DATA-002` | — | change owner | Volatile media ownership and lifecycle |
| `TASK-P02-007` | PLAN-002 | `REQ-DATA-001` | — | change owner | Durable Job state and restart/delivery request context |
| `TASK-P02-008` | PLAN-002 | `REQ-DATA-003` | — | change owner | Dual canonical transcript persistence and explicit linkage |
| `TASK-P02-009` | PLAN-002 | `REQ-DATA-008` | — | change owner | Backward-compatible persisted representations and migrations |
| `TASK-P02-010` | PLAN-002 | `REQ-DATA-010` | — | change owner | Completed-Job retention policy and canonical preservation |
| `TASK-P02-011` | PLAN-002 | `REQ-DATA-004` | — | change owner | Canonical completion consistency and artifact-reference truth |
| `TASK-P02-012` | PLAN-002 | `REQ-NFR-006` | — | assurance owner | External behavior and data compatibility during baseline repair |
| `TASK-P02-013` | PLAN-002 | — | — | plan gate | PLAN-002 exit-gate verification |
| `TASK-P03-001` | PLAN-003 | — | `REQ-ARC-001` | support / foundation | Bootstrap architecture dependency ratchet |
| `TASK-P03-002` | PLAN-003 | `REQ-SEC-008` | — | change owner | Provider-secret architectural boundary |
| `TASK-P03-003` | PLAN-003 | — | `REQ-ARC-012` | support / foundation | Establish purpose-specific port conventions and capability inventory |
| `TASK-P03-004` | PLAN-003 | `REQ-ARC-004` | — | change owner | Runtime and hardware policy outside pure domain |
| `TASK-P03-005` | PLAN-003 | `REQ-ARC-010` | — | change owner | Truthful configuration taxonomy and external compatibility |
| `TASK-P03-006` | PLAN-003 | `REQ-ARC-011` | — | change owner | Composition-root ownership of concrete providers and credentials |
| `TASK-P03-007` | PLAN-003 | `REQ-ARC-013` | — | change owner | Backend-neutral ASR contract |
| `TASK-P03-008` | PLAN-003 | `REQ-ARC-005` | — | change owner | Diarization capability, fallback and credential isolation |
| `TASK-P03-009` | PLAN-003 | `REQ-ARC-006` | — | change owner | Canonical transcript store and renderer contracts |
| `TASK-P03-010` | PLAN-003 | `REQ-SEC-009` | — | change owner | External-service disclosure boundary |
| `TASK-P03-011` | PLAN-003 | — | `REQ-ARC-012` | support / convergence | Remove obsolete generic FileStorage surface after replacement/no-consumer evidence |
| `TASK-P03-012` | PLAN-003 | `REQ-ARC-001` | — | closure owner | Mechanically enforced dependency direction |
| `TASK-P03-013` | PLAN-003 | `REQ-ARC-012` | — | closure owner | Purpose-specific application-owned ports |
| `TASK-P03-014` | PLAN-003 | — | — | plan gate | PLAN-003 exit-gate verification |
| `TASK-P04-001` | PLAN-004 | — | `REQ-ARC-002` | support / foundation | Establish application workflow boundary and extract submission/dedup/reprocess admission |
| `TASK-P04-002` | PLAN-004 | `REQ-ARC-003` | — | change owner | Application-owned execution, queue, cancellation and recovery coordination |
| `TASK-P04-003` | PLAN-004 | — | `REQ-ARC-002` | support / foundation | Extract completed-history selection and retrieval workflow |
| `TASK-P04-004` | PLAN-004 | `REQ-DATA-005` | — | change owner | Derived artifact association and authority |
| `TASK-P04-005` | PLAN-004 | `REQ-DATA-011` | — | change owner | Textual-search index data and lifecycle |
| `TASK-P04-006` | PLAN-004 | `REQ-ARC-007` | — | change owner | Separated lifecycle persistence, indexing and search capabilities |
| `TASK-P04-007` | PLAN-004 | — | `REQ-ARC-002` | support / foundation | Extract textual-search application workflow |
| `TASK-P04-008` | PLAN-004 | — | `REQ-ARC-002` | support / foundation | Extract transcript edit/export/video-derivative orchestration |
| `TASK-P04-009` | PLAN-004 | `REQ-ARC-008` | — | change owner | Application summary policy and infrastructure text-generation transport |
| `TASK-P04-010` | PLAN-004 | `REQ-DATA-006` | — | change owner | Bounded private operational logs |
| `TASK-P04-011` | PLAN-004 | `REQ-DATA-007` | — | change owner | Reconstructible cache lifecycle |
| `TASK-P04-012` | PLAN-004 | `REQ-ARC-009` | — | change owner | Operational policy separated from external I/O mechanisms |
| `TASK-P04-013` | PLAN-004 | — | `REQ-ARC-002` | support / foundation | Extract operational command orchestration and retention invocation |
| `TASK-P04-014` | PLAN-004 | `REQ-ARC-002` | — | closure owner | Application workflow ownership and thin Telegram transport |
| `TASK-P04-015` | PLAN-004 | `REQ-NFR-001` | — | assurance owner | Deterministic lifecycle reliability and failure isolation |
| `TASK-P04-016` | PLAN-004 | `REQ-NFR-005` | — | assurance / convergence owner | Cohesive, testable and reversible baseline refactoring |
| `TASK-P04-017` | PLAN-004 | — | — | plan gate | PLAN-004 exit-gate verification |
| `TASK-P05-001` | PLAN-005 | `REQ-NFR-002` | — | change / acceptance owner | Bounded resource consumption and external waits |
| `TASK-P05-002` | PLAN-005 | `REQ-NFR-003` | — | change / acceptance owner | Actionable privacy-aware observability |
| `TASK-P05-003` | PLAN-005 | `REQ-NFR-007` | — | change / acceptance owner | Non-blocking Telegram transport responsiveness |
| `TASK-P05-004` | PLAN-005 | `REQ-FUNC-001` | — | change / acceptance owner | Submit supported media and explicitly reprocess as a new Job |
| `TASK-P05-005` | PLAN-005 | `REQ-FUNC-002` | — | change / acceptance owner | Process media through truthful subtitle, ASR and diarization paths |
| `TASK-P05-006` | PLAN-005 | `REQ-FUNC-003` | — | change / acceptance owner | Primary and derivative delivery outcomes |
| `TASK-P05-007` | PLAN-005 | `REQ-FUNC-004` | — | change / acceptance owner | Observe queue/status and cancel scoped work |
| `TASK-P05-008` | PLAN-005 | `REQ-FUNC-005` | — | change / acceptance owner | Browse and retrieve completed history |
| `TASK-P05-009` | PLAN-005 | `REQ-FUNC-013` | — | change / acceptance owner | Text-search completed history |
| `TASK-P05-010` | PLAN-005 | `REQ-FUNC-006` | — | change / acceptance owner | Rename and merge speakers from canonical evidence |
| `TASK-P05-011` | PLAN-005 | `REQ-FUNC-007` | — | change / acceptance owner | Generate a derived summary from canonical evidence |
| `TASK-P05-012` | PLAN-005 | `REQ-FUNC-008` | — | change / acceptance owner | Generate transcript exports from canonical evidence |
| `TASK-P05-013` | PLAN-005 | `REQ-FUNC-014` | — | change / acceptance owner | Generate YouTube MP4 with selectable subtitles |
| `TASK-P05-014` | PLAN-005 | `REQ-FUNC-009` | — | change / acceptance owner | Inspect runtime health safely |
| `TASK-P05-015` | PLAN-005 | `REQ-FUNC-010` | — | change / acceptance owner | Inspect the latest relevant operational error |
| `TASK-P05-016` | PLAN-005 | `REQ-FUNC-011` | — | change / acceptance owner | Safely clear reconstructible cache |
| `TASK-P05-017` | PLAN-005 | — | — | plan gate | PLAN-005 exit-gate verification |
| `TASK-P06-001` | PLAN-006 | `REQ-NFR-004` | — | assurance owner | Supported runtime portability and environment-gated evidence |
| `TASK-P06-002` | PLAN-006 | `REQ-DATA-009` | — | data-contract owner | Credential-free standard backup and restore integrity |
| `TASK-P06-003` | PLAN-006 | `REQ-OPS-001` | — | operational owner | Source-valid startup and restart reconciliation |
| `TASK-P06-004` | PLAN-006 | `REQ-OPS-002` | — | operational owner | Automatic completed-Job retention execution |
| `TASK-P06-005` | PLAN-006 | `REQ-OPS-003` | — | operational owner | Private host installation and systemd service lifecycle |
| `TASK-P06-006` | PLAN-006 | `REQ-OPS-004` | — | operational procedure owner | Credential-free backup and validated restore procedure |
| `TASK-P06-007` | PLAN-006 | `REQ-OPS-005` | — | operational procedure owner | Versioned upgrade and rollback procedure |
| `TASK-P06-008` | PLAN-006 | `REQ-OPS-006` | — | operational procedure owner | Manual artifact recovery after delivery failure |
| `TASK-P06-009` | PLAN-006 | `REQ-FUNC-012` | — | conformance owner | Command, help and documentation conformance |
| `TASK-P06-010` | PLAN-006 | `REQ-OPS-007` | — | evidence aggregator / owner | Reproducible host/staging readiness evidence |
| `TASK-P06-011` | PLAN-006 | — | — | plan gate | PLAN-006 exit-gate verification |
