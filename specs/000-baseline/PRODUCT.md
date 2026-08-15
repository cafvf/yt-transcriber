# Baseline Product Specification

Version: **1.0.0**
Status: **Approved**
Baseline date: **2026-08-15**
Milestone: **Architecture & Specification Baseline**

## 1. Product identity

YT Transcriber is a private, local-first, single-operator application for acquiring media, transcribing spoken content, diarizing speakers, preserving auditable transcript artifacts, querying local history, and generating selected derived artifacts.

Telegram is the primary interaction surface in the current product. YouTube is one supported media source, not the identity of the entire domain.

The current product is not a public SaaS, multi-user platform, generic media hosting service, or public API.

## 2. Primary user

The baseline supports one explicitly authorized Telegram user.

Messages from other users are outside the supported product contract. The security posture treats unauthorized interaction conservatively and avoids exposing private system behavior.

## 3. Supported input classes

### YouTube reference

A supported YouTube reference may resolve source identity/metadata, apply duration constraints, use suitable YouTube subtitles when available, or otherwise acquire audio and enter the common transcription pipeline.

### Private Telegram audio

The current system accepts supported Telegram audio, voice, and audio documents from the authorized user.

The input is validated and staged locally. It does not receive a synthetic YouTube identity.

## 4. Common processing outcome

For supported media, the system aims to produce a canonical transcript representation and human-readable Markdown.

The path may include acquisition, conversion, runtime/model selection, ASR, diarization, rendering, local persistence, and delivery. Source-specific shortcuts may omit unnecessary stages.

## 5. Current capability groups

The baseline includes:

- submission and queue/status interaction;
- cancellation;
- transcription from YouTube and Telegram audio;
- transcript history;
- speaker rename support;
- textual history search;
- transcript export;
- local summarization through an OpenAI-compatible backend;
- YouTube subtitle/video derivative export where supported;
- health diagnostics;
- last-error diagnostics;
- cache/retention operations;
- restart reconciliation for defined job states.

Detailed use-case flows are deferred until this baseline is approved.

## 6. Canonical versus derived outputs

Human-readable transcript Markdown and persisted transcript segment snapshots are primary transcript artifacts in the current system.

Exports, summaries, indexes, and video subtitle derivatives are derived products. They must not silently overwrite canonical transcript representation.

## 7. Processing model

The baseline processes one queued transcription job at a time.

The queue is in memory, while sufficient job state is persisted to support current restart reconciliation semantics.

The baseline does not promise checkpoint-level resume within download, ASR, alignment, diarization, rendering, or other expensive stages.

## 8. Scope lock for this milestone

Allowed:

- specification and characterization;
- correction of architectural violations;
- domain/taxonomy correction;
- decomposition/refactoring;
- contract/architecture/conformance/regression tests;
- documentation reconciliation;
- operational evidence;
- preservation of externally visible behavior unless a specification explicitly changes it.

Not allowed:

- semantic search;
- new ASR backends;
- expanded multilingual behavior;
- translation;
- advanced selective `/redo`;
- Obsidian/Notion integration;
- statistics as a new product feature;
- checkpoint-level resume;
- unrelated commands/integrations.

## 9. Out of scope for the current baseline

No current guarantee exists for public service operation, multiple users/tenants, external API clients, batch submission, semantic retrieval, translation, general-purpose multilingual backend selection, checkpoint resume, automatic cross-host synchronization, cloud backup, or generic knowledge-base publishing.

## 10. Baseline evidence

As of 2026-08-15:

- Ruff lint passed;
- Ruff format check passed;
- mypy passed;
- 703 selected pytest tests passed;
- 46 tests were deselected by configured markers;
- global branch-aware coverage was 79%;
- local secret scanner passed;
- Gitleaks passed;
- `git diff --check` passed.

These results demonstrate a stable executable baseline but do not prove architectural correctness or completion of real-host operational rehearsals.

## 11. Product naming direction

The repository/product name may remain `yt-transcriber` for continuity.

Internal terminology should distinguish generic media concepts from source-specific YouTube and transport-specific Telegram concepts.
