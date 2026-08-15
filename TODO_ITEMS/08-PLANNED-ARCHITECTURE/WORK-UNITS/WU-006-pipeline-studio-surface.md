# WU-006: Pipeline Studio and Flow Builder

- **Status**: NOT_STARTED
- **Bundle**: 08-Planned Architecture - C (Pipeline, API, and Embedded Product Surfaces)
- **Target**: 08-PLANNED-ARCHITECTURE/Pipeline studio and flow builder
- **Created**: 2026-08-15
- **Completed**:

## Delivery Gaps to Close

| Feature | Backend | UI | Actions | Docs | Postman | Scripts | Source |
|---------|---------|-----|---------|------|---------|---------|--------|
| Pipeline studio and flow builder | MISSING | MISSING | MISSING | PARTIAL | MISSING | MISSING | GAP-MATRIX §9 |

Note: No COHESION-MATRIX exists for Planned Architecture. This is a net-new surface with the most MISSING cells in the family.

## Cross-Feature Dependencies

- `02-GATEWAY-AND-ROUTING` — pipeline visualizes ingest, routing, branches, enforcement, outcomes
- `03-OBSERVE` — execution overlays and traffic flow visualization
- `04-SAFETY-AND-GOVERNANCE` — enforcement nodes in the pipeline graph
- `05-FINOPS` — cost overlays on pipeline paths
- `06-BUILD-AND-IMPROVE` — workflow and agent assets as pipeline participants

## Paired Features (files to update)

- `08-PLANNED-ARCHITECTURE/GAP-MATRIX.md` — pipeline studio row
- `FEATURE-STATUS.md` — 08-C delivery counts

## Scope

- **Backend**: Define a pipeline model describing ingest → routing → branches → enforcement → outcomes → reporting. Create pipeline graph schema. Build pipeline visualization and authoring APIs. Support reusable pipeline templates.
- **UI**: Visual pipeline graph with route and branch editor concepts. Flow-builder canvas for authoring ingest, routing, enforcement, and reporting paths. Execution overlays showing real traffic volume, latency, and failure hotspots. Scenario mode for different policy, budget, or provider conditions.
- **Docs**: Document pipeline studio concepts, the flow model, and authoring workflows.
- **Postman**: Add pipeline visualization and authoring endpoints.
- **Scripts/Examples**: Add examples creating a pipeline template and viewing execution overlays.

## Acceptance Criteria

1. Pipeline studio has a coherent workflow-centered model
2. Visual pipeline graph renders ingest-to-outcome flow
3. Flow builder supports authoring routing, enforcement, and reporting paths
4. Pipeline connects to gateway, observe, governance, and FinOps context
5. FEATURE-STATUS.md dashboard updated
