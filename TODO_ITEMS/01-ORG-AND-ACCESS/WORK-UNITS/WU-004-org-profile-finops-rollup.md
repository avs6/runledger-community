# WU-004: Org Profile FinOps Rollup Summaries

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - A (Org Foundation)
- **Target**: 01-ORG-AND-ACCESS/Organization profile (`/organization`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-16

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Organization profile | FinOps: Budget detail | 01×05 | GAP | STRONG |
| Org: Organization profile | FinOps: Budgets | 01×05 | PARTIAL | STRONG |
| Org: Organization profile | FinOps: Budget overrides | 01×05 | PARTIAL | STRONG |
| Org: Organization profile | FinOps: Budget notifications | 01×05 | PARTIAL | STRONG |
| Org: Organization profile | FinOps: Billing periods | 01×05 | PARTIAL | STRONG |
| Org: Organization profile | FinOps: Billing period detail | 01×05 | PARTIAL | STRONG |
| Org: Organization profile | FinOps: Chargeback | 01×05 | PARTIAL | STRONG |
| Org: Organization profile | FinOps: Ledger | 01×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Organization profile × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Organization profile
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Organization profile row (Cohesion column)
- `FEATURE-STATUS.md` — 01-A × 05 counts

## Scope

- **Backend**: Add read-only org-level financial posture summary endpoint: active budget count, total spend, overdue billing periods, chargeback allocation status, ledger readiness. Org profile should consume these as summaries, not duplicate editing.
- **UI**: Org console should display a financial posture card with drill-through links to budgets, billing, chargeback, and ledger. No editing controls — read-only with navigation.
- **Docs**: Document the org financial posture summary and its relationship to the FinOps surfaces.
- **Postman**: Add org financial posture summary request.
- **Scripts/Examples**: Add example reading org financial posture and navigating into budget detail.

## Acceptance Criteria

1. Org console shows a read-only financial posture summary
2. Summary includes budget count, spend, billing status, chargeback, ledger readiness
3. Each summary element links to the owning FinOps surface
4. No duplicate editing controls created in the org console
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated

## Completion Notes

- Expanded `GET /org/finance` into a real org financial posture rollup with budget, override, notification, billing, chargeback, and ledger readiness signals.
- Added a read-only Financial Posture section to `/organization` with drill-through links into Budgets, Billing, Chargeback, and Compliance.
- Updated docs, Postman, a runnable example, and a smoke script to reflect the org-level FinOps handoff flow.
