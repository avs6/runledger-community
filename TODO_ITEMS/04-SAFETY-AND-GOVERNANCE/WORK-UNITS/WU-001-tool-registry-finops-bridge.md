# WU-001: Tool Registry FinOps Budget Bridge

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - A (Tool Governance)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Tool registry
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tool registry | FinOps: Budget detail | 04×05 | GAP | STRONG |
| Safety: Tool registry | FinOps: Budgets | 04×05 | PARTIAL | STRONG |
| Safety: Tool registry | FinOps: Chargeback | 04×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Tool registry × FinOps cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of Tool registry
- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` — Tool registry row
- `FEATURE-STATUS.md` — 04-A × 05 counts

## Scope

- **Backend**: Tool registry should expose budget impact context: which budgets a tool's usage charges against, budget utilization attributable to tool invocations, and chargeback allocation by tool. Budget detail should link back to tool registry entries that consume it.
- **UI**: Tool registry detail should show budget impact summary with drill-through to budget detail. Registry list should show cost attribution indicators. Chargeback surfaces should attribute by tool where relevant.
- **Docs**: Document tool-to-budget attribution workflow.
- **Postman**: Add budget context to tool registry response payloads.
- **Scripts/Examples**: Add example viewing budget impact of a registered tool.

## Acceptance Criteria

1. Tool registry detail shows budget impact with budget detail links
2. Budget utilization attributable to tool invocations is visible
3. Chargeback surfaces attribute by tool
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
