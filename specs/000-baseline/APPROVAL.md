# Baseline Specification Approval

Package: **000-baseline**
Approved version: **1.0.0**
Constitution: **1.0.0**
Approval date: **2026-08-15**
Status: **Approved**

## Decision

The project owner explicitly approved the reviewed baseline specifications and authorized promotion from `0.3.0-draft / Approval Candidate` to `1.0.0 / Approved`.

Promotion is semantic-preserving: no product, architecture, domain, data, quality, security, or operations rule was changed as part of the status transition.

## Approved artifacts

- `PRODUCT.md`
- `ARCHITECTURE.md`
- `DOMAIN.md`
- `DATA-AND-ARTIFACTS.md`
- `QUALITY.md`
- `SECURITY-AND-OPERATIONS.md`
- `DECISIONS.md`
- `OPEN-DECISIONS.md`

The ratified `../constitution.md` remains the higher-order normative artifact.

## Effect

From this approval onward:

1. conflicts between implementation and these specifications are classified under the Constitution rather than automatically resolved in favor of current code;
2. known baseline deviations remain defects/debt to be derived into requirements rather than silently accepted;
3. current-system use cases may now be derived from the approved baseline;
4. no implementation plan or task breakdown is authorized before use cases and the requirement tree are reviewed.
