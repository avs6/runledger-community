# Build & Improve — GAP Matrix

Last updated: PENDING AUDIT

## Legend

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet audited |
| `OK` | Verified working |
| `PARTIAL` | Present but partial, buggy, or unclear |
| `MISSING` | Missing, broken, or disconnected |
| `LEGACY` | Legacy/transitional surface; do not expand |

---

## Feature Rows

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Playground | `/playground` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.4` | Backend session/request CRUD and send/compare APIs exist, but the UI is mostly a history viewer with API examples rather than an interactive playground. |
| Prompts list | `/prompts` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `7.1` | Solid list/create/delete UI backed by real prompt APIs, but full lifecycle completion depends on prompt detail/version flows. |
| Prompt detail and versions | `/prompts/{name}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `7.1` | One of the strongest shipped feature sets: versioning, promotion, metrics, edit-as-new-version, and Git sync align well with workflow improvement. |
| Agents list | `/agents` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.1` | Backend agent CRUD exists, but the page is read-only card browsing and explicitly tells users to use the API to create agents. |
| Agent detail | `/agents/{agent_id}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.1` | Good read surface for stats and recent runs, but no edit/retire controls are exposed in the UI. |
| Agent memory | `/agents/{agent_id}/memory` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Agent detail` as a tab unless memory becomes a first-class managed domain. | P6 | `PENDING` | `8.1` | Useful observability page over memory read endpoints, but it is not a memory management UI and has weak docs/Postman/story coverage. |
| Workflows list | `/workflows` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.2` | Backend workflow CRUD exists, but the page is read-only and tells users to create definitions via API. |
| Workflow detail | `/workflows/{workflow_id}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.2` | Strong detail page for cost and runs, but no edit/archive controls despite backend support. |
| Workflow run detail | `/workflows/{workflow_id}/runs/{run_id}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.2`, `3.2` | Good drilldown on workflow execution steps, but it is investigative only and lightly documented. |
| Datasets | `/datasets` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Group under `Evaluation studio` instead of a separate top-level area. | P6 | `PENDING` | `7.3` | UI supports create/list/delete and detail viewing, but backend lacks full update flows and docs are bundled into evaluations/replay material. |
| Evaluation studio | `/evaluation` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Make this the single parent surface for scores, datasets, experiments, and replay. | P6 | `PENDING` | `7.2`, `7.3` | Cohesive cross-surface studio for experiments, datasets, prompts, and evaluators, but it is an aggregator rather than a clean end-to-end CRUD owner for each entity. |
| Experiments | `/experiments` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Group under `Evaluation studio`. | P6 | `PENDING` | `7.3` | Good create/run/delete UI, but full backend CRUD is not complete because update/edit is not exposed as a first-class experiment contract. |
| Replay lab | `/replay` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into the evaluation suite as replay mode, not a parallel lab product. | P6 | `PENDING` | `3.15`, `7.3` | The route works, but it reuses dataset/experiment APIs and concepts instead of a clearly separate replay domain, which weakens cohesion versus the product story. |
| Replay experiment detail | `/replay/{experiment_id}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Experiments` detail or evaluation result detail. | P6 | `PENDING` | `3.15`, `7.3` | Good result view with route recommendation action, but it is built on replay results plus gateway recommendation APIs and lacks a fuller replay management surface. |
| Optimization opportunities | `/optimization-opportunities` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `5.7`, `8.9` | Strong recommendation dashboard, but it derives opportunities heuristically from run-flow data instead of using a dedicated backend opportunities contract. |
| Optimization simulator | `/optimization-simulator` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `3.17`, `5.5`, `5.7` | Real simulation endpoint plus clear UI, but it is a what-if analysis surface rather than a CRUD-managed entity. |
| Model scorecards | `/model-scorecards` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Group with `Model usage` if the product wants one model intelligence area. | P6 | `PENDING` | `3.14` | Completed on Friday, August 14, 2026. The page already had the real scorecard/trend APIs and an interactive UI; this pass finished the cohesion work by adding dedicated documentation and explicit workflow bridges into Model Usage and Evaluations so the feature is no longer relying on indirect coverage or a CRUD-oriented completion bar that does not fit observability-style model intelligence. |
| Vector stores list | `/vector-stores` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.3` | Backend collection CRUD is real, but the UI is a read-only catalog that again tells users to use the API to create stores. |
| Vector store detail | `/vector-stores/{collection_id}` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `8.3` | Good read-only detail for stats and recent queries, but no rename/update/delete/query actions are surfaced despite backend capability. |
| Runbooks | `/runbooks` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P6 | `PENDING` | `3.16` | Valuable operator workflow with generate/list/export, but it is not a full CRUD domain and backend lives under runs rather than a dedicated runbooks router. |
