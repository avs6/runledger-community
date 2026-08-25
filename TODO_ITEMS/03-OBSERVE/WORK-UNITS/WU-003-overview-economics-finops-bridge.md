# WU-003: Overview & Economics FinOps Budget Bridge

- **Status**: COMPLETED
- **Bundle**: 03-Observe - A/C (Overview & Entry, Economics & Intel)
- **Target**: 03-OBSERVE/Analytics overview, Model usage
- **Created**: 2026-08-14
- **Completed**: 2026-08-24

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Analytics overview | FinOps: Budget detail | 03×05 | GAP | STRONG |
| Observe: Model usage | FinOps: Budget detail | 03×05 | GAP | STRONG |
| Observe: Analytics overview | FinOps: Budgets | 03×05 | PARTIAL | STRONG |
| Observe: Analytics overview | FinOps: Budget overrides | 03×05 | PARTIAL | STRONG |
| Observe: Analytics overview | FinOps: Budget notifications | 03×05 | PARTIAL | STRONG |
| Observe: Analytics overview | FinOps: Billing periods | 03×05 | PARTIAL | STRONG |
| Observe: Analytics overview | FinOps: Billing period detail | 03×05 | PARTIAL | STRONG |
| Observe: Analytics overview | FinOps: Chargeback | 03×05 | PARTIAL | STRONG |
| Observe: Analytics overview | FinOps: Ledger | 03×05 | PARTIAL | STRONG |
| Observe: Model usage | FinOps: Budgets | 03×05 | PARTIAL | STRONG |
| Observe: Model usage | FinOps: Billing periods | 03×05 | PARTIAL | STRONG |
| Observe: Model usage | FinOps: Billing period detail | 03×05 | PARTIAL | STRONG |
| Observe: Model usage | FinOps: Chargeback | 03×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Analytics overview and Model usage × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Analytics overview and Model usage
- `FEATURE-STATUS.md` — 03-A/C × 05 counts

## Scope

- **Backend**: Analytics overview should expose budget posture summary: active budget count, utilization percentage, overdue budgets, notification status. Model usage should show per-model budget detail linkage: cost against budget, billing period allocation, chargeback attribution by model.
- **UI**: Analytics overview should include a budget posture card with drill-through to budget detail. Model usage should show per-model budget utilization with links to budget detail. Both should link to billing period detail and chargeback.
- **Docs**: Document the overview-to-budget and model-usage-to-budget operator bridges.
- **Postman**: Add budget posture summary to analytics overview endpoint; add budget context to model usage endpoint.
- **Scripts/Examples**: Add example viewing budget posture from analytics overview and model-level budget utilization.

## Acceptance Criteria

1. Analytics overview shows budget posture card with drill-through to budget detail
2. Model usage shows per-model budget utilization with budget detail links
3. Both surfaces link to billing and chargeback attribution
4. Budget notification status visible from analytics overview
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
