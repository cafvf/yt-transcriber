# REQ-ARC-006 — Canonical transcript store and renderer contracts

Version: **1.0.0**
Status: **Approved / Frozen**
Wave: **B**
Derived families: **ARCH-TRANSCRIPT**
Behavior/spec sources: **DD-001, UC-004..UC-009**
Dependencies: **REQ-ARC-012, REQ-DATA-003, REQ-DATA-004**

## Normative requirement

Application transcript-consuming workflows SHALL depend on explicit canonical transcript store and rendering capabilities rather than concrete filesystem snapshot/Markdown renderer classes or filename conventions.

## Acceptance criteria

- AC-01: Canonical transcript store supports durable save/load by explicit canonical transcript reference and version-aware decoding.
- AC-02: Renderer consumes structured transcript evidence plus aliases/provenance and returns Markdown content without owning storage.
- AC-03: Rename, summary, export and history workflows do not import the concrete filesystem snapshot repository.
- AC-04: Missing/corrupt structured evidence is surfaced explicitly to the application workflow.

## Required evidence

- port contract tests
- architecture import tests
- workflow tests with fake/in-memory store

## Scope guard

This requirement repairs or preserves the approved current baseline. It does not authorize semantic search, translation, an alternative ASR product feature, checkpoint resume, multi-user behavior, or knowledge-system integration.
