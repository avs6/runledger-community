# WU-003: Consumer Migration and Legacy Cleanup

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/Legacy Python gateway deprecation and consumer migration
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Legacy Python gateway deprecation | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. Gaps derived from GAP-MATRIX and BLUEPRINT cross-feature integration requirements.

## Cross-Feature Dependencies

- `02-GATEWAY-AND-ROUTING` — all gateway consumer-facing assets must reflect Rust runtime
- `03-OBSERVE` — observability examples must reference Rust execution traces
- `05-FINOPS` — cost tracking examples must reference Rust-native metering
- `06-BUILD-AND-IMPROVE` — playground and build surfaces must not reference stale Python completion paths

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — legacy deprecation row
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — consumer migration impacts
- `FEATURE-STATUS.md` — 08-A delivery counts

## Scope

- **Backend**: Remove stale Python-hosted completion references and inline-runtime assumptions. Keep management and analytics APIs on the Python control plane. Remove dead inline-runtime code from the Python gateway router.
- **UI**: Ensure no UI surface depends on deprecated Python-inline runtime paths. Update any UI flows that still assume Python-hosted completion.
- **Docs**: Move all live completion examples to `runledger-gateway-rs`. Migrate generated Postman/OpenAPI guidance to reflect the Rust runtime model. Update reference API docs.
- **Postman**: Migrate all gateway runtime collections to Rust-facing endpoints. Remove stale Python-inline runtime examples.
- **Scripts/Examples**: Update all scripts and examples to use the Rust data plane. Remove stale Python runtime examples. Add migration guide for consumers transitioning from Python to Rust endpoints.

## Acceptance Criteria

1. All consumer-facing assets reflect the Rust runtime model
2. No stale Python-inline runtime assumptions remain in docs/examples/scripts
3. Postman collections fully migrated to Rust-facing endpoints
4. Migration guide available for consumer transition
5. Dead inline-runtime code removed from Python gateway router
6. FEATURE-STATUS.md dashboard updated
