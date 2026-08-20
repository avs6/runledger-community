# WU-002: Platform settings convergence and delivery completeness

- **Status**: NOT_STARTED
- **Bundle**: Platform & Utility - Platform Settings Convergence
- **Target**: 07-PLATFORM-AND-UTILITY/Platform settings (`/settings`)
- **Created**: 2026-08-15
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Platform settings | Budgets | 07x05 | PARTIAL | STRONG |
| Platform settings | Billing periods | 07x05 | PARTIAL | STRONG |
| Platform settings | Chargeback | 07x05 | PARTIAL | STRONG |
| Platform settings | Organization profile | 07x01 | PARTIAL | STRONG |
| Platform settings | Onboarding | 07x01 | PARTIAL | STRONG |
| Platform settings | Workspaces | 07x01 | PARTIAL | STRONG |
| Platform settings | API keys | 07x01 | PARTIAL | STRONG |
| Platform settings | All organizations | 07x07 | PARTIAL | STRONG |
| Platform settings | Model gateway | 07x02 | PARTIAL | STRONG |
| Platform settings | Guardrails | 07x04 | PARTIAL | STRONG |
| Platform settings | Telemetry | 07x03 | PARTIAL | STRONG |
| Platform settings | Audit log | 07x04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - Platform settings row
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - Platform settings cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - their view of platform/default setting boundaries
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - their view of platform defaults and gateway config ownership
- `03-OBSERVE/COHESION-MATRIX.md` - their view of telemetry and operational-posture linkage
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - their view of compliance defaults, audit evidence, and governance posture
- `05-FINOPS/COHESION-MATRIX.md` - their view of ledger and billing-default linkage
- `07-PLATFORM-AND-UTILITY/DELIVERY-STATUS.md` - platform settings delivery completeness

## Scope

- **Backend**: Normalize platform-settings contracts around retention, backup, storage posture, deployment profile, feature flags, and compliance defaults so the route behaves like one managed surface.
- **UI**: Rework `/settings` into a cohesive settings shell with consistent tabs, edit/save patterns, validation, summaries, and ownership cues.
- **Docs**: Consolidate platform-settings documentation so absorbed surfaces are described as one platform-defaults and compliance console.
- **Postman**: Fill in missing platform-settings coverage for each converged subarea and any shared summary endpoints introduced by the settings shell.
- **Scripts/Examples**: Add or refresh platform settings simulations that exercise end-to-end configuration changes and posture review flows.

## Acceptance Criteria

1. `/settings` behaves as one coherent platform-admin surface rather than a loose umbrella of uneven tabs.
2. Absorbed compliance and operational setting areas stay owned by Platform settings with clearer boundaries from org-level controls.
3. Postman and scripts/examples coverage for Platform settings is no longer partial.
4. All listed cohesion cells updated to target state.
5. All paired feature files updated.
6. `FEATURE-STATUS.md` dashboard updated.
