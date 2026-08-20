# WU-013: Python Hot Path Migration Refresh

- **Status**: NOT_STARTED
- **Bundle**: 08-Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/review-refactored-gateway-modules
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

This planned-architecture family does not yet have a dedicated `COHESION-MATRIX.md`.
Close this work through `GAP-MATRIX.md`, `BLUEPRINT.md`, and the paired matrices below.

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` - refactored gateway modules row
- `08-PLANNED-ARCHITECTURE/BLUEPRINT.md` - Bundle A hot-path migration framing
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit remaining Python preflight and execution-support logic that still belongs on the Rust side.
- **UI**: Clarify any runtime-admin visibility needed to make the migration understandable to operators.
- **Docs**: Explain which gateway modules remain control-plane only and which should no longer own live request-path behavior.
- **Postman**: Remove ambiguous control-plane versus hot-path assumptions.
- **Scripts/Examples**: Add migration-validation scenarios that prove remaining hot-path helpers are accounted for.

## Acceptance Criteria

1. Remaining Python hot-path work is re-audited with explicit migration targets
2. Control-plane versus data-plane module ownership is clearly documented
3. Paired matrices and blueprint references are updated consistently
4. FEATURE-STATUS.md is updated
