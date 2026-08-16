# F3 — Application capability inventory

Status: **TASK-P03-003 implemented / local gate pending**
Date: **2026-08-15**
Plan: **PLAN-003 — Hexagonal boundaries and provider seams**
Primary support: **REQ-ARC-012**

## Purpose

This inventory records the application-facing capability/data-contract surfaces
that exist at the start of PLAN-003. It is a migration guardrail, not permission
to create speculative abstractions.

A new file under `application/ports/` must correspond to a demonstrated approved
capability and must be added deliberately to the executable inventory. Provider
API shapes, provider credentials and generic filesystem escape hatches are not
valid reasons to create a port.

## Current inventory

| Module | Current role | Classification | PLAN-003 disposition |
|---|---|---|---|
| `audio_converter.py` | Convert/split audio needed by approved workflows | Purpose-specific capability | Keep; no provider-specific API surface |
| `diarization_engine.py` | Speaker diarization | Purpose-specific capability | P03-008 makes the contract fully provider-neutral |
| `file_storage.py` | Generic filesystem CRUD/listing | **Known temporary generic exception** | Remove in P03-011 after replacement/no-consumer evidence |
| `gpu_detector.py` | Detect hardware capability for runtime selection | Purpose-specific capability | P03-004 separates hardware/runtime policy cleanly |
| `history_search.py` | Search/refresh persisted textual history | Purpose-specific repository capability | Keep while approved history behavior exists |
| `incoming_media.py` | Source-neutral inbound media description | Application data contract | Keep; workflow ownership changes belong to F4 |
| `job_repository.py` | Persist/query jobs and request context | Purpose-specific repository capability | Keep |
| `transcription_engine.py` | Speech-to-text / ASR | Purpose-specific capability | P03-007 replaces backend-shaped parameters |
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

## Generic filesystem exception

`file_storage.py` is the only permitted generic storage abstraction during the
PLAN-003 migration. It is not endorsed as a target architecture.

Its removal is owned by **TASK-P03-011** after P03-009 establishes the canonical
transcript capabilities and reference evidence proves there is no approved
runtime consumer requiring generic `FileStorage`.

No renamed replacement such as `Storage`, `Filesystem`, `FileSystem`,
`BlobStore`, `GenericStorage` or equivalent may be introduced to evade that
cleanup.

## Planned capability additions

PLAN-003 may add only capabilities already frozen by the plan, principally:

- backend-neutral ASR contract refinements — P03-007;
- provider-neutral diarization contract refinements — P03-008;
- canonical transcript store and renderer contracts — P03-009.

This document does not authorize future product capabilities such as translation,
semantic search, alternate ASR product behavior, Obsidian integration,
statistics or checkpoint resume.

## Executable evidence

`tests/conformance/test_application_port_conventions.py` verifies that:

- the port module inventory does not drift silently;
- application ports do not import concrete/provider packages;
- `FileStorage` is the single known generic filesystem exception;
- no additional generic storage abstraction appears.

The provider-credential rule remains independently enforced by
`tests/conformance/test_provider_secret_boundary.py`.
