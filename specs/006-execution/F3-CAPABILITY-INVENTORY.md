# F3 — Application capability inventory

Status: **Updated through TASK-P03-012 — dependency direction closed; REQ-ARC-012 remains open**
Date: **2026-08-16**
Plan: **PLAN-003 — Hexagonal boundaries and provider seams**
Primary support: **REQ-ARC-012**

## Purpose

This inventory records the current application-facing capability/data-contract
surfaces after the PLAN-003 capability migrations through TASK-P03-012. It is a
migration guardrail, not permission to create speculative abstractions.

A new file under `application/ports/` must correspond to a demonstrated approved
capability and must be added deliberately to the executable inventory. Provider
API shapes, provider credentials and generic filesystem escape hatches are not
valid reasons to create a port.

## Current inventory

| Module | Current role | Classification | PLAN-003 disposition |
|---|---|---|---|
| `audio_converter.py` | Convert/split audio needed by approved workflows | Purpose-specific capability | Keep; no provider-specific API surface |
| `canonical_transcript.py` | Save/load structured canonical transcript evidence by explicit reference | Purpose-specific repository/data contract | Established by P03-009; keep |
| `diarization_engine.py` | Speaker diarization | Purpose-specific capability | Provider-neutral contract established by P03-008 |
| `gpu_detector.py` | Detect hardware capability for runtime selection | Purpose-specific capability | Runtime/hardware policy separated by P03-004 |
| `history_search.py` | Search/refresh persisted textual history | Purpose-specific repository capability | Keep while approved history behavior exists |
| `incoming_media.py` | Source-neutral inbound media description | Application data contract | Keep; workflow ownership changes belong to F4 |
| `job_repository.py` | Persist/query jobs and request context | Purpose-specific repository capability | Keep |
| `transcript_renderer.py` | Render structured transcript evidence to Markdown | Purpose-specific rendering capability | Established by P03-009; rendering owns no storage |
| `transcription_engine.py` | Speech-to-text / ASR | Purpose-specific capability | Backend-neutral contract established by P03-007 |
| `youtube_downloader.py` | YouTube-specific acquisition/subtitle capability | Approved source-specific capability | Keep provider implementation behind the port |

`__init__.py` is package scaffolding and is not a capability.

## Conventions

Application-owned ports SHALL:

1. live under `yt_transcriber_bot.application.ports`;
2. depend only on stdlib plus application/domain concepts;
3. not import infrastructure, composition, provider SDKs or persistence/ML
   implementations;
4. not transport provider credentials;
5. describe the capability needed by an approved workflow rather than a generic
   provider API or generic filesystem surface;
6. be implementable by a test double without importing infrastructure.

## Generic filesystem cleanup

TASK-P03-011 retired the temporary generic filesystem exception after repository
and runtime reference evidence showed no approved consumer requiring it.

The following obsolete surface was removed together:

- `application/ports/file_storage.py`;
- the concrete `LocalFileStorage` filesystem adapter;
- composition construction/exposure of `file_storage`;
- the 11 integration tests dedicated only to that abstraction;
- the temporary `file_storage.py` entry in the executable port inventory.

No renamed replacement such as `Storage`, `Filesystem`, `FileSystem`,
`BlobStore`, `GenericStorage` or equivalent was introduced.

Purpose-specific storage/persistence capabilities remain explicit, including
canonical transcript persistence and job/history repositories. P03-011 is
support/convergence evidence for `REQ-ARC-012`; it does not close that
requirement.

## PLAN-003 capability evolution

Completed capability work reflected by this inventory:

- backend-neutral ASR contract — P03-007;
- provider-neutral diarization contract, fallback and provenance — P03-008;
- canonical transcript store and renderer contracts — P03-009;
- obsolete generic `FileStorage` retirement — P03-011;
- mechanically enforced zero-violation dependency direction — P03-012.

TASK-P03-012 closed `REQ-ARC-001` and removed the legacy dependency-exception
manifest. TASK-P03-013 is now the closure owner for `REQ-ARC-012`.

This document does not authorize future product capabilities such as translation,
semantic search, alternate ASR product behavior, Obsidian integration,
statistics or checkpoint resume.

## Executable evidence

`tests/conformance/test_application_port_conventions.py` verifies that:

- the port module inventory does not drift silently;
- application ports do not import concrete/provider packages;
- generic storage port modules are forbidden after TASK-P03-011;
- the retired `FileStorage` / `LocalFileStorage` runtime surface does not
  reappear.

The provider-credential rule remains independently enforced by
`tests/conformance/test_provider_secret_boundary.py`.

`tests/conformance/test_hexagonal_dependencies.py` independently verifies that:

- the domain/application forbidden dependency set is exactly empty;
- no legacy dependency-exception manifest is required;
- representative forbidden imports are detected;
- direct application stdlib-I/O hotspots cannot appear without an explicit
  frozen purpose-specific requirement/task owner.

This I/O governance is not permission to retain generic filesystem capability
surfaces. `REQ-ARC-012` remains open until TASK-P03-013 verifies the complete
purpose-specific application-owned port boundary.
