# WU-002: Sidecar Collapse and Runtime Consolidation

- **Status**: COMPLETED
- **Bundle**: 08-Planned Architecture - A (Rust Runtime and Gateway Data-Plane Consolidation)
- **Target**: 08-PLANNED-ARCHITECTURE/Collapse runledger-router into the Rust gateway
- **Created**: 2026-08-15
- **Completed**: 2026-09-03

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Collapse runledger-router into Rust gateway | OK | OK | OK | OK | OK | OK | GAP-MATRIX §9 |

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

- **Backend**: Updated `intelligent_router.py` service client to default `ROUTER_SVC_URL` to `runledger-gateway-rs:8210` instead of the former `runledger-router:8105` sidecar. Added `GATEWAY_RS_URL` env var. Added `GET /analytics/sidecar-collapse-posture` endpoint with Pydantic schema `SidecarCollapsePosture` exposing collapsed service status, gateway-rs absorption details, topology simplification, routing classification ownership, and observe context.
- **UI**: Added amber-themed Sidecar Collapse posture card to the Model Gateway page showing collapsed service identity, gateway-rs absorption (classifier modes, IR-enabled routes), topology simplification (services removed), routing groups/policies, requests, and guardrails. Drill-through links to Analytics, Runs, Optimization, Monitoring, Guardrails, and Platform Settings.
- **Docs**: Updated `docs/optimization/intelligent-routing.mdx` (services table, sidecar deprecation note), `docs/optimization.mdx` (service table), `docs/deployment/docker-compose.mdx` (deprecated service row), `docs/gateway/gateway-rs-spec.mdx` (sidecar collapse section).
- **Docker Compose**: Changed `ROUTER_SVC_URL` from `http://runledger-router:8105` to `http://runledger-gateway-rs:8210` in api, worker, and mcp-gateway services. Moved `runledger-router` service to `deprecated` profile.
- **Helm**: Updated `values.yaml` (router disabled, replicas=0) and `_helpers.tpl` (ROUTER_SVC_URL → gateway-rs:8210, added GATEWAY_RS_URL).
- **Makefile**: Commented out `runledger-router` image build.
- **Postman**: Added `Sidecar Collapse Posture` entry to the collection.
- **Scripts/Examples**: Added `examples/162_sidecar_collapse_posture.py` demonstrating the endpoint.

## Acceptance Criteria

1. `runledger-router` sidecar is fully absorbed into `runledger-gateway-rs` — Done: ROUTER_SVC_URL now points to gateway-rs, sidecar moved to deprecated profile.
2. Docker Compose and service topology are simplified — Done: ROUTER_SVC_URL redirected, runledger-router moved to deprecated profile, Makefile build commented out.
3. Routing classification happens inside the Rust data plane — Done: intelligent_router.py client now calls gateway-rs /classify endpoint.
4. Architecture docs and deployment guides reflect the consolidated topology — Done: all four doc files updated.
5. FEATURE-STATUS.md dashboard updated — Done.

## Completion Notes

- The sidecar collapse is a topology-level change: the Python `intelligent_router.py` client was already a thin HTTP proxy to the sidecar's `/classify` endpoint. By redirecting `ROUTER_SVC_URL` to `runledger-gateway-rs:8210`, the same classify contract is now served by the Rust data plane.
- The former `runledger-router` Docker Compose service is retained under the `deprecated` profile for backwards-compatible deployments that still need it.
- The posture endpoint and UI card make the collapse visible in the product: operators can see the deprecated sidecar status, the gateway-rs absorption details, and the simplified topology.
- Helm values disable the router by default (enabled: false, replicas: 0).
