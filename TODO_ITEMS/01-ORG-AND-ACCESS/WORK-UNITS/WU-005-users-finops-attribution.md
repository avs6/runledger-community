# WU-005: User Identity in FinOps Attribution

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/Users (`/users`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-16

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Users | FinOps: Budget detail | 01×05 | GAP | STRONG |
| Org: Users | FinOps: Budgets | 01×05 | PARTIAL | STRONG |
| Org: Users | FinOps: Budget overrides | 01×05 | PARTIAL | STRONG |
| Org: Users | FinOps: Billing periods | 01×05 | PARTIAL | STRONG |
| Org: Users | FinOps: Billing period detail | 01×05 | PARTIAL | STRONG |
| Org: Users | FinOps: Chargeback | 01×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Users × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Users
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Users row (Cohesion column)
- `FEATURE-STATUS.md` — 01-B × 05 counts

## Scope

- **Backend**: User identity should connect to spend accountability: budget detail should show per-user spend where attributable, billing period detail should support user-level breakdown, chargeback should recognize user as an attribution dimension.
- **UI**: Budget detail should show user-level spend breakdown. User detail page should show financial exposure (budgets they touch, spend attributed to them).
- **Docs**: Document user-level financial attribution patterns.
- **Postman**: Add user filter to budget detail and billing breakdown endpoints.
- **Scripts/Examples**: Add example viewing a user's financial footprint across budgets and billing.

## Acceptance Criteria

1. Budget detail surfaces per-user spend breakdown
2. Billing period detail supports user-level attribution
3. Chargeback recognizes user identity as an allocation dimension
4. User detail page shows linked financial exposure
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated

## Completion Notes

- Added `GET /budgets/{id}/breakdown` endpoint returning per-end-user spend breakdown (cost, run count, call count, % of total) with proper `BudgetUserBreakdownEntry` Pydantic schema.
- Budget detail page now renders a "Spend by End User" table from the breakdown data.
- Budget breakdown supports all scope types: `end_user`, `access_group` (via member ID resolution), `api_key` (via `ProviderCall.api_key_id`), `feature_tag`, and `app`.
- Billing period breakdown and chargeback accept `end_user_id` filter for user-scoped views.
- Added `GET /users/{user_id}/finance` endpoint returning 30-day and total spend, run/call counts, and budgets scoped to the user's identity (matching platform `User.id` against `ProviderCall.end_user_id`).
- Created `/users/[user_id]` detail page with financial exposure cards (spend, runs, calls), budget exposure table, and drill-through links to Runs, Analytics, and Chargeback.
- Users list page now links to the user detail page via a dollar-sign icon.
- Updated `docs/finops/budgets.mdx` with per-user spend breakdown documentation.
- Added `User Financial Exposure` and `Budget Spend Breakdown` Postman requests.
- Added `examples/51_user_finance_exposure.py` demonstrating the user financial footprint workflow.
- Identity note: platform User identity is bridged to FinOps via `str(User.id)` matching `ProviderCall.end_user_id`. This convention is strongest when SDK callers pass the platform user ID as their `end_user_id`.
