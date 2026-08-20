# WU-016: Users Scope Attribution and Governance Refresh

- **Status**: NOT_STARTED
- **Bundle**: 01-Org & Access - Bundle B (Identity and Scope Control)
- **Target**: 01-ORG-AND-ACCESS/Users (`/users`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Users | FinOps: Budgets | 01x05 | GAP | PARTIAL |
| Org: Users | FinOps: Budget detail | 01x05 | GAP | PARTIAL |
| Org: Users | FinOps: Billing periods | 01x05 | GAP | PARTIAL |
| Org: Users | FinOps: Billing period detail | 01x05 | GAP | PARTIAL |
| Org: Users | FinOps: Chargeback | 01x05 | GAP | PARTIAL |
| Org: Users | Observe: Analytics overview | 01x03 | GAP | PARTIAL |
| Org: Users | Observe: Model usage | 01x03 | GAP | PARTIAL |
| Org: Users | Observe: Analytics economics | 01x03 | GAP | PARTIAL |
| Org: Users | Observe: Cost and savings | 01x03 | GAP | PARTIAL |
| Org: Users | Observe: Outcomes and ROI | 01x03 | GAP | PARTIAL |
| Org: Users | Safety: Tool registry | 01x04 | GAP | PARTIAL |
| Org: Users | Safety: Tool policies | 01x04 | GAP | PARTIAL |
| Org: Users | Safety: Approvals | 01x04 | GAP | PARTIAL |
| Org: Users | Safety: Data capture | 01x04 | GAP | PARTIAL |
| Org: Users | Safety: Audit log | 01x04 | GAP | PARTIAL |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Users row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Users cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Users
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Users
- `05-FINOPS/COHESION-MATRIX.md` — their view of Users
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 1.4 / 1.6 if delivery changes

## Scope

- **Backend**: Add or normalize user-attribution, user-scope summary, and governance-evidence linkage where user posture is currently indirect.
- **UI**: Strengthen `/users` with user-to-runtime, user-to-spend, and user-to-governance visibility.
- **Docs**: Document users as an operational identity surface, not just CRUD.
- **Postman**: Cover any new attribution or user-summary endpoints.
- **Scripts/Examples**: Add a user-scope walkthrough showing memberships, usage, and governance posture.

## Acceptance Criteria

1. `/users` exposes real downstream identity context for spend, observability, and governance.
2. Operators can understand where a user is active and how that user participates in runtime or exception workflows.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
