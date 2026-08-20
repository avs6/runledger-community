# WU-015: Consumer Migration Refresh

- **Status**: NOT_STARTED
- **Bundle**: 08-Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/legacy-python-gateway-deprecation
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

This planned-architecture family does not yet have a dedicated `COHESION-MATRIX.md`.
Close this work through `GAP-MATRIX.md`, `BLUEPRINT.md`, and the paired matrices below.

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` - legacy Python gateway deprecation row
- `08-PLANNED-ARCHITECTURE/BLUEPRINT.md` - Bundle A consumer-migration framing
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md`
- `03-OBSERVE/COHESION-MATRIX.md`
- `05-FINOPS/COHESION-MATRIX.md`
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md`

## Scope

- **Backend**: Re-audit lingering Python-inline gateway assumptions across generated assets and support surfaces.
- **UI**: Clarify any remaining product references that still imply the old runtime path.
- **Docs**: Finish normalizing control-plane/data-plane guidance across docs and examples.
- **Postman**: Remove or clearly mark stale inline-runtime assumptions.
- **Scripts/Examples**: Align benchmark, scenario, and example coverage to the Rust runtime model.

## Acceptance Criteria

1. Consumer migration cleanup is re-audited across docs, Postman, scripts, and examples
2. Legacy Python runtime assumptions are explicitly identified and tracked
3. Paired matrices and blueprint references are updated consistently
4. FEATURE-STATUS.md is updated
