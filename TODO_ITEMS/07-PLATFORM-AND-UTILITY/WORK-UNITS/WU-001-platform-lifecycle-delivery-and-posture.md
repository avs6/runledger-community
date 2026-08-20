# WU-001: Platform lifecycle delivery and posture completion

- **Status**: NOT_STARTED
- **Bundle**: Platform & Utility - Platform Lifecycle Control Plane
- **Target**: 07-PLATFORM-AND-UTILITY/All organizations (`/organizations`)
- **Created**: 2026-08-15
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| All organizations | Budgets | 07x05 | PARTIAL | STRONG |
| All organizations | Billing periods | 07x05 | PARTIAL | STRONG |
| All organizations | Chargeback | 07x05 | PARTIAL | STRONG |
| All organizations | Ledger | 07x05 | PARTIAL | STRONG |
| All organizations | Onboarding | 07x01 | PARTIAL | STRONG |
| All organizations | Workspaces | 07x01 | PARTIAL | STRONG |
| All organizations | API keys | 07x01 | PARTIAL | STRONG |
| All organizations | Platform settings | 07x07 | PARTIAL | STRONG |
| All organizations | Model gateway | 07x02 | PARTIAL | STRONG |
| All organizations | Guardrails | 07x04 | PARTIAL | STRONG |
| All organizations | Audit log | 07x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - All organizations row
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - All organizations cells
- `05-FINOPS/COHESION-MATRIX.md` - their view of All organizations lifecycle and FinOps summaries
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - their view of lifecycle handoff into onboarding, workspaces, and API keys
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - their view of platform-admin gateway posture summaries
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - their view of audit and guardrail posture summaries
- `07-PLATFORM-AND-UTILITY/DELIVERY-STATUS.md` - platform lifecycle delivery completeness if support surfaces change

## Scope

- **Backend**: Add or normalize organization-level summary payloads for billing, lifecycle posture, gateway readiness, and governance posture without moving ownership out of the underlying feature families.
- **UI**: Strengthen `/organizations` as the platform-admin lifecycle hub with downstream posture cards, clearer lifecycle filters, and explicit handoff paths into org-owned setup surfaces.
- **Docs**: Document `/organizations` as the canonical platform lifecycle owner and explain the boundaries between org lifecycle, org settings, and platform settings.
- **Postman**: Add or refresh organization lifecycle and posture-summary coverage so platform-admin entry points are exercised as first-class API paths.
- **Scripts/Examples**: Add or refresh realistic platform-admin org lifecycle simulations, including create, suspend, reactivate, and posture review flows.

## Acceptance Criteria

1. `/organizations` remains the canonical platform lifecycle owner for create, update, suspend, reactivate, and delete flows.
2. Platform-admin users can see useful downstream posture summaries for FinOps, gateway, and governance without those surfaces being absorbed into `/organizations`.
3. Support surfaces for All organizations are materially improved across docs, Postman, and scripts/examples.
4. All listed cohesion cells updated to target state.
5. All paired feature files updated.
6. `FEATURE-STATUS.md` dashboard updated.
