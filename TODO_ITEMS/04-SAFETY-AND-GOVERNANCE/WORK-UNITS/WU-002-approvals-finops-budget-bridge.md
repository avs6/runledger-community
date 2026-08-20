# WU-002: Approvals & Alert Rules FinOps Budget Bridge

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - B (Exception Workflows)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Approvals, Alert rules
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Approvals | FinOps: Budgets | 04×05 | GAP | STRONG |
| Safety: Approvals | FinOps: Budget detail | 04×05 | GAP | STRONG |
| Safety: Alert rules | FinOps: Budgets | 04×05 | PARTIAL | STRONG |
| Safety: Alert rules | FinOps: Budget detail | 04×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Approvals and Alert rules × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Approvals and Alert rules
- `FEATURE-STATUS.md` — 04-B × 05 counts

## Scope

- **Backend**: Approvals should support budget-related exception paths: temporary budget override approvals, budget breach exception requests, high-cost action approvals. Budget detail should link to pending and resolved approval requests that affected it. Alert rules should support budget-based conditions: spend threshold, utilization percentage, budget breach events.
- **UI**: Approvals queue should show budget context on budget-related requests with drill-through to budget detail. Alert rules should offer budget-based condition types. Both surfaces should link to budget detail for context.
- **Docs**: Document budget-driven approval and alert workflows.
- **Postman**: Add budget context to approval request and alert rule payloads.
- **Scripts/Examples**: Add example creating a budget override approval and a budget-threshold alert rule.

## Acceptance Criteria

1. Approvals supports budget override and budget breach exception paths
2. Budget detail links to related approval requests
3. Alert rules supports budget-based conditions
4. Both surfaces link to budget detail for context
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
