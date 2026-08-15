# System Requirement Tree

Version: **1.0.0**
Status: **Approved / Frozen**

## SYS-001 — Private local-first transcription and transcript-artifact system

The system shall preserve the approved current product behavior while eliminating known architectural, domain, data, security, and operational inconsistencies before new product functionality is introduced.

```text
SYS-001
│
├─ FUNC — Functional capability families
│  ├─ FUNC-SOURCE       Source submission, validation, identity, explicit reprocessing
│  ├─ FUNC-PROCESS      Queueing, acquisition, subtitle shortcut, conversion, ASR, diarization, rendering
│  ├─ FUNC-DELIVERY     Primary/retrieval/derived artifact delivery, retry, and failure/outcome semantics
│  ├─ FUNC-CONTROL      Status/queue observation and cancellation
│  ├─ FUNC-HISTORY      Completed-history browse/retrieve
│  ├─ FUNC-SEARCH       Textual history search and bounded fallback
│  ├─ FUNC-EDIT         Speaker alias/merge and transcript re-render
│  ├─ FUNC-SUMMARY      Derived summary generation and index refresh
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
│  └─ DOMAIN-PROVENANCE Processing fingerprint, source identity, model/backend/language/runtime provenance
│
├─ ARCH — Architecture families
│  ├─ ARCH-BOUNDARY     Enforce domain/application/infrastructure/composition dependency direction
│  ├─ ARCH-PORTS        External capabilities accessed through purpose-specific application-owned contracts
│  ├─ ARCH-APP          Application-owned use-case and policy orchestration
│  ├─ ARCH-TRANSPORT    Thin Telegram transport: map inputs/outputs without owning application workflows
│  ├─ ARCH-EXECUTION    Application-owned queue/worker/cancellation/recovery/delivery coordination
│  ├─ ARCH-RUNTIME      Hardware capability and runtime/model-selection policy separated from pure domain
│  ├─ ARCH-ASR          Backend-neutral ASR application contract
│  ├─ ARCH-DIAR         Backend-neutral diarization contract, fallback semantics, credential isolation
│  ├─ ARCH-TRANSCRIPT   Transcript-store/render contracts independent of concrete filesystem renderer
│  ├─ ARCH-PERSIST      Separate Job persistence, transcript storage, indexing, and search responsibilities
│  ├─ ARCH-TEXTGEN      Backend-neutral text-generation contract and application summary policy
│  ├─ ARCH-OPS          Health/error/retention policies separated from concrete filesystem/network/log mechanisms
│  ├─ ARCH-CONFIG       Configuration-loading boundary, coherent taxonomy, secret separation, single fingerprint authority
│  └─ ARCH-COMPOSITION  Concrete adapters, credentials, provider/runtime setup wired at composition/infrastructure edge
│
├─ DATA — Persistence/data/artifact families
│  ├─ DATA-JOB          Durable Job state, restart payload, lifecycle/provenance fields
│  ├─ DATA-MEDIA        Staging/downloaded/converted media identity, ownership, cleanup, and lifecycle
│  ├─ DATA-TRANSCRIPT   Versioned canonical structured transcript snapshot
│  ├─ DATA-MARKDOWN     Canonical human-readable Markdown rendering
│  ├─ DATA-DERIVED      Summary/export/video derivative association, canonical linkage, provenance
│  ├─ DATA-SEARCH       FTS/index documents, refresh/backfill, bounded fallback support
│  ├─ DATA-OPSLOG       Sanitized operational-error/audit/application-log persistence, bounds, and lifecycle
│  ├─ DATA-CACHE        Model/tokenizer/cache ownership, reconstructibility, provenance, safe cleanup
│  ├─ DATA-INTEGRITY    Canonical-evidence atomicity/coherence, artifact-reference truth, orphan/corruption handling
│  ├─ DATA-RETENTION    Artifact-class retention/deletion with containment and truthful post-delete references
│  ├─ DATA-COMPAT       Backward-compatible persisted representations, including legacy `downloading` for semantic acquiring
│  └─ DATA-BACKUP       Backup/restore set, integrity, permissions, credential exclusion, sensitive-data handling
│
├─ NFR — Non-functional families
│  ├─ NFR-RELIABILITY   Deterministic lifecycle outcomes, idempotent recovery, failure isolation
│  ├─ NFR-RESOURCE      Sequential processing, bounded queue/storage/logs, timeouts/limits, safe resource fallback
│  ├─ NFR-OBS           Actionable diagnostics/audit with minimal sensitive content
│  ├─ NFR-PORTABILITY   Supported Python/Linux/runtime expectations with explicit environment-gated evidence
│  ├─ NFR-MAINTAIN      Cohesion, testability, reversible change, no speculative abstractions
│  └─ NFR-COMPAT        Preserve current externally visible behavior/data unless a versioned decision changes it
│
├─ SEC — Information-security families
│  ├─ SEC-AUTH          Single authorized operator, silent rejection, and explicit approved delivery-audience policy
│  ├─ SEC-SECRETS       Secret storage, least privilege, no versioning/logging/prompt disclosure, rotation/revocation
│  ├─ SEC-PRIVACY       Private classification of media, transcripts, indexes, logs, backups, paths, IDs, derivatives
│  ├─ SEC-SANITIZE      One coherent sanitization policy for errors/diagnostics/audit/Telegram disclosure paths
│  ├─ SEC-BOUNDARY      Provider credentials never become domain/application business payload
│  ├─ SEC-INPUT         Treat URLs/media/filenames/provider output/transcript content as untrusted boundary input
│  ├─ SEC-EXTERNAL      Explicit trust-boundary handling for external text-generation/provider endpoints
│  ├─ SEC-SUPPLYCHAIN   Dependency/model/tokenizer provenance, lock integrity, executable remote-code trust controls
│  └─ SEC-FILES         Path containment, restrictive permissions, protected backups, safe deletion
│
└─ OPS — Operational families
   ├─ OPS-STARTUP       Startup/restart Job reconciliation and source-valid pending requeue
   ├─ OPS-RETENTION     Automatic configured volatile-artifact retention execution
   ├─ OPS-SERVICE       Host installation/deployment prerequisites plus systemd lifecycle, least-privilege runtime, logs
   ├─ OPS-BACKUP        Backup and restore procedure/validation under approved credential-exclusion policy
   ├─ OPS-UPGRADE       Upgrade and rollback procedure/validation
   ├─ OPS-RECOVERY      Manual artifact recovery after delivery failure/interruption
   └─ OPS-EVIDENCE      Reproducible sanitized host/staging evidence required for private-production readiness
```

## Interpretation rules

1. Top-level and second-level identifiers define coverage areas, not atomic requirements.
2. A branch may be cross-cutting without being owned by a single use case.
3. Architecture families describe **ownership and boundary intent**, not concrete implementation tools.
4. `FUNC-DELIVERY` distinguishes primary-transcription delivery from delivery of already-completed/derived artifacts: only the former participates in the `delivering -> completed|delivery_failed` Job lifecycle contract.
5. `DATA-INTEGRITY` prevents a successful Job from claiming canonical evidence that was not durably created and prevents durable metadata from silently pointing at purged/non-owned artifacts.
6. `DATA-MEDIA` is distinct from `DATA-RETENTION`: media lifecycle includes staging/rejection/cancel/failure/restart cleanup, not only FIFO cleanup of old completed Jobs.
7. `SEC-SUPPLYCHAIN` does not prohibit local Hugging Face/model tooling; it requires explicit trust/provenance decisions, especially when executable model/tokenizer code can be enabled.
8. No new product functionality is introduced by these branches. They make current behavior and current hardening obligations explicit.
