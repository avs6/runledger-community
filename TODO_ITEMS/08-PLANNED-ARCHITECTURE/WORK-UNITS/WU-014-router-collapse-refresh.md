# WU-014: Router Collapse Refresh

- **Status**: NOT_STARTED
- **Bundle**: 08-Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/collapse-runledger-router
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

This planned-architecture family does not yet have a dedicated `COHESION-MATRIX.md`.
Close this work through `GAP-MATRIX.md`, `BLUEPRINT.md`, and the paired matrices below.

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` - runledger-router collapse row
- `08-PLANNED-ARCHITECTURE/BLUEPRINT.md` - Bundle A sidecar-collapse framing
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit the sidecar collapse so routing classification clearly lands inside the Rust runtime.
- **UI**: Identify any operator-facing service-topology or runtime-status implications from removing the sidecar.
- **Docs**: Remove architectural ambiguity around `runledger-router` as a distinct service.
- **Postman**: Keep runtime-support and control-plane route docs aligned with the merged service topology.
- **Scripts/Examples**: Add service-topology scenarios that validate the merged runtime model.

## Acceptance Criteria

1. The sidecar collapse target is re-audited as a concrete architecture migration
2. Service-topology and operator-workflow implications are explicitly covered
3. Paired matrices and blueprint references are updated consistently
4. FEATURE-STATUS.md is updated
