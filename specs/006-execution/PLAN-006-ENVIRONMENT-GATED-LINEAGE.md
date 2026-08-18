# PLAN-006 — Environment-Gated Test Lineage

Status: **Round A executable evidence contract**
Frozen inventory source: `specs/002-requirements/EVIDENCE-INVENTORY.md`
F0 baseline evidence: `specs/006-execution/F0-BASELINE.md`
Frozen baseline revision: `5266d01b660398d0ff25c1bff01eb287114f0d7d`

## Baseline provenance

F0 ties the `749 collected / 703 selected / 46 deselected` inventory to the
approved baseline revision above. The frozen groups reconstruct as:

```text
25  SQLAlchemy/SQLite Job repository
 4  history-search persistence/index behavior
11  obsolete LocalFileStorage abstraction
 3  real ffmpeg/ffprobe integration
 3  file-backed startup recovery
--
46
```

## Lineage discovered during Round A

Three distinct transformations occurred after the baseline.

### History search

The four historical history-search tests mixed persistence, index refresh,
search behavior and workflow ownership. After the decomposition at `0e2bb0a`,
three SQLite integration contracts remain and rebuild/current-history ownership
is separately tested in `TextSearchWorkflow`.

### LocalFileStorage

The 11 tests belonged to the generic `LocalFileStorage` abstraction which the
frozen evidence inventory explicitly permitted to retire with the non-target
abstraction. Removal occurred at `c666305`, with purpose-specific filesystem
contracts retained elsewhere.

### Real ffprobe portability evidence

One of the three historical `TestFfmpegRealIntegration` tests,
`test_real_probe_duration`, disappeared when `split_for_telegram()` left
`FfmpegAudioConverter`. Unlike `LocalFileStorage`, the frozen inventory says the
three ffmpeg/ffprobe behaviors are durable evidence for processing, media,
architecture ports and portability.

Round A therefore restores that evidence at its current architectural owner:
`FfprobeAudioDurationInspector`. The replacement integration test creates a real
WAV with ffmpeg and obtains its duration through the real ffprobe subprocess.

The resulting frozen lineage is:

```text
46 = 30 + 4 + 1 + 11
     |    |   |    |
     |    |   |    +-- RETIRED_WITH_ABSTRACTION
     |    |   +------- REPLACED_BY_PORTABILITY_CONTRACT
     |    +----------- REPLACED_BY_DECOMPOSITION
     +---------------- PRESERVED historical nodeids
```

`MISSING` must be zero.

## Current integration inventory after restoration

The current marker-selected integration inventory becomes **35**:

- 30 preserved historical nodeids;
- 3 current SQLite history-search contracts;
- 1 post-baseline JobRepository canonical-reference migration contract;
- 1 restored real ffprobe portability contract.

The new count is not test-count inflation for its own sake. It repairs a durable
evidence role whose disappearance the frozen inventory did not authorize.

## Evidence semantics

Collection alone is never execution evidence. The Round A gate validates frozen
provenance before applying changes, executes replacement evidence explicitly,
runs the complete integration selection with JUnit accounting, rejects skips as
execution PASS for the current supported environment, and only then emits the
final lineage.

Historical nodeids that were replaced remain `NOT_EXECUTED`; their current
replacement evidence is recorded separately as PASS. Historical
`LocalFileStorage` nodeids remain explicitly retired rather than recreated.
