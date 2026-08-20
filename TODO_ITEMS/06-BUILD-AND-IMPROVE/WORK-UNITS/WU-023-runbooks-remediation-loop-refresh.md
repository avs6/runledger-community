# WU-023: Runbooks Remediation Loop Refresh

- **Status**: NOT_STARTED
- **Bundle**: 06-Build - C (Evaluation and Replay Studio)
- **Target**: 06-BUILD-AND-IMPROVE/runbooks
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Runbooks | Gateway: Guardrails | 06x02 | PARTIAL | STRONG |
| Build: Runbooks | Observe: Runs list | 06x03 | PARTIAL | STRONG |
| Build: Runbooks | Observe: Run detail | 06x03 | PARTIAL | STRONG |
| Build: Runbooks | Safety: Alert rules | 06x04 | PARTIAL | STRONG |
| Build: Runbooks | FinOps: Billing periods | 06x05 | PARTIAL | STRONG |
| Build: Runbooks | Build: Optimization opportunities | 06x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/GAP-MATRIX.md` - Runbooks row
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - Runbooks cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit Runbooks as the downstream remediation and guidance loop from runtime and evaluation evidence.
- **UI**: Strengthen incident, alert, and optimization context around generated runbooks.
- **Docs**: Position runbooks inside the improve loop rather than as a thin runs-adjacent artifact.
- **Postman**: Keep runbook generation and export flows aligned with evidence-driven remediation.
- **Scripts/Examples**: Add a runbook scenario linking one incident to evaluation, alerting, and cost review.

## Acceptance Criteria

1. Runbooks are re-audited as remediation-loop surfaces
2. Incident, governance, and cost relationships are explicitly covered
3. All listed cohesion cells move to the target state
4. FEATURE-STATUS.md is updated
