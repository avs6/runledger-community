# WU-013: Runs List Investigation Bridge Refresh

- **Status**: COMPLETED
- **Bundle**: 03-Observe - Bundle B (Request, Run, and Session Investigation)
- **Target**: 03-OBSERVE/Runs list (`/runs`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-25

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Runs list | Org: Users | 03x01 | GAP | PARTIAL |
| Observe: Runs list | Org: Access groups | 03x01 | GAP | PARTIAL |
| Observe: Runs list | FinOps: Budgets | 03x05 | PARTIAL | STRONG |
| Observe: Runs list | FinOps: Budget detail | 03x05 | PARTIAL | STRONG |
| Observe: Runs list | Gateway: Guardrails | 03x02 | PARTIAL | STRONG |
| Observe: Runs list | Safety: Approvals | 03x04 | N/A | PARTIAL |
| Observe: Runs list | Safety: Data capture | 03x04 | N/A | PARTIAL |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Runs list row
- `03-OBSERVE/COHESION-MATRIX.md` — Runs list cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Runs list
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Runs list
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Runs list
- `05-FINOPS/COHESION-MATRIX.md` — their view of Runs list
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.2 if delivery surfaces change

## Scope

- **Backend**: Improve run-list attribution and summary context for identity scope, spend posture, and governance evidence.
- **UI**: Make `/runs` a clearer bridge into cost, policy, and identity investigation.
- **Docs**: Document run-list investigation as part of the main cross-suite explanation workflow.
- **Postman**: Add any new run-list filter or summary fields that expose policy/spend context.
- **Scripts/Examples**: Add a run-ledger walkthrough that includes spend and enforcement interpretation.

## Acceptance Criteria

1. `/runs` exposes practical identity, spend, and policy context without requiring immediate deep drill-ins.
2. Investigators can move from a run row into the correct runtime, FinOps, or governance owner surfaces.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
