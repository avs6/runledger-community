# WU-002: Investigation Surfaces FinOps Budget Bridge

- **Status**: COMPLETED
- **Bundle**: 03-Observe - B (Investigation)
- **Target**: 03-OBSERVE/Request flow, Request explorer
- **Created**: 2026-08-14
- **Completed**: 2026-08-24

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Request flow | FinOps: Budget detail | 03×05 | GAP | STRONG |
| Observe: Request explorer | FinOps: Budget detail | 03×05 | GAP | STRONG |
| Observe: Runs list | FinOps: Budgets | 03×05 | PARTIAL | STRONG |
| Observe: Runs list | FinOps: Budget overrides | 03×05 | PARTIAL | STRONG |
| Observe: Runs list | FinOps: Billing periods | 03×05 | PARTIAL | STRONG |
| Observe: Runs list | FinOps: Billing period detail | 03×05 | PARTIAL | STRONG |
| Observe: Runs list | FinOps: Chargeback | 03×05 | PARTIAL | STRONG |
| Observe: Run detail | FinOps: Budgets | 03×05 | PARTIAL | STRONG |
| Observe: Run detail | FinOps: Budget overrides | 03×05 | PARTIAL | STRONG |
| Observe: Run detail | FinOps: Billing periods | 03×05 | PARTIAL | STRONG |
| Observe: Run detail | FinOps: Billing period detail | 03×05 | PARTIAL | STRONG |
| Observe: Run detail | FinOps: Chargeback | 03×05 | PARTIAL | STRONG |
| Observe: Request flow | FinOps: Budgets | 03×05 | PARTIAL | STRONG |
| Observe: Request flow | FinOps: Budget overrides | 03×05 | PARTIAL | STRONG |
| Observe: Request flow | FinOps: Billing periods | 03×05 | PARTIAL | STRONG |
| Observe: Request flow | FinOps: Billing period detail | 03×05 | PARTIAL | STRONG |
| Observe: Request flow | FinOps: Chargeback | 03×05 | PARTIAL | STRONG |
| Observe: Request explorer | FinOps: Budgets | 03×05 | PARTIAL | STRONG |
| Observe: Request explorer | FinOps: Budget overrides | 03×05 | PARTIAL | STRONG |
| Observe: Request explorer | FinOps: Billing periods | 03×05 | PARTIAL | STRONG |
| Observe: Request explorer | FinOps: Billing period detail | 03×05 | PARTIAL | STRONG |
| Observe: Request explorer | FinOps: Chargeback | 03×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Investigation × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Investigation features
- `03-OBSERVE/GAP-MATRIX.md` — Request flow, Request explorer rows
- `FEATURE-STATUS.md` — 03-B × 05 counts

## Scope

- **Backend**: Request flow and request explorer should expose budget detail context: per-request cost against budget, budget utilization at request time, override status. Runs list and run detail should show budget and billing attribution. Chargeback allocation should be visible from investigation surfaces.
- **UI**: Request flow and request explorer should show inline budget impact with drill-through to budget detail. Run detail should show budget utilization context. Investigation surfaces should link to billing period detail and chargeback for attribution.
- **Docs**: Document cost investigation workflows bridging from request analysis into FinOps.
- **Postman**: Add budget context to request flow and request explorer responses.
- **Scripts/Examples**: Add example investigating a request's budget impact and drilling into budget detail.

## Acceptance Criteria

1. Request flow shows per-request budget impact with budget detail links
2. Request explorer shows budget context and links to budget detail
3. Run detail shows budget utilization at time of execution
4. Investigation surfaces link to billing and chargeback attribution
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
