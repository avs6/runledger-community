# WU-015: Budget Detail Drillback Refresh

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/budget-detail
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budget detail | Org: Organization profile | 05x01 | GAP | STRONG |
| FinOps: Budget detail | Org: Users | 05x01 | GAP | STRONG |
| FinOps: Budget detail | Org: Access groups | 05x01 | GAP | STRONG |
| FinOps: Budget detail | Org: API keys | 05x01 | GAP | STRONG |
| FinOps: Budget detail | Gateway: Response cache | 05x02 | GAP | STRONG |
| FinOps: Budget detail | Gateway: Rate limits | 05x02 | GAP | STRONG |
| FinOps: Budget detail | Observe: Run detail | 05x03 | PARTIAL | STRONG |
| FinOps: Budget detail | Observe: Request flow | 05x03 | PARTIAL | STRONG |
| FinOps: Budget detail | Safety: Audit log | 05x04 | PARTIAL | STRONG |
| FinOps: Budget detail | Build: Workflow detail | 05x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/GAP-MATRIX.md` - Budget detail row
- `05-FINOPS/COHESION-MATRIX.md` - Budget detail cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - org, access-group, and API key drillback view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - cache and rate-control drillback view
- `03-OBSERVE/COHESION-MATRIX.md` - run and request investigation view
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - audit evidence view
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - workflow-improvement drillback view

## Scope

- **Backend**: Re-audit Budget Detail as the main drillback surface for scope resolution, runtime consequences, and evidence context.
- **UI**: Make it easier to trace a budget from summary into cache effects, throttles, scope owners, and related workflow usage.
- **Docs**: Document the detail route as a true investigative surface, not only a nested budget subpage.
- **Postman**: Keep detail, history, and related-evidence flows aligned with the intended operator workflow.
- **Scripts/Examples**: Add a scenario that starts from a breach and drills into scope owners, runtime context, and related workflow activity.

## Acceptance Criteria

1. Budget Detail is re-audited as the main FinOps drillback surface
2. Scope-owner, runtime, and evidence relationships are explicitly covered
3. Workflow and optimization drillback relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
