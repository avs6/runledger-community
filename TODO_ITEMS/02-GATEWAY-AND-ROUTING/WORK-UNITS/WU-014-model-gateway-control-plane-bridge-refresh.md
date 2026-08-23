# WU-014: Model Gateway Control Plane Bridge Refresh

- **Status**: COMPLETED
- **Bundle**: 02-Gateway & Routing - Bundle A (Provider Catalog and Routing Control Plane)
- **Target**: 02-GATEWAY-AND-ROUTING/Model gateway (`/gateway`)
- **Created**: 2026-08-16
- **Completed**: 2026-08-22

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Model gateway | Org: Organization profile | 02x01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: Onboarding | 02x01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: Users | 02x01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: Access groups | 02x01 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Workspace dashboard | 02x03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Outcomes and ROI | 02x03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Analytics users | 02x03 | PARTIAL | STRONG |
| Gateway: Model gateway | Observe: Analytics user detail | 02x03 | PARTIAL | STRONG |
| Gateway: Model gateway | Safety: Approvals | 02x04 | PARTIAL | STRONG |
| Gateway: Model gateway | Safety: Audit log | 02x04 | PARTIAL | STRONG |
| Gateway: Model gateway | Safety: Governance pack | 02x04 | PARTIAL | STRONG |
| Gateway: Model gateway | Platform: All organizations | 02x07 | PARTIAL | STRONG |
| Gateway: Model gateway | Platform: Platform settings | 02x07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/GAP-MATRIX.md` — Model gateway row
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Model gateway cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Model gateway
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Model gateway
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Model gateway
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Model gateway
- `02-GATEWAY-AND-ROUTING/DELIVERY-STATUS.md` — 4.1 / 4.8 if delivery changes

## Scope

- **Backend**: Add or normalize gateway-posture summaries and runtime evidence contracts that downstream org, observe, and platform surfaces can consume.
- **UI**: Make `/gateway` a clearer cross-suite control plane with stronger drill-through and posture summaries.
- **Docs**: Tighten gateway control-plane guidance and Rust/Python runtime ownership explanation.
- **Postman**: Add any new control-plane summary requests or missing runtime-reference coverage.
- **Scripts/Examples**: Add a control-plane walkthrough covering route posture, runtime evidence, and governance handoff.

## Acceptance Criteria

1. `/gateway` provides clearer cross-suite control posture for org, observe, governance, and platform consumers.
2. Operators can explain runtime behavior, ownership, and evidence from the gateway surface itself.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
