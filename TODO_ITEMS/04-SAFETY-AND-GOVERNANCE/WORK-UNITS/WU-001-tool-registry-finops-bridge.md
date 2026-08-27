# WU-001: Tool Registry FinOps Budget Bridge

- **Status**: COMPLETED
- **Bundle**: 04-Safety - A (Tool Governance)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Tool registry
- **Created**: 2026-08-14
- **Completed**: 2026-08-26

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tool registry | FinOps: Budget detail | 04×05 | STRONG | STRONG |
| Safety: Tool registry | FinOps: Budgets | 04×05 | STRONG | STRONG |
| Safety: Tool registry | FinOps: Chargeback | 04×05 | STRONG | STRONG |

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

## Completion Notes

- Backend: Added `GET /analytics/tool-registry-finops-posture` endpoint returning budget context (total/tool-scoped budgets, total limit), chargeback context (active rules, tool-dimension rules), and spend context (tool spend, call count, total spend) for the workspace over 30 days.
- UI: Tool Registry page now shows an emerald-themed FinOps Budget Impact posture card with tool spend, total spend, budget coverage, and chargeback rule counts. Registry list table includes a Cost column with drill-through to Chargeback filtered by `feature_tag` dimension. Drill-through links to Budgets, Budget Detail, Chargeback by Tool, and Ledger.
- UI: Budget Detail performance economics card now includes a Tool Registry drill-through link. Chargeback overview now includes Tool Registry, Budgets, Budget Detail, and Ledger drill-through links.
- Docs: `docs/governance/tool-governance.mdx` updated with budget impact section and FinOps-related cards.
- Postman: Added "Tool Registry FinOps Posture" request to the analytics folder.
- Example: Added `examples/93_tool_registry_budget_impact.py` demonstrating tool registry listing, posture fetch, and chargeback report by tool.
