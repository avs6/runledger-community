# WU-001: Provider Profiles FinOps Budget Bridge

- **Status**: NOT_STARTED
- **Bundle**: 02-Gateway & Routing - A (Provider & Routing)
- **Target**: 02-GATEWAY-AND-ROUTING/Provider profiles (`/provider-profiles`)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Provider profiles | FinOps: Budget overrides | 02×05 | GAP | STRONG |
| Gateway: Provider profiles | FinOps: Budgets | 02×05 | PARTIAL | STRONG |
| Gateway: Provider profiles | FinOps: Budget detail | 02×05 | PARTIAL | STRONG |
| Gateway: Provider profiles | FinOps: Billing periods | 02×05 | PARTIAL | STRONG |
| Gateway: Provider profiles | FinOps: Billing period detail | 02×05 | PARTIAL | STRONG |
| Gateway: Provider profiles | FinOps: Chargeback | 02×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Provider profiles × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Provider profiles
- `02-GATEWAY-AND-ROUTING/GAP-MATRIX.md` — Provider profiles row (Cohesion column)
- `FEATURE-STATUS.md` — 02-A × 05 counts

## Scope

- **Backend**: Provider profiles should link to budget overrides (currently GAP): override policies should accept provider-profile scope, provider detail should return active override count. Strengthen provider-to-budget, billing, and chargeback links: provider detail should show attached budget posture, billing attribution by provider, and chargeback allocation shares.
- **UI**: Provider profile detail should show budget override exposure, budget posture summary, billing attribution, and chargeback share with drill-through links to the owning FinOps surfaces.
- **Docs**: Document provider-profile financial posture and override integration.
- **Postman**: Add provider-profile scope to budget override endpoints; add provider financial posture request.
- **Scripts/Examples**: Add example creating a budget override scoped to a provider profile and viewing provider billing attribution.

## Acceptance Criteria

1. Budget overrides can be scoped to a provider profile
2. Provider profile detail shows budget override count and posture
3. Provider billing and chargeback attribution is surfaceable
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
