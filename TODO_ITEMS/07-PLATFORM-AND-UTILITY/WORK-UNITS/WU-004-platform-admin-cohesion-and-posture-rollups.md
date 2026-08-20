# WU-004: Platform admin cohesion and posture rollups

- **Status**: NOT_STARTED
- **Bundle**: Platform & Utility - Platform Posture Summaries and Admin Workflow Cohesion
- **Target**: 07-PLATFORM-AND-UTILITY/Platform admin workflow (`/organizations`, `/settings`, `/plugins`)
- **Created**: 2026-08-15
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| All organizations | Platform settings | 07x07 | PARTIAL | STRONG |
| All organizations | Monitoring | 07x03 | PARTIAL | STRONG |
| All organizations | Telemetry | 07x03 | PARTIAL | STRONG |
| All organizations | Governance pack | 07x04 | PARTIAL | STRONG |
| Platform settings | All organizations | 07x07 | PARTIAL | STRONG |
| Platform settings | Monitoring | 07x03 | STRONG | STRONG |
| Platform settings | Organization profile | 07x01 | PARTIAL | STRONG |
| Platform settings | Model gateway | 07x02 | PARTIAL | STRONG |
| Plugins | Evaluation studio | 07x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - All organizations, Platform settings, and Plugins rows where completion language changes
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - cross-surface platform-admin cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - their view of org handoff and setup posture
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - their view of platform-admin posture summaries
- `03-OBSERVE/COHESION-MATRIX.md` - their view of monitoring and telemetry rollups
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - their view of governance evidence summaries
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` - their view of plugin/setup entry points for builder workflows
- `07-PLATFORM-AND-UTILITY/DELIVERY-STATUS.md` - any delivery surfaces affected by shared posture and navigation work

## Scope

- **Backend**: Introduce only the shared summary payloads needed for a cohesive platform-admin journey across org lifecycle, platform defaults, and collapsed discovery entry points.
- **UI**: Improve top-level platform-admin navigation, posture rollups, and first-boot guidance so operators can move cleanly between `/organizations`, `/settings`, and onboarding-owned discovery flows.
- **Docs**: Present Platform and Utility as one coherent admin story with explicit ownership boundaries and no stale ghost-route language.
- **Postman**: Cover any shared posture-summary endpoints or cross-surface admin flows introduced to support the platform-admin journey.
- **Scripts/Examples**: Add or refresh platform-admin walkthroughs that connect lifecycle, settings, observability posture, and setup handoff in one realistic sequence.

## Acceptance Criteria

1. Platform-admin navigation and handoff between `/organizations`, `/settings`, and onboarding are materially clearer.
2. Shared posture rollups help operators understand gateway, observability, and governance readiness without duplicating those control planes.
3. Platform and Utility support surfaces describe one coherent admin workflow rather than disconnected leftovers.
4. All listed cohesion cells updated to target state.
5. All paired feature files updated.
6. `FEATURE-STATUS.md` dashboard updated.
