# Requirement Branch Dependencies

Version: **1.0.0**
Status: **Approved / Frozen**

## 1. Dependency principles

The dependency model is not a project-task schedule. It answers which concepts must be stable enough for another requirement family to be specified without circular or accidental assumptions.

Security is cross-cutting, but not every `SEC-*` branch can be completely specified before architecture. Foundational security invariants are defined early; boundary-specific security is co-derived with the architectural boundary it constrains.

## 2. Core graph

```text
CONSTITUTION + 000-baseline + 001-use-cases
                  │
                  ├─> evidence inventory / brownfield facts
                  │
                  ├─> SEC-AUTH / SEC-SECRETS / SEC-PRIVACY
                  │    SEC-INPUT / SEC-SUPPLYCHAIN / SEC-FILES / SEC-SANITIZE
                  │
                  ├─> DOMAIN-MEDIA ─> DOMAIN-JOB
                  │        │              └─> DATA-JOB ─> OPS-STARTUP
                  │        └─> DATA-MEDIA ───────────────┘
                  │
                  ├─> DOMAIN-TRANSCRIPT ─> DATA-TRANSCRIPT ─> DATA-MARKDOWN
                  │         │                      │
                  │         └─> DOMAIN-ARTIFACT    ├─> DATA-DERIVED
                  │                                ├─> DATA-SEARCH
                  │                                └─> DATA-INTEGRITY
                  │
                  └─> ARCH-BOUNDARY ─> ARCH-PORTS ─> ARCH-APP
                                      │              ├─> ARCH-TRANSPORT
                                      │              ├─> ARCH-EXECUTION
                                      │              ├─> ARCH-TRANSCRIPT
                                      │              ├─> ARCH-TEXTGEN
                                      │              └─> ARCH-OPS
                                      └─> ARCH-RUNTIME ─> ARCH-ASR / ARCH-DIAR
```

`DATA-INTEGRITY` then constrains completion, retention, recovery, history and all transcript-consuming workflows. `SEC-*` constrains every branch even when not drawn on every arrow.

## 3. Direct prerequisite matrix

`baseline` below means the ratified Constitution + approved `000-baseline` + frozen `001-use-cases` where behavior is involved.

| Branch | Direct conceptual prerequisites |
|---|---|
| DOMAIN-MEDIA | baseline |
| DOMAIN-JOB | DOMAIN-MEDIA |
| DOMAIN-TRANSCRIPT | baseline |
| DOMAIN-ARTIFACT | DOMAIN-TRANSCRIPT |
| DOMAIN-PROVENANCE | DOMAIN-MEDIA, DOMAIN-JOB, DOMAIN-TRANSCRIPT |
| SEC-AUTH | baseline |
| SEC-SECRETS | baseline |
| SEC-PRIVACY | baseline |
| SEC-INPUT | baseline, SEC-PRIVACY |
| SEC-SUPPLYCHAIN | baseline, SEC-SECRETS |
| SEC-FILES | SEC-PRIVACY |
| SEC-SANITIZE | SEC-SECRETS, SEC-PRIVACY |
| SEC-BOUNDARY | SEC-SECRETS, ARCH-BOUNDARY |
| SEC-EXTERNAL | SEC-SECRETS, SEC-PRIVACY, SEC-INPUT |
| DATA-JOB | DOMAIN-JOB, DOMAIN-MEDIA, DOMAIN-PROVENANCE |
| DATA-MEDIA | DOMAIN-MEDIA, DOMAIN-ARTIFACT, SEC-PRIVACY, SEC-FILES |
| DATA-TRANSCRIPT | DOMAIN-TRANSCRIPT, DOMAIN-PROVENANCE |
| DATA-MARKDOWN | DOMAIN-TRANSCRIPT, DOMAIN-ARTIFACT, DATA-TRANSCRIPT |
| DATA-DERIVED | DOMAIN-ARTIFACT, DOMAIN-PROVENANCE, DATA-TRANSCRIPT, DATA-INTEGRITY |
| DATA-OPSLOG | SEC-SANITIZE, SEC-PRIVACY |
| DATA-CACHE | DOMAIN-ARTIFACT, SEC-FILES, SEC-SUPPLYCHAIN |
| DATA-SEARCH | DATA-JOB, DATA-TRANSCRIPT, DATA-DERIVED, SEC-PRIVACY |
| DATA-INTEGRITY | DATA-JOB, DATA-MEDIA, DATA-TRANSCRIPT, DATA-MARKDOWN |
| DATA-RETENTION | DOMAIN-ARTIFACT, DATA-INTEGRITY, DATA-MEDIA, DATA-OPSLOG, DATA-CACHE |
| DATA-COMPAT | DOMAIN-JOB, DATA-JOB, DATA-TRANSCRIPT |
| DATA-BACKUP | DATA-JOB, DATA-MEDIA, DATA-TRANSCRIPT, DATA-MARKDOWN, DATA-DERIVED, DATA-OPSLOG, SEC-SECRETS, SEC-PRIVACY, SEC-FILES |
| ARCH-BOUNDARY | baseline |
| ARCH-PORTS | ARCH-BOUNDARY |
| ARCH-APP | ARCH-BOUNDARY, ARCH-PORTS |
| ARCH-CONFIG | ARCH-BOUNDARY, DOMAIN-PROVENANCE, SEC-SECRETS |
| ARCH-TRANSPORT | ARCH-APP, ARCH-PORTS, SEC-AUTH, SEC-INPUT |
| ARCH-EXECUTION | ARCH-APP, DOMAIN-JOB, DATA-JOB |
| ARCH-RUNTIME | ARCH-PORTS, ARCH-CONFIG |
| ARCH-ASR | ARCH-PORTS, ARCH-RUNTIME, DOMAIN-PROVENANCE |
| ARCH-DIAR | ARCH-PORTS, ARCH-RUNTIME, DOMAIN-PROVENANCE, SEC-BOUNDARY |
| ARCH-TRANSCRIPT | ARCH-APP, ARCH-PORTS, DOMAIN-TRANSCRIPT, DOMAIN-ARTIFACT, DATA-INTEGRITY |
| ARCH-PERSIST | ARCH-PORTS, DATA-JOB, DATA-TRANSCRIPT |
| ARCH-TEXTGEN | ARCH-APP, ARCH-PORTS, SEC-EXTERNAL, SEC-SUPPLYCHAIN |
| ARCH-OPS | ARCH-APP, ARCH-PORTS, DATA-OPSLOG, SEC-FILES |
| ARCH-COMPOSITION | ARCH-BOUNDARY, ARCH-PORTS, ARCH-CONFIG, SEC-BOUNDARY |
| NFR-RELIABILITY | DOMAIN-JOB, DATA-INTEGRITY |
| NFR-RESOURCE | DATA-MEDIA, DATA-CACHE, DATA-OPSLOG |
| NFR-OBS | DATA-OPSLOG, SEC-SANITIZE |
| NFR-PORTABILITY | ARCH-RUNTIME, ARCH-COMPOSITION |
| NFR-MAINTAIN | ARCH-BOUNDARY, ARCH-APP |
| NFR-COMPAT | DATA-COMPAT, frozen external contract |
| FUNC-SOURCE | DOMAIN-MEDIA, DATA-MEDIA, ARCH-TRANSPORT, SEC-AUTH, SEC-INPUT |
| FUNC-PROCESS | FUNC-SOURCE, DOMAIN-JOB, DOMAIN-TRANSCRIPT, ARCH-EXECUTION, ARCH-RUNTIME, ARCH-ASR, ARCH-DIAR, ARCH-TRANSCRIPT, DATA-INTEGRITY |
| FUNC-DELIVERY | ARCH-TRANSPORT, DOMAIN-JOB, DATA-INTEGRITY, SEC-AUTH, SEC-PRIVACY, NFR-RELIABILITY |
| FUNC-CONTROL | DOMAIN-JOB, DATA-JOB, ARCH-EXECUTION, ARCH-TRANSPORT |
| FUNC-HISTORY | DATA-JOB, DATA-MARKDOWN, DATA-INTEGRITY, ARCH-TRANSPORT |
| FUNC-SEARCH | FUNC-HISTORY, DATA-SEARCH, ARCH-PERSIST |
| FUNC-EDIT | DATA-JOB, DATA-TRANSCRIPT, DATA-MARKDOWN, DATA-SEARCH, DATA-INTEGRITY, ARCH-TRANSCRIPT |
| FUNC-SUMMARY | DATA-TRANSCRIPT, DATA-DERIVED, DATA-SEARCH, ARCH-TEXTGEN, FUNC-DELIVERY, SEC-EXTERNAL |
| FUNC-EXPORT | DATA-TRANSCRIPT, DATA-DERIVED, DATA-INTEGRITY, ARCH-TRANSCRIPT, FUNC-DELIVERY |
| FUNC-VIDEO | DOMAIN-MEDIA, DATA-MEDIA, DATA-TRANSCRIPT, DATA-DERIVED, DATA-INTEGRITY, FUNC-DELIVERY, SEC-INPUT |
| FUNC-DIAG | ARCH-OPS, DATA-OPSLOG, NFR-OBS |
| FUNC-MAINT | ARCH-OPS, DATA-CACHE, SEC-FILES |
| FUNC-INTERFACE | stabilized current FUNC families, IC-001, NFR-COMPAT |
| OPS-STARTUP | DOMAIN-JOB, DATA-JOB, DATA-MEDIA, ARCH-EXECUTION, NFR-RELIABILITY |
| OPS-RETENTION | DATA-RETENTION, ARCH-OPS |
| OPS-SERVICE | ARCH-COMPOSITION, NFR-PORTABILITY, NFR-OBS, SEC-SECRETS, SEC-FILES |
| OPS-BACKUP | DATA-BACKUP, OPS-SERVICE |
| OPS-UPGRADE | DATA-COMPAT, NFR-COMPAT, OPS-BACKUP, OPS-SERVICE |
| OPS-RECOVERY | FUNC-DIAG, FUNC-DELIVERY, DATA-INTEGRITY, SEC-PRIVACY |
| OPS-EVIDENCE | OPS-STARTUP, OPS-RETENTION, OPS-SERVICE, OPS-BACKUP, OPS-UPGRADE, OPS-RECOVERY, NFR-OBS, SEC-SANITIZE |

## 4. Critical rules preventing incoherent derivation

1. **Canonical evidence before successful completion.** The Job cannot be specified as successfully complete independently of the required canonical machine-readable transcript evidence.
2. **Source-valid recovery.** A non-empty persisted string is not by itself sufficient proof that a source can be safely requeued after restart; recoverability is source-specific and must include usable acquisition data.
3. **Retention preserves truth.** Deleting an artifact must not leave durable metadata claiming that the deleted artifact remains available.
4. **Transport does not own application policy.** Telegram may map inputs and perform protocol-level send mechanics; queue policy, use-case decisions, search/history rules, derived workflows and lifecycle semantics are application responsibilities.
5. **Runtime/provider details stay out of pure domain.** CUDA/CTranslate2/VRAM/model-path existence are runtime/provider concerns.
6. **Diarization is not an ASR footnote.** It has its own capability contract, fallback semantics, provenance and credential boundary.
7. **Operational I/O is still external I/O.** Application code does not gain permission to own filesystem/network/log mechanisms merely by using Python stdlib instead of importing `infrastructure`.
8. **Primary vs derived delivery failure differs.** A failure to deliver a newly completed primary transcript drives the primary Job to `delivery_failed`; a failure to send an already-completed or derived artifact must not retroactively corrupt the original completed Job.
9. **Supply-chain trust is explicit.** Enabling executable tokenizer/model code or changing locked dependencies is a trust decision, not an ordinary configuration toggle.
10. **Operational evidence follows implemented semantics.** Rehearsals prove the baseline intended for closure, not a helper script or an obsolete revision.

11. **Automatic retention is not cache cleanup.** `SS-002`/`OPS-RETENTION` cover the configured FIFO cleanup of volatile completed-Job artifacts. Reconstructible model/tokenizer cache deletion remains the operator-initiated `UC-012`/`FUNC-MAINT` concern even though `DATA-RETENTION` defines lifecycle classifications across data classes.

## 5. Hardening lanes

```text
Lane A — Domain/data truth
DOMAIN-* -> DATA-JOB/MEDIA/TRANSCRIPT/MARKDOWN -> DATA-INTEGRITY -> DATA-COMPAT/RETENTION/BACKUP

Lane B — Architectural reconvergence
ARCH-BOUNDARY -> ARCH-PORTS/APP/CONFIG -> TRANSPORT/EXECUTION/RUNTIME -> ASR/DIAR/TRANSCRIPT/PERSIST/TEXTGEN/OPS -> COMPOSITION

Lane C — Current behavior preservation
FUNC-SOURCE/PROCESS/DELIVERY/CONTROL -> HISTORY/SEARCH/EDIT -> SUMMARY/EXPORT/VIDEO -> DIAG/MAINT/INTERFACE

Lane D — Security and operations
SEC-* constrains A/B/C from the start; OPS-* follows stable semantics and produces OPS-EVIDENCE
```
