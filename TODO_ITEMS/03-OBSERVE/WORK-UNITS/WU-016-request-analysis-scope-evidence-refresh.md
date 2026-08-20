# WU-016: Request Analysis Scope and Evidence Refresh

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - Bundle B (Request, Run, and Session Investigation)
- **Target**: 03-OBSERVE/Request flow + Request explorer (`/request-flow`, `/request-explorer`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Request flow | Org: Access groups | 03x01 | GAP | PARTIAL |
| Observe: Request explorer | Org: Access groups | 03x01 | GAP | PARTIAL |
| Observe: Request flow | FinOps: Budget detail | 03x05 | PARTIAL | STRONG |
| Observe: Request explorer | FinOps: Budget detail | 03x05 | PARTIAL | STRONG |
| Observe: Request flow | Gateway: Guardrails | 03x02 | PARTIAL | STRONG |
| Observe: Request explorer | Gateway: Guardrails | 03x02 | PARTIAL | STRONG |
| Observe: Request flow | Safety: Approvals | 03x04 | N/A | PARTIAL |
| Observe: Request explorer | Safety: Data capture | 03x04 | N/A | PARTIAL |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Request flow / Request explorer rows
- `03-OBSERVE/COHESION-MATRIX.md` — request-analysis cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Request flow / explorer
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Request flow / explorer
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Request flow / explorer
- `05-FINOPS/COHESION-MATRIX.md` — their view of Request flow / explorer
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.6 / 3.7 if delivery surfaces change

## Scope

- **Backend**: Improve request-analysis context for access-group scope, budget linkage, and guardrail/evidence interpretation.
- **UI**: Make request flow and explorer stronger at explaining why traffic was blocked, throttled, cached, or budget-impacted.
- **Docs**: Update request-analysis docs to reflect the live investigation contract and cross-suite pivots.
- **Postman**: Add or refine request-analysis requests if new evidence fields are introduced.
- **Scripts/Examples**: Add a request-causality walkthrough covering budget, policy, and scope explanation.

## Acceptance Criteria

1. Request-analysis surfaces explain traffic outcomes through scope, spend, and policy evidence more clearly.
2. Investigators can trace a request into the right owner surfaces without losing context.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
