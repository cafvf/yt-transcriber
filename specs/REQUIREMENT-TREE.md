# System Requirement Tree

Version: **0.1.0-draft**

## SYS-001 — Private local-first transcription and transcript-artifact system

The system shall preserve the approved current product behavior while eliminating known architectural, domain, data, security, and operational inconsistencies before new product functionality is introduced.

```text
SYS-001
│
├─ FUNC — Functional capability families
│  ├─ FUNC-SOURCE       Source submission, validation, identity, explicit reprocessing
│  ├─ FUNC-PROCESS      Queueing, acquisition, subtitle shortcut, conversion, ASR, diarization, rendering
│  ├─ FUNC-DELIVERY     Artifact delivery, retry, completed/delivery_failed outcome
│  ├─ FUNC-CONTROL      Status/queue observation and cancellation
│  ├─ FUNC-HISTORY      Completed-history browse/retrieve
│  ├─ FUNC-SEARCH       Textual history search and bounded fallback
│  ├─ FUNC-EDIT         Speaker alias/merge and transcript re-render
│  ├─ FUNC-SUMMARY      Derived summary generation
│  ├─ FUNC-EXPORT       TXT/JSON/SRT/VTT generation
│  ├─ FUNC-VIDEO        YouTube selectable-subtitle MP4 derivative
│  ├─ FUNC-DIAG         Healthcheck and latest-error diagnostics
│  ├─ FUNC-MAINT        Safe reconstructible-cache cleanup
│  └─ FUNC-INTERFACE    Current commands, aliases, help, documentation conformance
│
├─ DOMAIN — Domain model and invariant families
│  ├─ DOMAIN-MEDIA      MediaSource identity and source-type taxonomy
│  ├─ DOMAIN-JOB        Job identity, semantic lifecycle states, terminal states, transition graph
│  ├─ DOMAIN-TRANSCRIPT Canonical transcript/segments/speaker semantics
│  ├─ DOMAIN-ARTIFACT   Canonical vs derived vs volatile artifact semantics
│  └─ DOMAIN-PROVENANCE Processing fingerprint, source identity, model/backend/language provenance
│
├─ ARCH — Architecture families
│  ├─ ARCH-BOUNDARY     Enforce domain/application/infrastructure/composition dependency direction
│  ├─ ARCH-PORTS        External capabilities accessed through application-owned contracts
│  ├─ ARCH-APP          Application-owned use-case/policy orchestration; thin transport adapters
│  ├─ ARCH-TRANSCRIPT   Transcript store/render contracts independent of concrete filesystem renderer
│  ├─ ARCH-PERSIST      Separate Job persistence, transcript storage, indexing, and search responsibilities
│  ├─ ARCH-ASR          Backend-neutral ASR application contract/runtime policy
│  ├─ ARCH-TEXTGEN      Backend-neutral text-generation contract and application summary policy
│  ├─ ARCH-CONFIG       Coherent configuration taxonomy and single processing-fingerprint authority
│  └─ ARCH-COMPOSITION  Concrete adapters, credentials, and provider setup wired only at composition/infrastructure edge
│
├─ DATA — Persistence/data/artifact families
│  ├─ DATA-JOB          Durable Job state, restart payload, lifecycle/provenance fields
│  ├─ DATA-TRANSCRIPT   Versioned canonical structured transcript snapshot
│  ├─ DATA-MARKDOWN     Canonical human-readable Markdown rendering
│  ├─ DATA-DERIVED      Summary/export/video derivative association and provenance
│  ├─ DATA-SEARCH       FTS/index documents, refresh/backfill, bounded fallback support
│  ├─ DATA-OPSLOG       Sanitized operational-error/audit/log persistence and lifecycle
│  ├─ DATA-RETENTION    Artifact-class retention/deletion and truthful references
│  ├─ DATA-COMPAT       Backward-compatible persisted representations, including legacy `downloading` for semantic acquiring state
│  └─ DATA-BACKUP       Backup/restore set, integrity, permissions, and sensitive-data handling
│
├─ NFR — Non-functional families
│  ├─ NFR-RELIABILITY   Deterministic lifecycle outcomes, idempotent recovery, failure isolation
│  ├─ NFR-RESOURCE      Sequential processing, bounded queue/storage, timeouts/limits, safe resource fallback
│  ├─ NFR-OBS           Actionable diagnostics/audit with minimal sensitive content
│  ├─ NFR-PORTABILITY   Supported Python/Linux/runtime expectations without hiding environment-gated checks
│  ├─ NFR-MAINTAIN      Cohesion, testability, reversible change, no speculative abstractions
│  └─ NFR-COMPAT        Preserve current externally visible behavior/data unless a versioned decision changes it
│
├─ SEC — Information-security families
│  ├─ SEC-AUTH          Single authorized operator and silent rejection of unauthorized Telegram users
│  ├─ SEC-SECRETS       Secret storage, least privilege, no versioning/logging/prompt disclosure, rotation/revocation after exposure
│  ├─ SEC-PRIVACY       Private classification of media, transcripts, indexes, logs, backups, paths, IDs, derived artifacts
│  ├─ SEC-SANITIZE      Central sanitization of errors/diagnostics/audit/Telegram output
│  ├─ SEC-BOUNDARY      Provider credentials never become domain/application business payload
│  ├─ SEC-EXTERNAL      Explicit trust-boundary handling for external text-generation or provider endpoints
│  └─ SEC-FILES         Path containment, restrictive permissions, protected backups, no arbitrary deletion
│
└─ OPS — Operational families
   ├─ OPS-STARTUP       Startup/restart Job reconciliation and deterministic pending requeue
   ├─ OPS-RETENTION     Automatic volatile-artifact retention execution
   ├─ OPS-SERVICE       systemd start/status/stop/restart and logs
   ├─ OPS-BACKUP        Backup and restore procedure/validation
   ├─ OPS-UPGRADE       Upgrade and rollback procedure/validation
   ├─ OPS-RECOVERY      Manual artifact recovery after delivery failure/interruption
   └─ OPS-EVIDENCE      Reproducible sanitized host/staging evidence required for private-production readiness
```

## Interpretation rule

Top-level and second-level identifiers define coverage areas. Atomic requirement IDs will be created later beneath these branches. No implementation technology should be inferred solely from branch names except where the approved baseline already constrains the external contract (for example private Telegram interaction and systemd deployment target).
