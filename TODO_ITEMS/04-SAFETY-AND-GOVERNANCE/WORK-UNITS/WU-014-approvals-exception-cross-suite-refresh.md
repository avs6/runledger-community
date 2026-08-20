# WU-014: Approvals Exception Cross Suite Refresh

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - B (Exception and Response Workflows)
- **Target**: 04-SAFETY-AND-GOVERNANCE/approvals
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Approvals | FinOps: Budgets | 04x05 | PARTIAL | STRONG |
| Safety: Approvals | FinOps: Budget detail | 04x05 | PARTIAL | STRONG |
| Safety: Approvals | Org: Users | 04x01 | PARTIAL | STRONG |
| Safety: Approvals | Org: Workspaces | 04x01 | PARTIAL | STRONG |
| Safety: Approvals | Org: API keys | 04x01 | PARTIAL | STRONG |
| Safety: Approvals | Gateway: Model gateway | 04x02 | PARTIAL | STRONG |
| Safety: Approvals | Gateway: Guardrails | 04x02 | PARTIAL | STRONG |
| Safety: Approvals | Observe: Runs list | 04x03 | PARTIAL | STRONG |
| Safety: Approvals | Observe: Run detail | 04x03 | PARTIAL | STRONG |
| Safety: Approvals | Observe: Monitoring | 04x03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` - Approvals row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - Approvals cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - user and workspace approval-context view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - model and guardrail escalation view
- `03-OBSERVE/COHESION-MATRIX.md` - investigation and monitoring evidence view
- `05-FINOPS/COHESION-MATRIX.md` - budget-override and exception-cost view

## Scope

- **Backend**: Re-audit Approvals as the human exception path for budget, access, model, and high-risk governance decisions.
- **UI**: Improve clarity around what triggered approval, what scope it applies to, and what runtime or spend outcome follows.
- **Docs**: Document Approvals as a suite-wide escalation primitive rather than a narrow local queue.
- **Postman**: Keep approval policy and request flows aligned with broader exception-routing expectations.
- **Scripts/Examples**: Add scenarios for budget override, scoped access exception, and runtime-governance approval handling.

## Acceptance Criteria

1. Approvals are re-audited as a true cross-suite exception mechanism
2. Budget, scope, and runtime approval stories are explicitly covered
3. Investigation and monitoring pivots are explicitly covered
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
