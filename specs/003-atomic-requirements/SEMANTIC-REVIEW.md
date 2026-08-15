# Semantic Review of Atomic Requirements

Review date: **2026-08-15**
Reviewed input: **003-atomic-requirements v0.1.0-draft (57 REQs)**
Approved output: **003-atomic-requirements v1.0.0 (66 REQs, Approved / Frozen)**
Reference implementation HEAD: **618a2924d65b6cbb4dfa8b28836877b93988abf1**

## Gate criteria

Every draft REQ and DD was checked for:

- necessity within the frozen current-product baseline;
- one coherent normative obligation rather than unrelated merged behavior;
- observable/testable acceptance criteria;
- compatibility with the Constitution and approved `000-baseline` specifications;
- consistency with frozen use cases/system/operational scenarios;
- explicit treatment of known brownfield deviations without normalizing defects;
- absence of future semantic-search/translation/alternative-ASR/checkpoint/multi-user scope;
- avoidance of premature implementation choices where a capability-level contract is sufficient.

## Result

**PASS after correction.** The draft was not approved unchanged.

- original REQs reviewed: **57**
- passed without semantic split: **21**
- revised for wording/observability/dependency precision: **27**
- over-broad REQs split into independent obligations: **9**
- new REQs created by those splits: **9**
- approved atomic REQs: **66**
- approved derivation decisions: **DD-001..DD-007**

## Required splits

| Draft REQ | Approved decomposition | Reason |
|---|---|---|
| REQ-SEC-002 | REQ-SEC-002 + REQ-SEC-008 | Secret storage/rotation/least-privilege is operational security; preventing secrets from crossing domain/application ports is an architectural boundary. They can fail independently. |
| REQ-SEC-005 | REQ-SEC-005 + REQ-SEC-009 | Untrusted-input containment and disclosure to configured external services are distinct threat/control surfaces. |
| REQ-DATA-002 | REQ-DATA-002 + REQ-DATA-010 | Temporary/staged media lifecycle applies to rejection/cancellation/restart; completed-Job retention is a different policy and scenario. |
| REQ-DATA-005 | REQ-DATA-005 + REQ-DATA-011 | Derived artifact association and textual-search index lifecycle have distinct storage/update contracts. |
| REQ-ARC-001 | REQ-ARC-001 + REQ-ARC-012 | Mechanical dependency direction and the quality/shape of application ports are independently testable architectural obligations. |
| REQ-ARC-004 | REQ-ARC-004 + REQ-ARC-013 | Runtime/hardware selection and the backend-neutral ASR contract are independent seams and had distinct brownfield defects. |
| REQ-NFR-002 | REQ-NFR-002 + REQ-NFR-007 | Finite/bounded resource consumption and non-blocking Telegram event-loop behavior are distinct quality properties. |
| REQ-FUNC-005 | REQ-FUNC-005 + REQ-FUNC-013 | Frozen UC-004 history browse/retrieve and UC-005 textual search were intentionally separate; merging them reintroduced a rejected abstraction. |
| REQ-FUNC-008 | REQ-FUNC-008 + REQ-FUNC-014 | Frozen UC-008 transcript export and UC-009 YouTube video derivative have different dependencies and failure modes. |

## Important semantic corrections

### Telegram audience

`DD-004` and `REQ-SEC-001` keep the hardened **private-chat-only** baseline, but no longer prescribe silence as the only behavior for the authorized operator in a group. Security requires refusal before private lookup/work/state mutation; the transport may ignore the request or return neutral guidance. Unauthorized users remain silently ignored according to the frozen behavior.

### Language truth

`DD-005`, `REQ-DOM-003`, `REQ-ARC-013`, and `REQ-FUNC-002` distinguish three different facts: operator-requested/forced language, independently observed language, and confidence. Forced `/pt` or `/en` remains an approved processing constraint, but it cannot relabel a conflicting independent observation or borrow its confidence.

### Duration truth

`DD-006`, `REQ-DATA-002`, `REQ-NFR-002`, and `REQ-FUNC-002` require unknown duration to remain unknown until a bounded source-appropriate probe establishes it. Synthetic zero is not a valid substitute.

### Canonical completion consistency

`REQ-DATA-004` was renamed from “atomicity” to **completion consistency** to avoid prescribing a cross-filesystem/database transaction mechanism. The observable obligation is what matters: successful completion cannot be claimed when required canonical evidence failed, and persisted availability references must remain truthful.

### Filesystem containment

`REQ-SEC-007` replaces the non-verifiable phrase “symlink behavior is considered” with a concrete invariant: destructive operations resolve/validate targets and refuse symlink/resolved paths escaping the approved root.

### Processing fingerprint

`REQ-DOM-005` now distinguishes the request-time policy fingerprint from actual run provenance. The fingerprint may include configured fallback policy that could affect a request, while actual subtitle/ASR/backend/runtime/fallback facts are recorded separately when known.

### Search and derived artifacts

`REQ-DATA-005` now covers derived artifacts only; `REQ-DATA-011` owns textual-index lifecycle. This removes the current hidden-indexing side-effect from the conceptual lifecycle repository contract.

### Runtime versus ASR

`REQ-ARC-004` now owns hardware/runtime policy outside pure domain; `REQ-ARC-013` separately defines the backend-neutral ASR contract. This prevents a future backend from inheriting WhisperX/CTranslate2-shaped parameters merely because the current adapter uses them.

### Resource bounds versus async responsiveness

`REQ-NFR-002` owns finite limits/timeouts/storage budgets; `REQ-NFR-007` separately requires long synchronous work not to monopolize the Telegram event loop.

## Derivation decisions disposition

| Decision | Result | Note |
|---|---|---|
| DD-001 | PASS | Purpose-specific canonical transcript store/renderer contracts remain necessary and non-generic. |
| DD-002 | PASS | Secret-file permission verification remains host/deployment evidence rather than mandatory `/healthcheck` discovery. |
| DD-003 | PASS | External compatibility remains frozen while internal taxonomy may be corrected. |
| DD-004 | REVISED / APPROVED | Private-chat-only remains; authorized-group refusal may be silent or neutral, but never disclose private state/content. |
| DD-005 | REVISED / APPROVED | Forced/requested language, independent observation, and confidence are explicitly separated. |
| DD-006 | REVISED / APPROVED | Unknown duration must be resolved by a bounded source-appropriate probe or rejected before expensive processing. |
| DD-007 | PASS | Telegram routing remains application persistence context, not pure Job identity. |

## Original-REQ disposition

| Draft REQ | Disposition |
|---|---|
| REQ-SEC-001 | REVISED |
| REQ-SEC-002 | SPLIT → REQ-SEC-002, REQ-SEC-008 |
| REQ-SEC-003 | REVISED |
| REQ-SEC-004 | PASS |
| REQ-SEC-005 | SPLIT → REQ-SEC-005, REQ-SEC-009 |
| REQ-SEC-006 | REVISED |
| REQ-SEC-007 | REVISED |
| REQ-DOM-001 | PASS |
| REQ-DOM-002 | PASS |
| REQ-DOM-003 | REVISED |
| REQ-DOM-004 | REVISED |
| REQ-DOM-005 | REVISED |
| REQ-DATA-001 | PASS |
| REQ-DATA-002 | SPLIT → REQ-DATA-002, REQ-DATA-010 |
| REQ-DATA-003 | PASS |
| REQ-DATA-004 | REVISED |
| REQ-DATA-005 | SPLIT → REQ-DATA-005, REQ-DATA-011 |
| REQ-DATA-006 | REVISED |
| REQ-DATA-007 | PASS |
| REQ-DATA-008 | PASS |
| REQ-DATA-009 | REVISED |
| REQ-ARC-001 | SPLIT → REQ-ARC-001, REQ-ARC-012 |
| REQ-ARC-002 | REVISED |
| REQ-ARC-003 | REVISED |
| REQ-ARC-004 | SPLIT → REQ-ARC-004, REQ-ARC-013 |
| REQ-ARC-005 | REVISED |
| REQ-ARC-006 | PASS |
| REQ-ARC-007 | REVISED |
| REQ-ARC-008 | REVISED |
| REQ-ARC-009 | REVISED |
| REQ-ARC-010 | REVISED |
| REQ-ARC-011 | REVISED |
| REQ-NFR-001 | PASS |
| REQ-NFR-002 | SPLIT → REQ-NFR-002, REQ-NFR-007 |
| REQ-NFR-003 | PASS |
| REQ-NFR-004 | REVISED |
| REQ-NFR-005 | PASS |
| REQ-NFR-006 | REVISED |
| REQ-FUNC-001 | REVISED |
| REQ-FUNC-002 | REVISED |
| REQ-FUNC-003 | PASS |
| REQ-FUNC-004 | PASS |
| REQ-FUNC-005 | SPLIT → REQ-FUNC-005, REQ-FUNC-013 |
| REQ-FUNC-006 | PASS |
| REQ-FUNC-007 | REVISED |
| REQ-FUNC-008 | SPLIT → REQ-FUNC-008, REQ-FUNC-014 |
| REQ-FUNC-009 | PASS |
| REQ-FUNC-010 | REVISED |
| REQ-FUNC-011 | PASS |
| REQ-FUNC-012 | REVISED |
| REQ-OPS-001 | PASS |
| REQ-OPS-002 | REVISED |
| REQ-OPS-003 | REVISED |
| REQ-OPS-004 | PASS |
| REQ-OPS-005 | PASS |
| REQ-OPS-006 | PASS |
| REQ-OPS-007 | PASS |

## Approval conclusion

No unresolved semantic contradiction remains among the Constitution, approved baseline specifications, frozen behavior model, frozen 66-family tree, and the corrected atomic requirements.

Approval of this package authorizes **planning** against these REQs. It does not by itself authorize arbitrary productive refactoring: implementation still follows `PLAN → TASKS → RED test → GREEN → REFACTOR → CONFORMANCE`, and behavior may change only where an approved REQ explicitly classifies the current brownfield behavior as a defect/hardening target.
