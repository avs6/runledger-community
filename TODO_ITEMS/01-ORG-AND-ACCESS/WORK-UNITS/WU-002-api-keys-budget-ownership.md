# WU-002: API Keys as First-Class Budget Owners

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/API keys (`/api-keys`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-16

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: API keys | FinOps: Budgets | 01×05 | GAP | STRONG |
| Org: API keys | FinOps: Budget detail | 01×05 | GAP | STRONG |
| Org: API keys | FinOps: Budget overrides | 01×05 | GAP | STRONG |
| Org: API keys | FinOps: Billing periods | 01×05 | PARTIAL | STRONG |
| Org: API keys | FinOps: Billing period detail | 01×05 | PARTIAL | STRONG |
| Org: API keys | FinOps: Chargeback | 01×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — API keys × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of API keys
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — API keys row (Cohesion column)
- `FEATURE-STATUS.md` — 01-B × 05 counts

## Scope

- **Backend**: API keys should be recognized as budget owners: budget creation/filtering by API key, budget detail showing per-key allocation, budget overrides assignable to API keys. Billing and chargeback should attribute spend to API keys.
- **UI**: Budget surfaces should expose API-key scope. API key detail page should show budget assignment and spend attribution.
- **Docs**: Document API keys as budget-owning identities.
- **Postman**: Add API-key filter/scope parameters to budget and billing collections.
- **Scripts/Examples**: Add example creating a budget scoped to an API key and viewing its spend attribution.

## Acceptance Criteria

1. Budgets can be scoped to API keys (create, list, filter)
2. Budget detail shows per-API-key allocation
3. Budget overrides can target specific API keys
4. Billing period detail attributes spend by API key
5. Chargeback recognizes API-key-level attribution
6. API key detail page shows budget and spend exposure
7. All listed cohesion cells updated to target state
8. All paired feature files updated
9. FEATURE-STATUS.md dashboard updated

## Completion Notes

- API keys now participate as first-class budget owners across persisted run/call attribution, billing filters, and chargeback allocation.
- The dashboard now has an API key detail route with scoped budget assignment, billing-period drill-through, and chargeback exposure.
- Docs, Postman, smoke coverage, and examples now reflect API-key-scoped FinOps evidence flows.
