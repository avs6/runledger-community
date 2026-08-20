# WU-017: Rate Limits Scope and Throttle Explainability Refresh

- **Status**: NOT_STARTED
- **Bundle**: 02-Gateway & Routing - Bundle C (Performance and Traffic Controls)
- **Target**: 02-GATEWAY-AND-ROUTING/Rate limits (`/rate-limits` compatibility, `/gateway` owner surface)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Rate limits | FinOps: Budget detail | 02x05 | GAP | PARTIAL |
| Gateway: Rate limits | FinOps: Budget notifications | 02x05 | N/A | PARTIAL |
| Gateway: Rate limits | FinOps: Chargeback | 02x05 | N/A | PARTIAL |
| Gateway: Rate limits | FinOps: Ledger | 02x05 | N/A | PARTIAL |
| Gateway: Rate limits | Org: Access groups | 02x01 | GAP | PARTIAL |
| Gateway: Rate limits | Org: Onboarding | 02x01 | PARTIAL | STRONG |
| Gateway: Rate limits | Observe: Workspace dashboard | 02x03 | N/A | PARTIAL |
| Gateway: Rate limits | Observe: Analytics overview | 02x03 | N/A | PARTIAL |
| Gateway: Rate limits | Observe: Model usage | 02x03 | N/A | PARTIAL |
| Gateway: Rate limits | Observe: Outcomes and ROI | 02x03 | N/A | PARTIAL |
| Gateway: Rate limits | Safety: Governance pack | 02x04 | N/A | PARTIAL |
| Gateway: Rate limits | Build: Evaluation studio | 02x06 | PARTIAL | STRONG |
| Gateway: Rate limits | Build: Experiments | 02x06 | PARTIAL | STRONG |
| Gateway: Rate limits | Build: Optimization opportunities | 02x06 | PARTIAL | STRONG |
| Gateway: Rate limits | Build: Optimization simulator | 02x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/GAP-MATRIX.md` — Rate limits row
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Rate limits cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Rate limits
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Rate limits
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Rate limits
- `05-FINOPS/COHESION-MATRIX.md` — their view of Rate limits
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Rate limits
- `02-GATEWAY-AND-ROUTING/DELIVERY-STATUS.md` — 4.9 / 6.5 / 6.7 if delivery changes

## Scope

- **Backend**: Strengthen throttle/quota explanation, actor-scope attribution, and downstream evidence/savings contracts.
- **UI**: Make `/gateway` rate-limit posture easier to understand across user scope, API-key tiers, model quotas, and downstream runtime outcomes.
- **Docs**: Clarify the technical-throttle vs financial-policy split without losing the real product relationship.
- **Postman**: Add any missing rate-overview, actor-scope, or throttle-evidence requests.
- **Scripts/Examples**: Add throttle/quota walkthroughs tied to request outcomes and optimization decisions.

## Acceptance Criteria

1. Rate-limit posture is understandable through user/access-group scope, request outcomes, and optimization surfaces.
2. Operators can trace throttling and quota decisions into the relevant observe, build, and FinOps owner surfaces.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
