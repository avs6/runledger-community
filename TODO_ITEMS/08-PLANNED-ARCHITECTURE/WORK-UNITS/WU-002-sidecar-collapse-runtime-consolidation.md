# WU-002: Sidecar Collapse and Runtime Consolidation

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/Collapse runledger-router into the Rust gateway
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Collapse runledger-router into Rust gateway | PARTIAL | N/A | PARTIAL | PARTIAL | MISSING | MISSING | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. Gaps derived from GAP-MATRIX and BLUEPRINT cross-feature integration requirements.

## Cross-Feature Dependencies

- `02-GATEWAY-AND-ROUTING` — sidecar classifier contracts absorbed into Rust runtime
- `03-OBSERVE` — routing classification telemetry must survive the collapse
- `04-SAFETY-AND-GOVERNANCE` — governance enforcement on the routing path moves into Rust

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — runledger-router collapse row
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — routing ownership changes
- `FEATURE-STATUS.md` — 08-A delivery counts

## Scope

- **Backend**: Fold `runledger-router` intelligent routing classifier into `runledger-gateway-rs`. The data-plane path should become authenticate → preflight → classify → choose route → execute without bouncing into a separate Python microservice. Simplify Docker Compose and service topology. Absorb sidecar classifier contracts into Rust-facing runtime APIs.
- **UI**: No direct UI changes. Gateway UI continues to speak to control-plane ownership.
- **Docs**: Update architecture docs and deployment guides to reflect the simplified service topology. Remove references to `runledger-router` as a separate service.
- **Postman**: Migrate any `runledger-router`-specific API references into the unified Rust runtime contract.
- **Scripts/Examples**: Update Docker Compose examples and deployment scripts to remove the sidecar.

## Acceptance Criteria

1. `runledger-router` sidecar is fully absorbed into `runledger-gateway-rs`
2. Docker Compose and service topology are simplified
3. Routing classification happens inside the Rust data plane
4. Architecture docs and deployment guides reflect the consolidated topology
5. FEATURE-STATUS.md dashboard updated
