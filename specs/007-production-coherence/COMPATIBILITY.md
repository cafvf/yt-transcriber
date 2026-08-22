# Compatibility and Deprecation Policy

Version: **1.0.0**
Status: **Normative for PLAN-007**

Backward compatibility is an exception, not a default design constraint. Existing code is not proof
of a compatibility requirement.

Every retained item SHALL record: legacy surface, canonical replacement, real compatibility need,
automated evidence, translation boundary, new-code rule, deprecation status, removal condition and
target version/window.

## COMPAT-001 — persisted Job status `downloading`
- Canonical: `JobStatus.ACQUIRING` / `acquiring`.
- Need: old databases may contain `downloading`.
- Boundary: persisted-status decoder.
- Evidence: fixture/test loading the old state and obtaining `ACQUIRING`.
- New-code rule: never persist/emit `downloading`.
- Removal: only after a documented migration guarantees supported databases no longer contain it.
- Target: post-1.x data-migration review, not earlier than one migration cycle.

## COMPAT-002 — legacy snapshot/schema readers
- Canonical: current snapshot/schema.
- Need: durable history/artifacts.
- Boundary: persistence/import reader.
- Evidence: frozen legacy fixtures.
- New-code rule: writers emit only current representation.
- Removal: only under an explicit versioned schema-support policy.

## COMPAT-003 — legacy DB column names
- Examples: physical `video_id`, `source_url`, `config_signature` where existing DBs depend on them.
- Canonical: source-neutral/domain terminology in application code.
- Boundary: persistence mapper.
- Evidence: integration tests against supported existing schema.
- New-code rule: physical column names do not define domain vocabulary.
- Removal: at the next justified versioned schema migration, not a cosmetic rename-only migration.

## COMPAT-004 — `MAX_VIDEO_DURATION_MIN`
- Canonical: internal `max_media_duration_min`.
- Need: existing operator configs may use the legacy env name.
- Boundary: config loader.
- Evidence: deterministic parsing/precedence test.
- New-code rule: application consumes only source-neutral settings.
- Removal: after at least one documented deprecation cycle and no required deployment fixture relies
  solely on the old name.

## Not presumed compatible
Do not retain these without new evidence:
- `used_alternate_track` as canonical state;
- `audio_track_was_dubbed` for original-track selection;
- `VideoMetadata` throughout new internal consumers;
- raw string language state where typed VOs apply;
- `config_signature` as canonical application/domain terminology.

## COMPAT-005 — legacy operational-error JSONL
- Canonical: `code`, `category`, `retryable`, `safe_message`, `technical_context`.
- Need: existing `/lasterror` history may contain pre-Gate-B JSONL records with `message`, `context` and `error_type`.
- Boundary: `JsonlOperationalErrorStore` reader only.
- Evidence: frozen legacy JSONL compatibility test plus canonical-writer test.
- New-code rule: writers never emit legacy keys and application behavior never branches on provider exception names.
- Removal: after the supported operational-error retention window guarantees pre-Gate-B records have expired.
- Target: first post-1.x retention-policy review after that window.
