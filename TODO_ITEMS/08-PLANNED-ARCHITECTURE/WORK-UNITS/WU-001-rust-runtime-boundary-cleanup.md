# WU-001: Rust Runtime Boundary Cleanup

- **Status**: COMPLETED
- **Bundle**: 08-Planned Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/High-performance gateway service split, Review refactored gateway modules
- **Created**: 2026-08-15
- **Completed**: 2026-09-03

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| High-performance gateway service split | OK | OK | OK | OK | OK | OK | GAP-MATRIX §9 |
| Review refactored gateway modules | OK | OK | OK | OK | OK | OK | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. Gaps derived from GAP-MATRIX and BLUEPRINT cross-feature integration requirements.

## Cross-Feature Dependencies

- `02-GATEWAY-AND-ROUTING` — runtime split reshapes gateway ownership boundary
- `03-OBSERVE` — live execution traces must flow from Rust data plane
- `04-SAFETY-AND-GOVERNANCE` — policy enforcement moves to Rust hot path
- `05-FINOPS` — enforcement and cost tracking must survive the split

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — gateway service split and module review rows
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — gateway ownership boundary changes
- `FEATURE-STATUS.md` — 08-A delivery counts

## Scope

- **Backend**: Added `GET /analytics/gateway-runtime-boundary-posture` endpoint exposing Rust data plane status, Python control plane ownership, hot-path migration state, runtime contract inventory, and observe context. Pydantic schema `GatewayRuntimeBoundaryPosture` added to analytics schemas.
- **UI**: Added teal-themed Runtime Boundary posture card to the Model Gateway page showing data plane capabilities, direct HTTP routes, control plane modules, legacy stub status, runtime contracts, requests/cache hits, guardrails, and budgets. Drill-through links to Analytics, Runs, Monitoring, Budgets, Tool Policies, Guardrails, Audit Log, and Platform Settings.
- **Docs**: Updated `docs/gateway/gateway-rs-spec.mdx` with Runtime boundary posture API section documenting the endpoint shape and UI card.
- **Postman**: Added `Gateway Runtime Boundary Posture` entry to the collection.
- **Scripts/Examples**: Added `examples/161_gateway_runtime_boundary_posture.py` demonstrating the endpoint.

## Acceptance Criteria

1. ~~All hot-path execution logic identified and migrated to Rust~~ — Already complete: gateway-rs owns all live chat completion traffic, Python `/gateway/chat/completions` returns 410 GONE.
2. ~~Python gateway modules are clean control-plane-only code~~ — Already complete: gateway_routing (CRUD), gateway_runtime (preflight/finalize/snapshot contracts), gateway_observability (stats), gateway_passthrough (proxy), gateway_legacy (410 stub).
3. ~~Runtime event contracts between Rust and Python are explicit~~ — Already complete (preflight, finalize, resolve-api-key, provider-execute, route-result, mirror, signed events, snapshot). Now surfaced via the runtime boundary posture endpoint and UI card.
4. Architecture docs reflect the split boundary — Updated gateway-rs-spec.mdx with posture API documentation.
5. FEATURE-STATUS.md dashboard updated — Done.

## Completion Notes

- The Rust runtime boundary was already materially complete before this WU. The work focused on making the boundary **visible**: a dedicated posture endpoint, a UI card on the gateway page, and supporting delivery surfaces (docs, Postman, example).
- The posture endpoint surfaces both static architecture facts (service identity, capabilities, contract paths) and live workspace metrics (route counts, request volume, cache hits, guardrails, budgets).
- Gateway module review confirmed the refactored Python layout is clean control-plane-only code: gateway_routing.py (CRUD), gateway_runtime.py (internal contracts for Rust), gateway_observability.py (stats/health), gateway_passthrough.py (proxy), gateway_legacy.py (410 stub).
