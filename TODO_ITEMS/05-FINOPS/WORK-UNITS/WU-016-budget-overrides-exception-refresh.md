# WU-016: Budget Overrides Exception Refresh

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/budget-overrides
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budget overrides | Org: Workspaces | 05x01 | PARTIAL | STRONG |
| FinOps: Budget overrides | Org: Access groups | 05x01 | PARTIAL | STRONG |
| FinOps: Budget overrides | Gateway: Model gateway | 05x02 | PARTIAL | STRONG |
| FinOps: Budget overrides | Gateway: Rate limits | 05x02 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Runs list | 05x03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Observe: Request explorer | 05x03 | PARTIAL | STRONG |
| FinOps: Budget overrides | Safety: Approvals | 05x04 | PARTIAL | STRONG |
| FinOps: Budget overrides | Safety: Alert rules | 05x04 | PARTIAL | STRONG |
| FinOps: Budget overrides | Safety: Governance pack | 05x04 | PARTIAL | STRONG |
| FinOps: Budget overrides | Platform: Plugins | 05x07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/GAP-MATRIX.md` - Budget overrides row
- `05-FINOPS/COHESION-MATRIX.md` - Budget overrides cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - workspace and access-group exception view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - gateway and rate-limit exception view
- `03-OBSERVE/COHESION-MATRIX.md` - investigative exception-history view
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - approvals, alerts, and evidence view
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - platform governance view

## Scope

- **Backend**: Re-audit Overrides as the governed spend-exception mechanism, including approval, activation, revocation, and runtime side effects.
- **UI**: Clarify override status, trigger source, approval linkage, and related runtime or monitoring context.
- **Docs**: Teach overrides as a governed exception flow inside Budgets, not a detached admin list.
- **Postman**: Keep override lifecycle and approval-linked scenarios aligned with the live product story.
- **Scripts/Examples**: Add scenarios for temporary override approval, activation, observation, and evidence export.

## Acceptance Criteria

1. Budget Overrides are re-audited as a governed exception flow
2. Approval, runtime, and evidence relationships are explicitly covered
3. Workspace, access-group, and platform-governance relationships are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
