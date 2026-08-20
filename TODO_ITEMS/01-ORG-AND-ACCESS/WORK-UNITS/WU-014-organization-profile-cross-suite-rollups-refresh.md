# WU-014: Organization Profile Cross-Suite Rollups Refresh

- **Status**: NOT_STARTED
- **Bundle**: 01-Org & Access - Bundle A (Organization Foundation and Lifecycle)
- **Target**: 01-ORG-AND-ACCESS/Organization profile (`/organization`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Organization profile | FinOps: Budget detail | 01x05 | GAP | PARTIAL |
| Org: Organization profile | FinOps: Billing period detail | 01x05 | GAP | PARTIAL |
| Org: Organization profile | Observe: Billing summary | 01x03 | GAP | PARTIAL |
| Org: Organization profile | Observe: Outcomes and ROI | 01x03 | GAP | PARTIAL |
| Org: Organization profile | Observe: Analytics users | 01x03 | GAP | PARTIAL |
| Org: Organization profile | Safety: Tool registry | 01x04 | GAP | PARTIAL |
| Org: Organization profile | Safety: Tool policies | 01x04 | GAP | PARTIAL |
| Org: Organization profile | Safety: Governance pack | 01x04 | GAP | PARTIAL |
| Org: Organization profile | Safety: Tags | 01x04 | GAP | PARTIAL |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Organization profile row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Organization profile cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Organization profile
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Organization profile
- `05-FINOPS/COHESION-MATRIX.md` — their view of Organization profile
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 1.2 if delivery surfaces change

## Scope

- **Backend**: Add or normalize org-level summary/read-only posture endpoints for spend, billing, outcomes, user analytics, and governance state.
- **UI**: Strengthen `/organization` as the org-admin rollup surface with clear drill-through to FinOps, Observe, and Governance.
- **Docs**: Document `/organization` as the top-level org posture surface rather than a metadata-only console.
- **Postman**: Add org-summary requests if new org rollup endpoints are introduced.
- **Scripts/Examples**: Add a validation flow showing org-level posture and drill-through.

## Acceptance Criteria

1. `/organization` exposes real rollups or drill-throughs for budget detail, billing detail, outcomes, user analytics, and governance posture.
2. Org admins can navigate from Organization profile into downstream FinOps, Observe, and Governance owner surfaces without ambiguity.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
