# WU-014: Run Detail Runtime Evidence Refresh

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - Bundle B (Request, Run, and Session Investigation)
- **Target**: 03-OBSERVE/Run detail (`/runs/{run_id}`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Run detail | FinOps: Budgets | 03x05 | PARTIAL | STRONG |
| Observe: Run detail | FinOps: Budget detail | 03x05 | PARTIAL | STRONG |
| Observe: Run detail | Org: Workspaces | 03x01 | PARTIAL | STRONG |
| Observe: Run detail | Org: MCP registry | 03x01 | PARTIAL | STRONG |
| Observe: Run detail | Gateway: Guardrails | 03x02 | PARTIAL | STRONG |
| Observe: Run detail | Safety: Approvals | 03x04 | N/A | PARTIAL |
| Observe: Run detail | Safety: Data capture | 03x04 | N/A | PARTIAL |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Run detail row
- `03-OBSERVE/COHESION-MATRIX.md` — Run detail cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Run detail
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Run detail
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Run detail
- `05-FINOPS/COHESION-MATRIX.md` — their view of Run detail
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.3 if delivery surfaces change

## Scope

- **Backend**: Enrich run-detail evidence with stronger workspace, MCP/tool, budget, and policy metadata where missing.
- **UI**: Make run detail the clearest single-surface explanation of routing, policy, cost, and tool/runtime outcomes.
- **Docs**: Clarify run detail as the primary execution-evidence page.
- **Postman**: Add any new run-detail evidence fields or related subresource requests.
- **Scripts/Examples**: Add a run-detail investigation example showing runtime, spend, and policy evidence together.

## Acceptance Criteria

1. Run detail explains routing, policy, scope, and spend outcomes more directly.
2. Operators can use one page to understand what happened before pivoting elsewhere.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
