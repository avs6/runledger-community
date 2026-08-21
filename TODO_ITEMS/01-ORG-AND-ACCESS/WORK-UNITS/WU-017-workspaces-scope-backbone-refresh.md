# WU-017: Workspaces Scope Backbone Refresh

- **Status**: DONE
- **Bundle**: 01-Org & Access - Bundle B (Identity and Scope Control)
- **Target**: 01-ORG-AND-ACCESS/Workspaces (`/workspace`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Workspaces | FinOps: Budget detail | 01x05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Budget overrides | 01x05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Budget notifications | 01x05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Billing periods | 01x05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Billing period detail | 01x05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Chargeback | 01x05 | PARTIAL | STRONG |
| Org: Workspaces | FinOps: Ledger | 01x05 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Sessions list | 01x03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Session detail | 01x03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Model usage | 01x03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Analytics economics | 01x03 | PARTIAL | STRONG |
| Org: Workspaces | Observe: Cost and savings | 01x03 | PARTIAL | STRONG |
| Org: Workspaces | Safety: Policy dry run | 01x04 | PARTIAL | STRONG |
| Org: Workspaces | Safety: Approvals | 01x04 | PARTIAL | STRONG |
| Org: Workspaces | Safety: Data capture | 01x04 | PARTIAL | STRONG |
| Org: Workspaces | Safety: Alert rules | 01x04 | PARTIAL | STRONG |
| Org: Workspaces | Safety: Audit log | 01x04 | PARTIAL | STRONG |
| Org: Workspaces | Safety: Governance pack | 01x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Workspaces row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Workspaces cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Workspaces
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Workspaces
- `05-FINOPS/COHESION-MATRIX.md` — their view of Workspaces
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 1.3 if delivery changes

## Scope

- **Backend**: Strengthen workspace-summary and drill-through contracts for spend, sessions, policy evidence, and governance posture.
- **UI**: Make `/workspace` the unmistakable scope backbone with stronger links into FinOps, Observe, and Governance owner surfaces.
- **Docs**: Reinforce workspaces as the canonical scope boundary across the product.
- **Postman**: Add workspace-summary or workspace-posture requests if needed.
- **Scripts/Examples**: Add a workspace lifecycle example that crosses runtime, spend, and governance.

## Acceptance Criteria

1. Workspace scope is clearly visible across spend, sessions, governance, and evidence workflows.
2. `/workspace` supports practical drill-through into the owner surfaces that depend on workspace scope.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
