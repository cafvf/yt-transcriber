# Environment-Gated Test Evidence Inventory

Version: **1.0.0**
Inventory date: **2026-08-15**
Baseline: **749 collected / 703 selected and passed / 46 deselected**

`pyproject.toml` excludes `integration`, `slow`, and `e2e` markers from the default test selection. The full current set of 46 deselected tests has been identified. All 46 are `integration` tests; no additional current test is excluded solely by `slow` or `e2e`.

| Test group | Count | Why gated | Requirement evidence disposition |
|---|---:|---|---|
| `tests/unit/infrastructure/persistence/test_job_repository.py` | 25 | Real SQLAlchemy/SQLite semantics, migrations, restart payload persistence | Preserve as integration evidence for DATA-JOB, DATA-COMPAT, ARCH-PERSIST, OPS-STARTUP |
| `tests/unit/infrastructure/persistence/test_history_search_repository.py` | 4 | Real SQLite/FTS5 or fallback behavior | Preserve as integration evidence for DATA-SEARCH, FUNC-SEARCH, ARCH-PERSIST, SEC-PRIVACY |
| `tests/unit/infrastructure/persistence/test_local_file_storage.py` | 11 | Real filesystem operations | Current evidence for an abstraction explicitly removed from target architecture; retire/replace as its consumers disappear rather than treating the abstraction itself as normative |
| `tests/unit/infrastructure/audio/test_ffmpeg_converter.py::TestFfmpegRealIntegration` | 3 | Requires real ffmpeg/ffprobe binaries | Preserve as environment-gated contract evidence for FUNC-PROCESS, DATA-MEDIA, ARCH-PORTS, NFR-PORTABILITY |
| Three startup-recovery tests in `tests/unit/infrastructure/telegram/test_bot_adapter.py` | 3 | Real file-backed SQLite across adapter/startup recovery | Preserve behavior while ownership moves toward ARCH-EXECUTION; evidence for OPS-STARTUP, DATA-JOB/MEDIA, NFR-RELIABILITY |
| **Total** | **46** |  |  |

## Gate policy derived from the inventory

1. These tests are not automatically moved into the default gate merely because they are important.
2. Requirement acceptance criteria must state when the relevant integration evidence is required.
3. Refactoring must not discard the 35 durable integration behaviors represented by SQLite/search/ffmpeg/recovery tests.
4. The 11 `LocalFileStorage` tests may disappear only together with the non-target abstraction and after replacement coverage proves the purpose-specific storage contracts that remain.
5. Production-readiness still requires separate real-host operational evidence; these integration tests do not substitute for systemd/backup/rollback/recovery rehearsal.
