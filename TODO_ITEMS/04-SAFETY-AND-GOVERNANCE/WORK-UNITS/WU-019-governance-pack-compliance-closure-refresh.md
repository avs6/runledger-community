# WU-019: Governance Pack Compliance Closure Refresh

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - D (Evidence, Audit, and Compliance Closure)
- **Target**: 04-SAFETY-AND-GOVERNANCE/governance-pack
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Governance pack | FinOps: Ledger | 04x05 | STRONG | STRONG |
| Safety: Governance pack | FinOps: Budgets | 04x05 | PARTIAL | STRONG |
| Safety: Governance pack | Org: Organization profile | 04x01 | PARTIAL | STRONG |
| Safety: Governance pack | Org: Workspaces | 04x01 | PARTIAL | STRONG |
| Safety: Governance pack | Gateway: Guardrails | 04x02 | PARTIAL | STRONG |
| Safety: Governance pack | Observe: Monitoring | 04x03 | PARTIAL | STRONG |
| Safety: Governance pack | Safety: Audit log | 04x04 | PARTIAL | STRONG |
| Safety: Governance pack | Safety: Tags | 04x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` - Governance pack row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - Governance pack cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - org and workspace evidence packaging view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - runtime-governance evidence source view
- `03-OBSERVE/COHESION-MATRIX.md` - monitoring evidence source view
- `05-FINOPS/COHESION-MATRIX.md` - ledger and budget evidence packaging view

## Scope

- **Backend**: Re-audit Governance Pack as the downstream compliance packaging layer that should consume upstream governance, runtime, and financial evidence coherently.
- **UI**: Make source coverage, scope filters, and evidence lineage easier to understand before export.
- **Docs**: Describe Governance Pack as a downstream package of cross-suite evidence, not an isolated export tool.
- **Postman**: Keep package generation and export flows aligned with richer source-consumption expectations.
- **Scripts/Examples**: Add a compliance-package example that pulls from security, runtime, spend, and audit sources together.

## Acceptance Criteria

1. Governance Pack is re-audited as a cross-suite compliance closure surface
2. Budget, ledger, runtime, and monitoring evidence relationships are explicitly covered
3. Audit-log and tag-source relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
