# WU-017: Billing Periods Reconciliation Refresh

- **Status**: COMPLETED
- **Bundle**: 05-FinOps - B (Billing and Reconciliation)
- **Target**: 05-FINOPS/billing-periods
- **Created**: 2026-08-16
- **Completed**: 2026-09-01

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Billing periods | Org: Users | 05x01 | GAP | STRONG |
| FinOps: Billing periods | Org: API keys | 05x01 | GAP | STRONG |
| FinOps: Billing periods | Gateway: Provider profiles | 05x02 | PARTIAL | STRONG |
| FinOps: Billing periods | Gateway: Response cache | 05x02 | PARTIAL | STRONG |
| FinOps: Billing periods | Gateway: Rate limits | 05x02 | PARTIAL | STRONG |
| FinOps: Billing periods | Observe: Analytics economics | 05x03 | STRONG | STRONG |
| FinOps: Billing periods | Safety: Alert rules | 05x04 | PARTIAL | STRONG |
| FinOps: Billing periods | Safety: Audit log | 05x04 | PARTIAL | STRONG |
| FinOps: Billing periods | Build: Optimization opportunities | 05x06 | PARTIAL | STRONG |
| FinOps: Billing periods | Platform: Platform settings | 05x07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/GAP-MATRIX.md` - Billing periods row
- `05-FINOPS/COHESION-MATRIX.md` - Billing periods cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - user and API key billing ownership view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - provider, cache, and throttle cost view
- `03-OBSERVE/COHESION-MATRIX.md` - economics and analytics view
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - alerting and audit evidence view
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - optimization feedback view
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - platform reconciliation view

## Scope

- **Backend**: Re-audit Billing Periods as the accounting and reconciliation shell that consumes spend controls and produces downstream allocation-ready outputs.
- **UI**: Strengthen visibility into period readiness, provider/cache effects, and related audit or optimization context.
- **Docs**: Position Billing as operational reconciliation, not only finance summary.
- **Postman**: Keep period lifecycle, export, and reconciliation flows aligned with the current operator workflow.
- **Scripts/Examples**: Add a billing-period scenario covering cache savings, provider mix, alerts, and downstream optimization review.

## Acceptance Criteria

1. Billing Periods are re-audited as the Bundle B parent surface
2. Gateway-cost, audit, and optimization relationships are explicitly covered
3. User and API key ownership relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
