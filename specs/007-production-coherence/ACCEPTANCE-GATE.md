# PLAN-007 Pre-Delivery and Release Gate

Version: **1.0.0**
Status: **Normative**

No patch, ZIP, package or release candidate is distributed merely because it appears correct.

1. **Artifact integrity:** archive opens/extracts, expected files only, SHA-256 verifies.
2. **Git integrity:** exact HEAD/base, status, `git diff --check`, reviewed change scope.
3. **Syntax/import:** applicable code compiles/imports.
4. **Lint/format:** repository-approved Ruff checks pass.
5. **Types:** mypy passes; type failure blocks delivery.
6. **Tests:** focused + relevant conformance/integration + full default suite as applicable.
7. **Architecture:** domain/application/composition/ports/I/O boundaries remain valid.
8. **Taxonomy:** no semantic synonyms/conflicts, misleading booleans, raw strings replacing existing
   VOs, Video/Media drift, signature/fingerprint drift, provider vocabulary in neutral contracts,
   missing units or persistence/UI/domain state conflation.
9. **Errors:** no swallowed failure, unsafe provider propagation or false success.
10. **Security:** secret scan, gitleaks, pre-commit and private-artifact inspection. A command that
    failed to execute is not a pass.
11. **Documentation:** commands/env/defaults/prerequisites/features match source.
12. **Clean install:** production instructions work without dev dependencies/source checkout.
13. **Operational:** when applicable, systemd, sanitized journal, health/status, SQLite and affected
    restart/rollback evidence pass.
14. **Delivery report:** candidate/base, files, commands/results, test totals, hashes, reservations
    and unexecuted checks are recorded.

Decision:
- **PASS:** all applicable critical gates pass.
- **PASS WITH RESERVATION:** only non-correctness/non-security limitations.
- **BLOCKED:** any applicable correctness/type/test/architecture/security/artifact/clean-install/
  required-runtime gate fails or is untrustworthy.

Anti-greenwashing: never change code merely to silence a gate when the change hides semantic or
architectural incoherence.
