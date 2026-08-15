# WU-004: Budget Control × Safety & Governance

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budgets, Budget detail, Budget overrides
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budgets | Safety: Approvals | 05×04 | GAP | STRONG |
| FinOps: Budget detail | Safety: Tool registry | 05×04 | GAP | STRONG |
| FinOps: Budget detail | Safety: Approvals | 05×04 | GAP | STRONG |
| FinOps: Budget detail | Safety: Governance pack | 05×04 | GAP | STRONG |
| FinOps: Budget detail | Safety: Tags | 05×04 | GAP | STRONG |
| FinOps: Budget overrides | Safety: Approvals | 05×04 | GAP | STRONG |
| FinOps: Budget overrides | Safety: Tags | 05×04 | GAP | STRONG |
| FinOps: Budgets | Safety: Tool registry | 05×04 | PARTIAL | STRONG |
| FinOps: Budgets | Safety: Alert rules | 05×04 | PARTIAL | STRONG |
| FinOps: Budgets | Safety: Audit log | 05×04 | PARTIAL | STRONG |
| FinOps: Budgets | Safety: Governance pack | 05×04 | PARTIAL | STRONG |
| FinOps: Budgets | Safety: Tags | 05×04 | PARTIAL | STRONG |
| FinOps: Budget detail | Safety: Alert rules | 05×04 | PARTIAL | STRONG |
| FinOps: Budget detail | Safety: Audit log | 05×04 | PARTIAL | STRONG |
| FinOps: Budget overrides | Safety: Alert rules | 05×04 | PARTIAL | STRONG |
| FinOps: Budget overrides | Safety: Audit log | 05×04 | PARTIAL | STRONG |
| FinOps: Budget overrides | Safety: Governance pack | 05×04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budgets/Budget detail/Overrides × Safety cells
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Budget surfaces
- `FEATURE-STATUS.md` — 05-A × 04 counts

## Scope

- **Backend**: Budget overrides must route through approvals for high-risk exceptions. Budget detail must link to tool registry (tool-level budget impact), governance pack (budget evidence), and tags (budget classification). Budget events must flow into audit log. Tags must serve as a budget attribution dimension. Alert rules must support budget-based conditions.
- **UI**: Override creation must show approval workflow for high-risk overrides. Budget detail must show governance pack evidence links, tool registry budget impact, and tag-based classification. Budget events must be visible in audit log. Tags should be available as a budget filter and grouping dimension.
- **Docs**: Document governed budget override workflow and tag-based budget attribution.
- **Postman**: Add governance context to budget and override endpoints.
- **Scripts/Examples**: Add example creating a governed budget override through approval and viewing budget evidence in governance pack.

## Acceptance Criteria

1. Budget overrides route through approvals for high-risk exceptions
2. Budget detail links to tool registry, governance pack, and tags
3. Budget events flow into audit log
4. Tags serve as budget attribution and classification dimension
5. Alert rules support budget-based conditions
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
