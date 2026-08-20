# WU-001: Access Groups as First-Class Financial Scopes

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/Access groups (`/access-groups`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-16

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Access groups | FinOps: Budgets | 01×05 | STRONG | STRONG |
| Org: Access groups | FinOps: Budget detail | 01×05 | STRONG | STRONG |
| Org: Access groups | FinOps: Budget overrides | 01×05 | STRONG | STRONG |
| Org: Access groups | FinOps: Billing periods | 01×05 | STRONG | STRONG |
| Org: Access groups | FinOps: Billing period detail | 01×05 | STRONG | STRONG |
| Org: Access groups | FinOps: Chargeback | 01×05 | STRONG | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Access groups × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Access groups
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Access groups row (Cohesion column)
- `FEATURE-STATUS.md` — 01-B × 05 counts

## Scope

- **Backend**: Add access-group-aware budget scoping: budgets, budget detail, budget overrides, billing periods, and billing period detail should accept and filter by access group. Chargeback attribution should recognize access groups as allocation units.
- **UI**: Budget and billing surfaces should show access-group scope selectors/filters. Access group detail page should show linked budgets and billing exposure.
- **Docs**: Document access groups as financial scope primitives in budget and billing docs.
- **Postman**: Add access-group filter parameters to budget and billing collections.
- **Scripts/Examples**: Add example exercising budget creation scoped to an access group, billing period filtered by access group.

## Acceptance Criteria

1. Budgets can be scoped to access groups (create, list, filter)
2. Budget detail and overrides reflect access-group ownership
3. Billing periods and billing period detail can filter by access group
4. Chargeback recognizes access groups as attribution units
5. Access group detail page links to its financial exposure
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated

## Completion Notes

- Access groups now act as real financial scopes across Budgets, Billing, and Chargeback.
- The access-groups dashboard deep-links into scoped budget, billing, and chargeback flows.
- Docs, Postman, and support examples now reflect the shipped access-group FinOps path.
