# WU-012: Rust Gateway Split Posture Refresh

- **Status**: NOT_STARTED
- **Bundle**: 08-Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/high-performance-gateway-service-split
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

This planned-architecture family does not yet have a dedicated `COHESION-MATRIX.md`.
Close this work by updating the row notes in `GAP-MATRIX.md`, the bundle framing in
`BLUEPRINT.md`, and the paired feature-family cohesion matrices listed below.

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` - High-performance gateway service split row
- `08-PLANNED-ARCHITECTURE/BLUEPRINT.md` - Bundle A runtime-boundary framing
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - runtime ownership view
- `03-OBSERVE/COHESION-MATRIX.md` - live execution and telemetry view
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - governance enforcement ownership view
- `05-FINOPS/COHESION-MATRIX.md` - cost and runtime attribution view

## Scope

- **Backend**: Re-audit the split between Python control plane and Rust data plane as an operator-visible architecture boundary.
- **UI**: Define what runtime health, capability, and deprecated-path visibility should surface in product.
- **Docs**: Tighten the split narrative so the end-state is unambiguous.
- **Postman**: Keep control-plane and runtime-support APIs aligned with the split model.
- **Scripts/Examples**: Add runtime-topology and migration-path examples that reinforce the true ownership boundary.

## Acceptance Criteria

1. The Rust/Python boundary is re-audited as a stable architecture contract
2. Product-surface implications for health, visibility, and deprecated paths are explicitly covered
3. Paired matrices and blueprint references are updated consistently
4. FEATURE-STATUS.md is updated
