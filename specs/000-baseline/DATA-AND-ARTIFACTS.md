# Baseline Data and Artifacts Specification

Version: **1.0.0**
Status: **Approved**
Baseline date: **2026-08-15**

## 1. Purpose

This document defines conceptual roles of persisted state and generated artifacts before implementation-oriented requirements.

It does not freeze the current database schema as ideal design.

## 2. Data classes

The system manages:

1. job lifecycle/state;
2. source metadata and processing provenance;
3. staged/downloaded media;
4. converted audio;
5. transcript Markdown;
6. structured transcript segment snapshots;
7. derived exports;
8. summaries;
9. search/index data;
10. operational audit/error logs;
11. model/cache data;
12. backups.

These classes have different retention, sensitivity, and reproducibility roles.

## 3. Job persistence

Job persistence owns durable job identity/lifecycle and sufficient state for history, delivery, restart reconciliation, artifact association, rename persistence, source provenance, and requested language/configuration provenance.

It must not become a transport payload dump.

## 4. Canonical transcript evidence

The domain `Transcript` is the canonical logical representation of recognized speech.

For persisted evidence:

- the versioned structured transcript snapshot is the canonical machine-readable representation;
- Markdown is the canonical human-readable rendering;
- Markdown must not be parsed as the source of structured transcript truth when a structured snapshot exists;
- derived exports, summaries, search indexing, rename/re-render operations, and future transformations should consume the structured representation through an application contract rather than depend on Markdown layout.

The two persisted forms have distinct canonical roles rather than competing ownership.

## 5. Derived artifacts

Derived artifacts reference canonical evidence and should be regenerable where practical.

Current derived classes include plain text, JSON/SRT/VTT, summaries, selected YouTube video/subtitle derivatives, and text-search documents/indexes.

Derived artifacts must not silently alter/replace canonical transcript evidence.

## 6. Provenance

Outputs materially affected by processing configuration retain sufficient significant choices.

The project uses one conceptual, versioned processing fingerprint for output-affecting policy. Fingerprint identity excludes secrets and unrelated operational settings.

The fingerprint and human-readable provenance are related but not identical:

- the fingerprint answers whether two processing configurations are materially equivalent for transcript production;
- provenance records facts useful to explain how a specific artifact was produced, including actual backend/model and relevant fallback/runtime facts.

A future serialization/hash format is an implementation-plan decision as long as it is deterministic, versioned, and backward interpretable.

## 7. Search index

Search indexes are derived local private data.

Lifecycle persistence and search-index maintenance should have separate conceptual ownership even if the current implementation combines them.

## 8. Retention

Retention is explicit per data class.

The current baseline removes selected volatile media/conversion/log data from old completed jobs while preserving transcript Markdown and structured snapshots required by current history/rename/export behavior.

Future deletion must not silently break an approved capability.

## 9. Backup

A backup inherits the highest sensitivity of included content.

It requires access control, restrictive permissions, and preferably encrypted/protected storage.

Restore semantics must preserve database integrity and artifact relationships.

## 10. Compatibility and migration

Schema/artifact changes affecting existing history require an explicit compatibility decision, migration/fallback where needed, regression tests using representative data, and operator guidance when manual action is required.

Silent destructive migration is prohibited.

## 10.1 Snapshot schema evolution

Existing snapshot schema version 1 is part of the brownfield compatibility baseline and must remain readable throughout architectural cleanup.

If a later snapshot schema version is introduced during this milestone:

- new writes must include an explicit schema version;
- old v1 snapshots must remain readable through compatibility decoding or a tested migration path;
- missing future provenance fields in historical snapshots are represented as unknown/not-recorded rather than fabricated;
- migration must preserve transcript segments, timestamps, speaker labels, source metadata, and the ability to re-render current human-readable Markdown;
- destructive in-place migration without rollback/backup evidence is prohibited.

## 11. Requirement-derivation notes

The exact application contracts for loading/saving canonical transcript evidence will be derived with the use cases and atomic requirements.

The current generic `FileStorage` abstraction is not part of the approved target architecture unless a real application capability requiring it is demonstrated. Baseline cleanup should remove the unused generic port/adapter/composition exposure rather than preserve speculative structure.

Lifecycle persistence and history/search indexing have separate conceptual ownership even if one concrete adapter temporarily implements both interfaces.
