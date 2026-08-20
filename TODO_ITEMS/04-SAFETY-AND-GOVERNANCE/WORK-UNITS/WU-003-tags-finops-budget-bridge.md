# WU-003: Tags FinOps Budget Detail Bridge

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - C (Data Protection)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Tags
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tags | FinOps: Budget detail | 04×05 | GAP | STRONG |
| Safety: Tags | FinOps: Budgets | 04×05 | PARTIAL | STRONG |
| Safety: Tags | FinOps: Chargeback | 04×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Tags × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Tags
- `FEATURE-STATUS.md` — 04-C × 05 counts

## Scope

- **Backend**: Tags should serve as a shared classification and attribution dimension for FinOps: tag-based budget scoping, tag-based cost attribution in budget detail, tag-based chargeback grouping. Budget detail should show tag breakdown. Auto-tagging rules should be available as a chargeback attribution mechanism.
- **UI**: Tags management should show budget and cost attribution context. Budget detail should show tag-based cost breakdowns. Chargeback should support tag-based grouping and attribution.
- **Docs**: Document tag-driven budget attribution and chargeback workflows.
- **Postman**: Add tag context to budget and chargeback responses.
- **Scripts/Examples**: Add example using tags for budget scoping and chargeback attribution.

## Acceptance Criteria

1. Tags serve as a FinOps attribution dimension
2. Budget detail shows tag-based cost breakdowns
3. Chargeback supports tag-based grouping
4. Auto-tagging rules available for chargeback attribution
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
