# 007 — Production Coherence & Distribution

Version: **1.0.0**
Status: **CLOSED — PASS WITH RESERVATION**
Approved direction: **2026-08-19**
Prerequisite: **PLAN-006 closure / stabilized private single-operator baseline**
Baseline revision: **6f77d24f2c82d4748fd777056325f629c6fdf27a**

## Purpose

This post-baseline phase converges the existing implementation into a coherent, distributable,
self-hosted, single-operator product without rewriting the frozen historical baseline.

It does not add unrelated product functionality. It makes the existing product semantically
unambiguous, safely configurable, installable by another operator and releasable through a
reproducible quality gate.

## Governing compatibility principle

A legacy or compatibility behavior may remain only when all are true:

1. a concrete backward-compatibility need is identified;
2. the legacy input/state is documented;
3. automated evidence proves the compatibility path;
4. the legacy concept is isolated at an explicit boundary;
5. new code uses only the canonical concept;
6. removal condition and target version/window are documented.

Compatibility without evidence SHALL be removed before release.

## Work packages

- **P07-A — Canonical taxonomy**
- **P07-B — Error contract and architectural boundaries**
- **P07-C — Configuration, packaging and distribution**
- **P07-D — Documentation and onboarding**
- **P07-E — Release gate**

Required order:

```text
taxonomy
  ↓
typed application contracts
  ↓
errors + I/O boundaries
  ↓
configuration + packaging
  ↓
README/operator documentation
  ↓
full release gate
```

## Product boundary

Target remains self-hosted, private and single-operator, with Telegram as the primary UI and local
transcription/diarization. This phase SHALL NOT silently redesign the bot as a public multi-user
service.

## Non-goals

Translation, new backend functionality, Obsidian notes, statistics, checkpoint resume and public
multi-user operation remain outside PLAN-007.
