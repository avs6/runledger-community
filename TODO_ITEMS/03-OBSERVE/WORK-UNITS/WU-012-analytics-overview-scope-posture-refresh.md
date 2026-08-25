# WU-012: Analytics Overview Scope Posture Refresh

- **Status**: COMPLETED
- **Bundle**: 03-Observe - Bundle A (Overview and Scoped Entry Points)
- **Target**: 03-OBSERVE/Analytics overview (`/analytics`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-25

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Analytics overview | Org: Access groups | 03x01 | GAP | PARTIAL |
| Observe: Analytics overview | Org: API keys | 03x01 | GAP | PARTIAL |
| Observe: Analytics overview | Gateway: Guardrails | 03x02 | PARTIAL | STRONG |
| Observe: Analytics overview | Gateway: Response cache | 03x02 | PARTIAL | STRONG |
| Observe: Analytics overview | Gateway: Rate limits | 03x02 | PARTIAL | STRONG |
| Observe: Analytics overview | Safety: Tool registry | 03x04 | N/A | PARTIAL |
| Observe: Analytics overview | Safety: Tool policies | 03x04 | N/A | PARTIAL |
| Observe: Analytics overview | Safety: Approvals | 03x04 | N/A | PARTIAL |
| Observe: Analytics overview | Safety: Data capture | 03x04 | N/A | PARTIAL |

## Paired Features (files to update)

- `03-OBSERVE/GAP-MATRIX.md` — Analytics overview row
- `03-OBSERVE/COHESION-MATRIX.md` — Analytics overview cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Analytics overview
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Analytics overview
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Analytics overview
- `03-OBSERVE/DELIVERY-STATUS.md` — 3.8 if delivery surfaces change

## Scope

- **Backend**: Enrich scoped-summary payloads with access-group, API-key, runtime-protection, and governance posture summaries.
- **UI**: Strengthen `/analytics` as the true top-level posture shell for scope, runtime, and governance signals.
- **Docs**: Teach `/analytics` as the canonical scoped overview and explain its cross-suite posture role.
- **Postman**: Add or update scoped-summary requests if new posture fields are introduced.
- **Scripts/Examples**: Add a scoped-overview walkthrough showing runtime, spend, and governance posture pivots.

## Acceptance Criteria

1. `/analytics` exposes practical overview posture for scope, runtime, and governance instead of generic summary cards only.
2. Operators can pivot from overview cards into the correct owner surfaces without ambiguity.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
