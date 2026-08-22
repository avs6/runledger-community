# WU-002: Performance Controls FinOps Budget Bridge

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - C (Performance Controls)
- **Target**: 02-GATEWAY-AND-ROUTING/Response cache, Rate limits (`/gateway`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Response cache | FinOps: Budget detail | 02×05 | GAP | STRONG |
| Gateway: Rate limits | FinOps: Budget detail | 02×05 | GAP | STRONG |
| Gateway: Response cache | FinOps: Budgets | 02×05 | PARTIAL | STRONG |
| Gateway: Response cache | FinOps: Billing periods | 02×05 | PARTIAL | STRONG |
| Gateway: Response cache | FinOps: Billing period detail | 02×05 | PARTIAL | STRONG |
| Gateway: Response cache | FinOps: Chargeback | 02×05 | PARTIAL | STRONG |
| Gateway: Rate limits | FinOps: Budgets | 02×05 | PARTIAL | STRONG |
| Gateway: Rate limits | FinOps: Budget overrides | 02×05 | PARTIAL | STRONG |
| Gateway: Rate limits | FinOps: Billing periods | 02×05 | PARTIAL | STRONG |
| Gateway: Rate limits | FinOps: Billing period detail | 02×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Response cache and Rate limits × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Response cache and Rate limits
- `02-GATEWAY-AND-ROUTING/GAP-MATRIX.md` — Response cache and Rate limits rows
- `FEATURE-STATUS.md` — 02-C × 05 counts

## Scope

- **Backend**: Budget detail should reflect cache savings and throttle impact: cache hit rates translate to cost avoidance, rate-limit enforcement translates to spend containment. Add cache-savings and throttle-impact fields to budget detail response. Add cache and rate-limit awareness to billing period breakdown.
- **UI**: Budget detail page should show cache savings contribution and throttle containment impact. Gateway cache and rate-limit controls should link to their budget detail impact. Billing period detail should surface cache/throttle economics.
- **Docs**: Document the relationship between performance controls and financial outcomes.
- **Postman**: Add cache savings and throttle impact to budget detail endpoint; add economics linkage to cache/rate-limit endpoints.
- **Scripts/Examples**: Add example showing how cache hit rates and rate-limit enforcement affect budget detail and billing outcomes.

## Acceptance Criteria

1. Budget detail shows cache savings contribution
2. Budget detail shows rate-limit containment impact
3. Gateway cache and rate-limit sections link to their budget impact
4. Billing period detail surfaces cache/throttle economics
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
