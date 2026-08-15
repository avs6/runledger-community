# WU-001: Rust Runtime Boundary Cleanup

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/High-performance gateway service split, Review refactored gateway modules
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| High-performance gateway service split | PARTIAL | MISSING | PARTIAL | PARTIAL | MISSING | MISSING | GAP-MATRIX §9 |
| Review refactored gateway modules | PARTIAL | N/A | PARTIAL | PARTIAL | MISSING | MISSING | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. Gaps derived from GAP-MATRIX and BLUEPRINT cross-feature integration requirements.

## Cross-Feature Dependencies

- `02-GATEWAY-AND-ROUTING` — runtime split reshapes gateway ownership boundary
- `03-OBSERVE` — live execution traces must flow from Rust data plane
- `05-FINOPS` — enforcement and cost tracking must survive the split
- `04-SAFETY-AND-GOVERNANCE` — policy enforcement moves to Rust hot path

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — gateway service split and module review rows
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — gateway ownership boundary changes
- `FEATURE-STATUS.md` — 08-A delivery counts

## Scope

- **Backend**: Review Python gateway modules (`gateway.py`, `gateway_shared.py`, `gateway_legacy.py`, `gateway_routing.py`, `gateway_passthrough.py`, `gateway_runtime.py`, `gateway_observability.py`). Identify remaining hot-path logic still living in Python. Move execution-critical logic to `runledger-gateway-rs`. Establish clear runtime event and decision contracts between Rust and Python.
- **UI**: Gateway UI should not depend on deprecated Python-inline runtime paths. Runtime health and capability visibility should improve.
- **Docs**: Document the control-plane vs data-plane boundary clearly. Update architecture docs to reflect the Rust runtime model.
- **Postman**: Begin migrating gateway runtime examples to Rust-facing contracts.
- **Scripts/Examples**: Add examples demonstrating the Rust data-plane execution path.

## Acceptance Criteria

1. All hot-path execution logic identified and migrated to Rust
2. Python gateway modules are clean control-plane-only code
3. Runtime event contracts between Rust and Python are explicit
4. Architecture docs reflect the split boundary
5. FEATURE-STATUS.md dashboard updated
