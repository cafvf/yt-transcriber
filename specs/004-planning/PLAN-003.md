# PLAN-003 — Hexagonal boundaries and provider seams

Version: **1.0.0**
Status: **Approved / Frozen**
Derived from: **003-atomic-requirements v1.0.0**
Prerequisite plans: **PLAN-002** *(PLAN-001 inherited through the approved PLAN-002 gate)*
Approved: **2026-08-15**

## Goal

Restore enforceable hexagonal dependency direction and provider seams without changing frozen product behavior: purpose-specific ports, pure runtime/domain separation, backend-neutral ASR/diarization, canonical transcript capabilities, truthful configuration ownership, edge-only credentials, external-service disclosure boundaries and composition-root control.

This plan establishes **boundaries and seams**. It does not yet move all portable workflows out of Telegram or split every infrastructure responsibility; PLAN-004 consumes these seams for that decomposition.

## Primary requirement scope

- `REQ-SEC-008` — Provider-secret architectural boundary
- `REQ-SEC-009` — External-service disclosure boundary
- `REQ-ARC-001` — Mechanically enforced dependency direction
- `REQ-ARC-004` — Runtime and hardware policy outside pure domain
- `REQ-ARC-005` — Diarization capability, fallback and credential isolation
- `REQ-ARC-006` — Canonical transcript store and renderer contracts
- `REQ-ARC-010` — Truthful configuration taxonomy and external compatibility
- `REQ-ARC-011` — Composition-root ownership of concrete providers and credentials
- `REQ-ARC-012` — Purpose-specific application-owned ports
- `REQ-ARC-013` — Backend-neutral ASR contract

## Implementation approach

1. Introduce a default-gate architecture check with a temporary explicit list of known violations; ratchet that list to zero by plan exit rather than accepting new violations.
2. Define only purpose-specific application capabilities required by approved workflows; avoid a replacement generic filesystem abstraction.
3. Move provider-secret resolution to composition/infrastructure and remove `hf_token`/equivalent provider credentials from application-port signatures.
4. Move filesystem/CUDA/VRAM/provider model-path policy out of pure domain and keep selected runtime facts available to provenance.
5. Replace WhisperX/CTranslate2-shaped ASR application parameters with a backend-neutral request/result seam while preserving current WhisperX behavior through the adapter.
6. Give diarization its own provider-neutral contract with explicit current fallback/error/provenance semantics and adapter-owned authentication.
7. Introduce canonical transcript store/renderer capabilities and migrate application imports away from concrete snapshot/renderer infrastructure classes.
8. Reorganize internal configuration by truthful concern while preserving operator env compatibility and the single fingerprint authority established in PLAN-002.
9. Make the composition root the owner of concrete provider selection, credentials and trusted external endpoints; external-service calls receive only data required by the approved operation.
10. Remove unused speculative/generic abstractions only after replacement capability coverage is proven.

## Ownership boundary and handoff

PLAN-003 owns **architectural seams and dependency enforcement**, not workflow ownership. It hands off:

- use-case/application orchestration and Telegram slimming to PLAN-004;
- functional equivalence/acceptance over the new seams to PLAN-005;
- environment/host verification of concrete adapters and secrets to PLAN-006.

PLAN-004 must consume ports created here instead of introducing alternate provider-specific or generic I/O seams.

## Migration and compatibility constraints

- Do not add an alternative ASR backend; only make the current contract capable of hosting one later.
- Do not introduce translation semantics into text-generation or language contracts.
- Do not leave a permanent architecture-test allowlist at plan exit.
- Do not move business workflows into composition while removing infrastructure imports.

## Exit gate

- Domain/application dependency rules pass in the default gate with no legacy exception list.
- Application ports carry no provider credentials.
- Trusted external endpoints/provider selection remain composition/config owned.
- ASR and diarization shared contract tests pass against current adapters.
- Canonical transcript consumers run with fake/in-memory capabilities.
- Composition smoke tests validate the graph without requiring real network calls.
- No generic replacement abstraction exists without an approved demonstrated capability.

## Not tasks

The numbered approach above defines migration order and design constraints, not a task checklist. Concrete files, red tests, implementation increments, commits and task ownership are defined in `../005-tasks/`.
