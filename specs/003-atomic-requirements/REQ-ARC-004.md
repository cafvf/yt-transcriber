# REQ-ARC-004 — Runtime and hardware policy outside pure domain

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-RUNTIME**
Behavior/spec sources: **ARCHITECTURE §9.1, Constitution IV**
Dependencies: **REQ-ARC-001, REQ-DOM-005**

## Normative requirement

Hardware detection and runtime/model/compute selection policy SHALL remain outside pure domain objects and SHALL be expressed as application/runtime policy whose selected facts can be recorded in run provenance.

## Acceptance criteria

- AC-01: Domain value objects do not query filesystem, CUDA, VRAM or installed-model state.
- AC-02: Application/runtime policy can select an execution profile from configuration plus detected hardware capability.
- AC-03: Concrete ML adapters translate the selected application/runtime profile into provider-specific device/compute/model options.
- AC-04: Known selected runtime/model facts are available to run provenance.

## Required evidence

- domain-purity architecture tests
- runtime-selection unit tests
- provenance tests

## Brownfield deviation addressed

`ModelName` and related runtime concepts currently mix domain identity with filesystem/VRAM/provider policy.

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
