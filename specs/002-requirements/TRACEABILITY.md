# Requirement-Tree Traceability

Version: **1.0.0**

## Operator use cases to requirement families

| Behavioral item | Primary requirement families |
|---|---|
| UC-001 Transcribe/reprocess media | FUNC-SOURCE, FUNC-PROCESS, FUNC-DELIVERY, DOMAIN-MEDIA, DOMAIN-JOB, DOMAIN-TRANSCRIPT, DOMAIN-PROVENANCE, ARCH-TRANSPORT, ARCH-EXECUTION, ARCH-RUNTIME, ARCH-ASR, ARCH-DIAR, ARCH-TRANSCRIPT, DATA-JOB, DATA-MEDIA, DATA-TRANSCRIPT, DATA-INTEGRITY, SEC-AUTH, SEC-INPUT, SEC-PRIVACY, NFR-RESOURCE, NFR-RELIABILITY |
| UC-002 Monitor | FUNC-CONTROL, ARCH-TRANSPORT, ARCH-EXECUTION, DATA-JOB, NFR-OBS, SEC-PRIVACY, SEC-SANITIZE |
| UC-003 Cancel | FUNC-CONTROL, DOMAIN-JOB, ARCH-EXECUTION, ARCH-TRANSPORT, DATA-JOB, DATA-MEDIA, NFR-RELIABILITY, SEC-SANITIZE |
| UC-004 History/retrieve | FUNC-HISTORY, FUNC-DELIVERY, ARCH-TRANSPORT, DATA-JOB, DATA-MARKDOWN, DATA-INTEGRITY, SEC-PRIVACY |
| UC-005 Search | FUNC-SEARCH, ARCH-PERSIST, DATA-SEARCH, SEC-PRIVACY, SEC-SANITIZE, NFR-RESOURCE |
| UC-006 Rename/merge | FUNC-EDIT, DOMAIN-TRANSCRIPT, DOMAIN-ARTIFACT, ARCH-APP, ARCH-TRANSCRIPT, DATA-JOB, DATA-TRANSCRIPT, DATA-MARKDOWN, DATA-SEARCH, DATA-INTEGRITY, SEC-PRIVACY |
| UC-007 Summary | FUNC-SUMMARY, FUNC-DELIVERY, ARCH-APP, ARCH-TEXTGEN, ARCH-TRANSPORT, DATA-TRANSCRIPT, DATA-DERIVED, DATA-SEARCH, DATA-INTEGRITY, SEC-EXTERNAL, SEC-SECRETS, SEC-PRIVACY, SEC-SUPPLYCHAIN, NFR-RESOURCE |
| UC-008 Export | FUNC-EXPORT, FUNC-DELIVERY, ARCH-APP, ARCH-TRANSCRIPT, ARCH-TRANSPORT, DATA-TRANSCRIPT, DATA-DERIVED, DATA-INTEGRITY, SEC-PRIVACY |
| UC-009 Video subtitles | FUNC-VIDEO, FUNC-DELIVERY, DOMAIN-MEDIA, ARCH-TRANSPORT, DATA-MEDIA, DATA-TRANSCRIPT, DATA-DERIVED, DATA-INTEGRITY, SEC-SECRETS, SEC-PRIVACY, SEC-INPUT, NFR-RESOURCE |
| UC-010 Healthcheck | FUNC-DIAG, ARCH-OPS, ARCH-CONFIG, DATA-OPSLOG, DATA-CACHE, NFR-OBS, NFR-PORTABILITY, SEC-SECRETS, SEC-SANITIZE, SEC-FILES, SEC-EXTERNAL, SEC-SUPPLYCHAIN, OPS-SERVICE |
| UC-011 Last error | FUNC-DIAG, ARCH-OPS, DATA-OPSLOG, NFR-OBS, SEC-SANITIZE, SEC-PRIVACY, OPS-RECOVERY |
| UC-012 Clear cache | FUNC-MAINT, ARCH-OPS, DATA-CACHE, SEC-FILES, SEC-SUPPLYCHAIN, NFR-RESOURCE |

## System/operational/interface traceability

| Behavioral item | Primary requirement families |
|---|---|
| SS-001 Startup recovery | DOMAIN-JOB, ARCH-EXECUTION, DATA-JOB, DATA-MEDIA, DATA-COMPAT, DATA-INTEGRITY, NFR-RELIABILITY, OPS-STARTUP |
| SS-002 Retention | DOMAIN-ARTIFACT, ARCH-OPS, DATA-MEDIA, DATA-OPSLOG, DATA-INTEGRITY, DATA-RETENTION, SEC-PRIVACY, SEC-FILES, NFR-RESOURCE, OPS-RETENTION |
| OS-001 Service lifecycle | ARCH-COMPOSITION, OPS-SERVICE, OPS-EVIDENCE, NFR-OBS, NFR-PORTABILITY, SEC-SECRETS, SEC-FILES |
| OS-002 Backup/restore | DATA-BACKUP, DATA-INTEGRITY, SEC-FILES, SEC-PRIVACY, SEC-SECRETS, OPS-BACKUP, OPS-EVIDENCE |
| OS-003 Upgrade/rollback | DATA-COMPAT, DATA-BACKUP, NFR-COMPAT, OPS-UPGRADE, OPS-BACKUP, OPS-EVIDENCE |
| OS-004 Manual artifact recovery | FUNC-DIAG, FUNC-DELIVERY, DATA-DERIVED, DATA-MARKDOWN, DATA-INTEGRITY, SEC-PRIVACY, SEC-FILES, OPS-RECOVERY, OPS-EVIDENCE |
| IC-001 Interface conformance | FUNC-INTERFACE, NFR-COMPAT, NFR-MAINTAIN, SEC-SANITIZE |

## Cross-cutting baseline-only traceability

| Requirement family | Primary normative source / current reason |
|---|---|
| ARCH-BOUNDARY, ARCH-PORTS, ARCH-APP, ARCH-COMPOSITION | Constitution + `000-baseline/ARCHITECTURE.md` |
| ARCH-TRANSPORT, ARCH-EXECUTION | Architecture target + current Telegram adapter/queue responsibility concentration |
| ARCH-RUNTIME | Constitution domain purity + current `Device`/`ComputeType`/`ModelName` runtime/provider leakage |
| ARCH-DIAR | Current independent diarization capability, fallback and credential boundary |
| ARCH-OPS | Constitution external-capability rule + current application services owning direct filesystem/network/log I/O |
| ARCH-CONFIG | Architecture/domain/security specs + current monolithic secret-bearing `AppSettings` and duplicate signatures |
| DATA-MEDIA, DATA-CACHE | Explicit data classes in `DATA-AND-ARTIFACTS.md` previously missing from the 0.1 tree |
| DATA-INTEGRITY | Canonical evidence contract + current optional snapshot persistence/stale artifact-reference risks |
| SEC-INPUT | Constitution defense-in-depth + external media/provider/tool boundaries |
| SEC-SUPPLYCHAIN | Constitution security principle + current dependency/model/tokenizer trust surfaces including `trust_remote_code` |
| NFR-MAINTAIN, NFR-PORTABILITY, NFR-COMPAT | `QUALITY.md`, `PRODUCT.md`, frozen current contract |
| DATA-OPSLOG | `DATA-AND-ARTIFACTS.md`, `SECURITY-AND-OPERATIONS.md` |

## Coverage rule

Every frozen UC/SS/OS/IC maps to at least one FUNC/OPS branch and to the applicable domain/data/security/architecture constraints. Every branch either maps to frozen behavior or to an explicit constitutional/approved-baseline constraint/current deviation. No branch exists solely to anticipate a future feature.

## Complete branch-coverage check

The following families are mainly constitutional/baseline constraints and may not be owned by one behavioral item, but they are explicitly traceable and remain in scope: ARCH-BOUNDARY, ARCH-PORTS, ARCH-RUNTIME, ARCH-ASR, ARCH-DIAR, ARCH-TRANSCRIPT, ARCH-PERSIST, ARCH-TEXTGEN, ARCH-CONFIG, ARCH-COMPOSITION, ARCH-OPS, SEC-BOUNDARY, DOMAIN-PROVENANCE, DATA-MARKDOWN, DATA-RETENTION, OPS-EVIDENCE.

A mechanical review confirms that every one of the 66 requirement families appears in this traceability document.
