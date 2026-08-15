# WU-008: Internal FinOps Cohesion

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A/C/D (Cross-bundle)
- **Target**: 05-FINOPS/Budgets, Budget detail, Chargeback, Ledger
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budgets | FinOps: Budget detail | 05×05 | GAP | STRONG |
| FinOps: Budget detail | FinOps: Budgets | 05×05 | GAP | STRONG |
| FinOps: Budget detail | FinOps: Chargeback | 05×05 | GAP | STRONG |
| FinOps: Budget detail | FinOps: Ledger | 05×05 | GAP | STRONG |
| FinOps: Chargeback | FinOps: Budget detail | 05×05 | PARTIAL | STRONG |
| FinOps: Ledger | FinOps: Budget detail | 05×05 | PARTIAL | STRONG |
| FinOps: Budgets | FinOps: Budget overrides | 05×05 | PARTIAL | STRONG |
| FinOps: Budgets | FinOps: Budget notifications | 05×05 | PARTIAL | STRONG |
| FinOps: Budgets | FinOps: Billing periods | 05×05 | PARTIAL | STRONG |
| FinOps: Budgets | FinOps: Billing period detail | 05×05 | PARTIAL | STRONG |
| FinOps: Budgets | FinOps: Chargeback | 05×05 | PARTIAL | STRONG |
| FinOps: Budgets | FinOps: Ledger | 05×05 | PARTIAL | STRONG |
| FinOps: Budget detail | FinOps: Budget overrides | 05×05 | PARTIAL | STRONG |
| FinOps: Budget detail | FinOps: Budget notifications | 05×05 | PARTIAL | STRONG |
| FinOps: Budget detail | FinOps: Billing periods | 05×05 | PARTIAL | STRONG |
| FinOps: Budget detail | FinOps: Billing period detail | 05×05 | PARTIAL | STRONG |
| FinOps: Budget overrides | FinOps: Budget notifications | 05×05 | PARTIAL | STRONG |
| FinOps: Budget overrides | FinOps: Billing periods | 05×05 | PARTIAL | STRONG |
| FinOps: Budget overrides | FinOps: Billing period detail | 05×05 | PARTIAL | STRONG |
| FinOps: Budget overrides | FinOps: Chargeback | 05×05 | PARTIAL | STRONG |
| FinOps: Budget overrides | FinOps: Ledger | 05×05 | PARTIAL | STRONG |
| FinOps: Budget notifications | FinOps: Billing periods | 05×05 | PARTIAL | STRONG |
| FinOps: Budget notifications | FinOps: Billing period detail | 05×05 | PARTIAL | STRONG |
| FinOps: Budget notifications | FinOps: Ledger | 05×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — all self-referential cells
- `FEATURE-STATUS.md` — 05 × self counts

## Scope

- **Backend**: Budget detail must become a real page that bidirectionally links to budgets (parent), overrides, notifications, billing periods, chargeback, and ledger. Chargeback should consume budget scope quality. Ledger should consume budget verification context. The internal FinOps domain should feel like one connected operating system.
- **UI**: Budget detail must link to parent budget, active overrides, notification channels, related billing periods, chargeback allocation, and ledger evidence. Chargeback should show upstream budget posture. Ledger should show budget verification status. Navigation between all FinOps surfaces should be seamless.
- **Docs**: Document the internal FinOps domain workflow from budget policy through billing to chargeback and ledger.
- **Postman**: Add cross-surface linkage to all FinOps endpoints.
- **Scripts/Examples**: Add example walking the full FinOps lifecycle: budget → override → billing → chargeback → ledger.

## Acceptance Criteria

1. Budget detail bidirectionally links to all FinOps surfaces
2. Chargeback consumes budget scope quality signals
3. Ledger consumes budget verification context
4. Internal FinOps navigation is seamless
5. All listed cohesion cells updated to target state
6. FEATURE-STATUS.md dashboard updated
