# WU-006: Budget Control × Platform Scope

- **Status**: NOT_STARTED
- **Bundle**: 05-FinOps - A (Spend Control Plane)
- **Target**: 05-FINOPS/Budgets, Budget detail, Budget overrides
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budget detail | Platform: All organizations | 05×07 | GAP | STRONG |
| FinOps: Budgets | Platform: All organizations | 05×07 | PARTIAL | STRONG |
| FinOps: Budgets | Platform: Platform settings | 05×07 | PARTIAL | STRONG |
| FinOps: Budget detail | Platform: Platform settings | 05×07 | PARTIAL | STRONG |
| FinOps: Budget overrides | Platform: All organizations | 05×07 | PARTIAL | STRONG |
| FinOps: Budget overrides | Platform: Platform settings | 05×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `05-FINOPS/COHESION-MATRIX.md` — Budgets/Budget detail/Overrides × Platform cells
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Budget surfaces
- `FEATURE-STATUS.md` — 05-A × 07 counts

## Scope

- **Backend**: Budget detail must support cross-org platform-level spend views. Platform operators need aggregate budget posture across all organizations. Platform settings should show budget governance configuration.
- **UI**: All organizations view should show per-org budget posture summary. Budget detail should support platform-scope rollups. Platform settings should expose budget governance defaults and platform-level budget controls.
- **Docs**: Document platform-level budget governance.
- **Postman**: Add platform-scope budget endpoints.
- **Scripts/Examples**: Add example viewing cross-org budget posture from platform scope.

## Acceptance Criteria

1. All organizations shows per-org budget posture
2. Budget detail supports platform-scope rollups
3. Platform settings exposes budget governance controls
4. All listed cohesion cells updated to target state
5. All paired feature files updated
6. FEATURE-STATUS.md dashboard updated
