# RunLedger Planned Architecture Additions Bundles Blueprint

Last updated: Friday, August 14, 2026

## Purpose

This file is the working blueprint for the `Planned Architecture Additions`
section in RunLedger.

It is derived from:

- [FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
- [DELIVERY-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/DELIVERY-AUDIT.md)

This blueprint converts the planned-architecture audit rows into
implementation-ready bundles, technical specs, migration sequencing, and a
large enhancement backlog for future product and platform evolution.

## Planned Architecture Additions Vision

This section should define the next-generation architecture of RunLedger rather
than acting as a dumping ground for unrelated future ideas.

It should answer:

- how the runtime becomes faster, cleaner, and more scalable
- how control plane and data plane stay clearly separated
- how governance and scope enforcement become stronger on live traffic
- how operators and builders gain better visual, API, and help surfaces
- how docs, naming, and design become coherent enough for long-term product
  maintainability

The target outcome is:

`Planned Architecture Additions = coherent future-state platform architecture`

not

`Planned Architecture Additions = disconnected roadmap bullets`

## Audit-First Rule

This blueprint is derived from the audit, not the reverse.

The required input order for this file was:

1. `FEATURE-AUDIT.md`
2. the `Planned Architecture Additions` rows
3. the embedded gap signals inside those rows
4. the delivery crosswalk references attached to those rows
5. the already-established neighboring cohesion blocks for Gateway, Safety and
   Governance, Platform, Observe, and Organization and Access

This section is unusual because it is a planned-architecture section rather
than a shipped-surface section. It does not yet have its own dedicated `11.x`
cohesion matrix block. For that reason, this blueprint derives its cohesion
requirements from:

- the per-row crosswalk references
- the embedded architecture notes in the `Notes` column
- the already-created blueprints and cohesion matrices for the feature families
  it is intended to reshape

If this planned section later gains its own dedicated cohesion matrix, this
blueprint should be updated to consume it explicitly.

## Feature-Audit to Bundle Mapping

This blueprint maps section `9` of
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
into four architecture bundles.

| Bundle | Bundle Name | Feature-AUDIT rows mapped into the bundle | Mapping notes |
|--------|-------------|--------------------------------------------|---------------|
| `Bundle A` | `Rust Runtime and Gateway Data-Plane Consolidation` | `High-performance gateway service split`, `Review refactored gateway modules and migrate remaining hot data path into Rust`, `Collapse runledger-router into the Rust gateway`, `Legacy Python gateway deprecation and consumer migration` | This is the runtime-platform modernization bundle and should remain the top priority architecture track. |
| `Bundle B` | `Runtime Governance and Policy Enforcement Deepening` | `Scope-aware runtime governance enforcement deepening` | This is the hot-path governance expansion bundle and depends on the gateway architecture settling cleanly. |
| `Bundle C` | `Pipeline, API, and Embedded Product Surfaces` | `Pipeline studio and flow builder`, `API explorer and generated Swagger UI`, `In-app customer documentation and help hub` | This is the operator and developer surface expansion bundle that turns architecture into visible product leverage. |
| `Bundle D` | `Design System, Documentation Architecture, and Repo Systemization` | `UI theme refresh and dark-mode redesign`, `Documentation IA, hierarchy, and diagrams`, `Broader repo naming and historical cleanup review` | This is the coherence bundle for product experience, documentation structure, and repository comprehensibility. |

Material delivery-crosswalk support for this family comes from:

- `4.1`, `4.3`, `4.4`, `4.5`, `4.8`, `4.10`
- `7.13`, `7.14`
- `1.8`
- `2.3`, `2.5`, `2.6`
- `3.6`
- `6.4`
- `reference/api`
- `docs/*`
- `scripts/*`
- `examples/*`
- `apps/web/app/globals.css`
- `apps/web/components/*`
- `apps/api/runledger_api/routers/gateway*.py`
- `apps/api/runledger_api/services/plugin_runner.py`
- `apps/api/runledger_api/routers/workspace_controls.py`
- `runledger-gateway-rs`

## Bundle Overview

The Planned Architecture Additions family should be implemented and maintained
in this order:

1. `Bundle A` Rust Runtime and Gateway Data-Plane Consolidation
2. `Bundle B` Runtime Governance and Policy Enforcement Deepening
3. `Bundle C` Pipeline, API, and Embedded Product Surfaces
4. `Bundle D` Design System, Documentation Architecture, and Repo Systemization

That ordering follows platform dependency rather than ordinary UI workflow:

1. stabilize the runtime architecture
2. deepen live governance on top of that architecture
3. expose the runtime and platform power through stronger product surfaces
4. systematize docs, design, and repo language so the whole suite stays
   coherent long term

## Bundle A - Rust Runtime and Gateway Data-Plane Consolidation

### Product goal

Finish the gateway split so Rust becomes the true live data plane while Python
remains the clear control plane.

### Scope

- High-performance gateway service split
- Review refactored gateway modules and migrate remaining hot data path into Rust
- Collapse `runledger-router` into the Rust gateway
- Legacy Python gateway deprecation and consumer migration

### Derivation from the audit

This bundle is derived from:

- the highest-priority `P0` rows in the planned-architecture section
- the notes that explicitly define the desired end state:
  - Rust owns the data plane
  - Python owns CRUD, snapshots, analytics, admin UX, and control-plane support
- the crosswalk references into Gateway and Runtime Controls
- the current codebase split across `gateway.py`, `gateway_shared.py`,
  `gateway_legacy.py`, `gateway_routing.py`, `gateway_passthrough.py`,
  `gateway_runtime.py`, and `gateway_observability.py`

### Current state summary

- the Rust gateway exists and is partially integrated
- the Python router split is directionally correct and should not be undone
- some hot-path logic and compatibility assumptions still remain in Python
- docs/Postman/scripts/examples still reflect a mixed or transitional world in
  places
- `runledger-router` still exists as a sidecar that should be collapsed

### Bundle-level route ownership

- data-plane service:
  - `runledger-gateway-rs`
- Python control plane:
  - `/gateway`
  - gateway CRUD, stats, snapshots, benchmarks, and admin/config surfaces
- migration targets:
  - stale Python-hosted completion assumptions
  - sidecar `runledger-router`

### Operator or user workflow

1. operator configures gateway routes, policies, and provider posture in the
   control plane
2. live traffic flows through the Rust data plane
3. runtime events and summaries flow back into Python-owned admin and
   observability surfaces

### Matrix-derived gap inventory

#### Runtime gaps

- remaining hot-path logic still living in Python
- sidecar classifier architecture still adding runtime complexity
- consumer assumptions still mixed across docs/examples/scripts

#### Ownership gaps

- some observers and future contributors may still confuse control-plane routing
  with runtime route decisioning
- stale gateway assumptions can reintroduce architectural drift

#### Delivery gaps

- OpenAPI/Postman/examples/scripts still need full Rust-runtime alignment

### Architecture and ownership notes

This bundle owns:

- runtime-service split completion
- hot-path migration into Rust
- runledger-router collapse
- consumer migration and legacy cleanup

This bundle does not own:

- gateway CRUD/admin retirement
- governance control-plane authoring UX
- deep product docs IA or design refresh

### Cross-feature integration requirements

- `Gateway & Routing`
- `Observe`
- `FinOps`
- `Safety & Governance`
- `Platform / Utility`

### Implementation phases

#### Phase A1 - Finish runtime boundary cleanup

- review Python gateway modules
- identify remaining hot-path logic
- move execution-critical logic to Rust

#### Phase A2 - Collapse sidecars and runtime duplication

- fold `runledger-router` into Rust gateway
- simplify compose and service topology

#### Phase A3 - Complete consumer migration

- move all remaining examples, docs, Postman assets, and scripts to the new
  runtime model
- remove stale Python-inline runtime assumptions

### Bundle polish opportunities

- better runtime topology diagrams
- clearer service health dashboards
- stronger operator-facing split-of-responsibility docs

### Product enhancement ideas and suggestions

1. `Recommended next` Add a runtime topology page that shows control plane, data plane, event ingest, and observability flows in one diagram.
2. `Recommended next` Add a gateway execution trace explainer that makes the Rust-versus-Python ownership boundary obvious to operators and developers.
3. `Optional future enhancement` Add live runtime capability negotiation so the UI can surface which advanced data-plane features are active in the current deployment.

---

## Bundle B - Runtime Governance and Policy Enforcement Deepening

### Product goal

Make governance enforcement truly scope-aware on live traffic instead of
remaining primarily tool/action-match oriented.

### Scope

- Scope-aware runtime governance enforcement deepening

### Derivation from the audit

This bundle is derived from:

- the explicit future row that calls out scope-aware runtime governance
  deepening
- the notes identifying current limitations around coarse tool/action matching
- the crosswalk references into gateway and tool-governance surfaces
- the Safety and Governance blueprint, which already marks scope-aware runtime
  enforcement as a future deepening pass

### Current state summary

- control-plane governance surfaces are materially stronger than before
- runtime enforcement exists, but scope context is not yet propagated richly
  enough into the hot path
- logging and violation outcomes are not yet fully shaped around workspace,
  access-group, and broader identity context

### Bundle-level route ownership

- control-plane owners remain:
  - `/tool-registry`
  - `/tool-policies`
- runtime deepening target:
  - Rust gateway hot path
  - plugin runner / workspace controls integration surfaces

### Operator or user workflow

1. operator defines governance policies in the control plane
2. live traffic resolves identity and scope on the hot path
3. runtime enforcement applies policy with richer scope context
4. outcomes flow into observability, audit, and violation evidence

### Matrix-derived gap inventory

#### Runtime gaps

- enforcement is not yet sufficiently workspace/access-group-aware
- violation and logging context should become richer

#### Ownership gaps

- control plane and runtime behavior should remain separate but explainable

#### Evidence gaps

- scope-aware decisions should be visible in request analysis, audit evidence,
  and governance exports

### Architecture and ownership notes

This bundle owns:

- hot-path scope-aware policy enforcement deepening
- scope identity propagation into execution and evidence

This bundle does not own:

- policy authoring as a product surface
- organization and access lifecycle UX

### Cross-feature integration requirements

- `Gateway & Routing`
- `Safety & Governance`
- `Organization & Access`
- `Observe`

### Implementation phases

#### Phase B1 - Define runtime scope model

- formalize workspace, access-group, API-key, and org identity propagation on
  the runtime path

#### Phase B2 - Enforce broader scope-aware policies

- move beyond coarse tool/action matching
- incorporate richer scope constraints and decisions

#### Phase B3 - Close the evidence loop

- expose policy decisions, scope context, and violations in observability and
  governance evidence surfaces

### Bundle polish opportunities

- better policy-decision explainers
- clearer violation lineage
- stronger runtime governance health summaries

### Product enhancement ideas and suggestions

4. `Recommended next` Add a runtime policy decision viewer that explains which scope inputs, policies, and route facts produced an allow, deny, or review outcome.
5. `Recommended next` Add governance heatmaps showing which workspaces or access groups are generating the most policy friction.
6. `Optional future enhancement` Add policy simulation against historical traffic with scope-aware replay before enabling a new runtime enforcement rule.

---

## Bundle C - Pipeline, API, and Embedded Product Surfaces

### Product goal

Expose the power of the runtime and workflow system through stronger native
product surfaces for pipeline authoring, API exploration, and embedded help.

### Scope

- Pipeline studio and flow builder
- API explorer and generated Swagger UI
- In-app customer documentation and help hub

### Derivation from the audit

This bundle is derived from:

- the planned new-surface rows in section `9`
- the notes describing pipeline studio as both visualization and authoring
- the desire to collapse Postman-first maintenance into generated Swagger and an
  embedded explorer
- the requirement to avoid scattering help links and instead introduce an
  intentional in-app documentation hub

### Current state summary

- these surfaces are mostly missing or partial
- documentation hints and OpenAPI groundwork already exist
- there is no cohesive in-product architecture surface yet for pipelines, APIs,
  and contextual help

### Bundle-level route ownership

- planned routes:
  - `/pipeline-studio`
  - `/api-docs`
  - top-right help or embedded docs hub

### Operator or user workflow

1. user explores architecture or configuration through a visual pipeline view
2. user inspects and tries APIs through an embedded explorer
3. user gets contextual help and task guidance inside the product

### Matrix-derived gap inventory

#### Product-surface gaps

- no unified runtime-flow visualization and authoring surface exists
- API exploration is still more artifact-oriented than in-product
- help is still externalized and fragmented

#### Governance and observability gaps

- pipeline authoring must connect to enforcement, routing, telemetry, and
  outcomes rather than becoming a generic diagram toy

#### Delivery gaps

- generated API assets and interactive docs need a stronger canonical path

### Architecture and ownership notes

This bundle owns:

- new user-facing architecture surfaces
- embedded API exploration
- contextual customer help entry points

This bundle does not own:

- underlying gateway CRUD ownership
- raw doc source reorganization
- dark-mode or design-system implementation

### Cross-feature integration requirements

- `Gateway & Routing`
- `Observe`
- `Onboarding`
- `Build & Improve`
- `Safety & Governance`

### Implementation phases

#### Phase C1 - Define canonical product concepts

- pipeline model
- API-docs ownership
- help-hub placement and task model

#### Phase C2 - Build first-class entry surfaces

- pipeline visualization/authoring shell
- generated Swagger explorer
- contextual help hub

#### Phase C3 - Integrate deeply with adjacent feature families

- connect to runtime, governance, observability, and onboarding workflows

### Bundle polish opportunities

- richer diagrams and animations
- better embedded examples
- stronger context-sensitive help

### Product enhancement ideas and suggestions

7. `Recommended next` Add pipeline diff views that show how a proposed routing or policy change alters the flow graph before deployment.
8. `Recommended next` Add embedded task walkthroughs in the help hub for common jobs such as setting up telemetry, creating provider profiles, or tracing a failed request.
9. `Optional future enhancement` Add guided API recipes inside Swagger that pre-fill common multi-step platform workflows.

---

## Bundle D - Design System, Documentation Architecture, and Repo Systemization

### Product goal

Make the product, docs, and repository feel intentional, teachable, and
maintainable so future development does not regress into scattered naming,
random docs order, or ad hoc UI polish.

### Scope

- UI theme refresh and dark-mode redesign
- Documentation IA, hierarchy, and diagrams
- Broader repo naming and historical cleanup review

### Derivation from the audit

This bundle is derived from:

- the `P1` rows focused on docs, dark mode, and naming cleanup
- the notes calling for workflow-oriented docs IA and stronger Mermaid/diagram
  usage
- the repo cleanup row that explicitly targets phase-era language and
  history-shaped naming

### Current state summary

- the current UI theme works functionally but needs a more intentional system
- docs reorganization is already in progress, but incomplete
- repo naming still contains historical migration and phase residue

### Bundle-level route ownership

- cross-app design surface:
  - `apps/web/app/globals.css`
  - `apps/web/components/*`
- docs surface:
  - `docs/`
- repo-wide cleanup surface:
  - tests, scripts, docs, support assets

### Operator or user workflow

1. customer navigates the product and docs with clearer hierarchy
2. operator finds contextual guidance more quickly
3. contributors and future AI agents navigate the repo with less historical
   confusion

### Matrix-derived gap inventory

#### Design gaps

- dark-mode and visual language are functional but not yet polished

#### Documentation gaps

- feature-oriented structure and hierarchy are incomplete
- diagrams and system mental models can be much stronger

#### Repo-systemization gaps

- stale phase naming and migration language still increase cognitive load

### Architecture and ownership notes

This bundle owns:

- design-system modernization
- docs information architecture
- naming and historical cleanup

This bundle does not own:

- runtime migration itself
- pipeline or API explorer feature ownership

### Cross-feature integration requirements

- every major blueprint and feature family
- onboarding and help hub
- docs and support assets

### Implementation phases

#### Phase D1 - Define system vocabulary and IA

- product naming
- docs hierarchy
- platform terminology

#### Phase D2 - Refresh experience foundations

- dark mode
- cross-app tokens and patterns
- doc templates and diagram conventions

#### Phase D3 - Finish repo cleanup

- remove stale historical labels
- align scripts/docs/tests with product terminology

### Bundle polish opportunities

- stronger typography and layout system
- richer diagram sets
- better documentation landing pages

### Product enhancement ideas and suggestions

10. `Recommended next` Add a design token system that makes platform status, severity, scope, and runtime state visually consistent across every major feature family.
11. `Recommended next` Add architecture overview maps at the top of the docs that explain the product from install through runtime through governance through FinOps.
12. `Optional future enhancement` Add repo navigation guides for future contributors and AI agents that explain the architectural center of gravity of each subsystem.

---

## Bundle A Technical Spec

### Technical goals

1. make Rust the true live gateway data plane
2. keep Python as the clean control plane
3. complete consumer migration and sidecar collapse

### Current implementation anchor points

- `runledger-gateway-rs`
- `apps/api/runledger_api/routers/gateway.py`
- `apps/api/runledger_api/routers/gateway_shared.py`
- `apps/api/runledger_api/routers/gateway_legacy.py`
- `apps/api/runledger_api/routers/gateway_routing.py`
- `apps/api/runledger_api/routers/gateway_passthrough.py`
- `apps/api/runledger_api/routers/gateway_runtime.py`
- `apps/api/runledger_api/routers/gateway_observability.py`
- `apps/api/runledger_api/services/intelligent_router.py`
- `docker-compose.yml`
- gateway docs, examples, scripts, and generated API assets

### Target architecture

- Rust data plane:
  - auth resolution needed for execution
  - intelligent routing/classification
  - route selection
  - provider execution
  - retries/fallback
  - cache participation
  - live traffic enforcement
- Python control plane:
  - CRUD
  - snapshots and signed event ingest
  - analytics and summaries
  - admin/config UX support
  - observability-facing management APIs

### Data model expectations

- preserve current control-plane entities
- introduce clearer runtime event and decision contracts where necessary
- avoid duplicating runtime state between Python and Rust

### Schema expectations

- stable management APIs in Python
- explicit runtime-support/event contracts between Rust and Python
- sidecar classifier contracts absorbed into the Rust runtime

### API contract changes

- remove stale Python-inline completion assumptions
- absorb `runledger-router` runtime interfaces into Rust-facing runtime APIs
- keep admin/config APIs mounted in Python

### UI requirements

- gateway UI should continue to speak to control-plane ownership
- no UI should depend on deprecated Python-inline runtime paths
- runtime health and capability visibility should improve

### Cross-feature integration requirements

- Observe for live execution traces
- FinOps for enforcement and cost tracking
- Governance for policy enforcement
- Platform for infra and deployment visibility

### Delivery-surface requirements

- docs
- Postman
- scripts
- examples
- reference API assets
- compose and deployment docs

### Implementation phases

1. finish hot-path review and migration
2. collapse `runledger-router`
3. complete consumer migration and Python cleanup

### Acceptance criteria

- Rust owns the active live data path
- Python owns the control plane cleanly
- sidecar routing classifier is gone
- stale inline-runtime assumptions are removed from docs/examples/scripts

### Product enhancement suggestions

- runtime topology page
- execution trace explainer
- capability negotiation

## Bundle B Technical Spec

### Technical goals

1. propagate scope context richly through runtime enforcement
2. make governance decisions visible and explainable
3. keep governance authoring and enforcement cleanly separated

### Current implementation anchor points

- `runledger-gateway-rs`
- `apps/api/runledger_api/services/plugin_runner.py`
- `apps/api/runledger_api/routers/workspace_controls.py`
- Tool Registry and Tool Policies surfaces
- governance evidence and observability integration surfaces

### Target architecture

- control-plane policy definition in Python/UI
- hot-path enforcement in Rust/runtime-support layers
- shared scope identity model across workspace, access-group, API-key, and org
- richer logging and evidence for enforcement decisions

### Data model expectations

- explicit scope context objects
- richer policy-decision records
- clearer violation lineage fields

### Schema expectations

- runtime-decision payloads
- enriched violation/audit/observability records
- replay/simulation-compatible policy evaluation structures

### API contract changes

- optional policy-decision explain endpoints
- richer violation ingestion or event publishing contracts
- compatible runtime summary APIs for observability and governance UI

### UI requirements

- policy-decision explanation views
- stronger scope-aware evidence filters
- runtime governance status and friction summaries

### Cross-feature integration requirements

- Organization and Access
- Gateway
- Observe
- Safety and Governance evidence surfaces

### Delivery-surface requirements

- docs
- scripts
- examples
- Postman or generated API explorers where relevant

### Implementation phases

1. formalize scope model
2. deepen enforcement
3. close evidence loop

### Acceptance criteria

- runtime enforcement is more than tool/action matching
- scope context appears clearly in decisions and evidence
- operators can inspect why enforcement happened

### Product enhancement suggestions

- decision viewer
- governance heatmaps
- historical replay simulation

## Bundle C Technical Spec

### Technical goals

1. create first-class architecture and API product surfaces
2. embed help where users actually need it
3. connect these surfaces tightly to runtime and workflow concepts

### Current implementation anchor points

- `reference/api`
- existing OpenAPI output
- docs sources under `docs/`
- onboarding and contextual UI entry points
- future route surfaces for `/pipeline-studio` and `/api-docs`

### Target architecture

- pipeline studio as both visualization and authoring
- Swagger/API explorer as generated and interactive
- help hub as contextual, embedded, and task-oriented

### Data model expectations

- pipeline model describing ingest, routing, enforcement, branching, outcomes,
  and reporting
- help-hub metadata for task-aware content linking
- recipe/example metadata for interactive API usage

### Schema expectations

- generated OpenAPI ownership
- pipeline graph schema
- embedded help index or navigation schema

### API contract changes

- generated docs APIs or artifacts
- pipeline visualization/authoring APIs
- help metadata or content-index APIs if needed

### UI requirements

- visual pipeline graph
- route and branch editor concepts
- embedded API testing
- contextual help drawer or hub

### Cross-feature integration requirements

- Gateway
- Observe
- Onboarding
- Build and Improve
- Governance

### Delivery-surface requirements

- docs
- OpenAPI generation
- examples
- scripts or demos
- top-right help entry guidance

### Implementation phases

1. define canonical product concepts
2. build first-class entry surfaces
3. integrate deeply with neighboring features

### Acceptance criteria

- pipeline studio has a coherent workflow-centered model
- API explorer is generated, interactive, and in-product
- help hub feels intentional rather than scattered

### Product enhancement suggestions

- pipeline diff views
- embedded task walkthroughs
- guided API recipes

## Bundle D Technical Spec

### Technical goals

1. create a coherent design and documentation system
2. reduce historical and naming noise across the repo
3. make the platform easier for customers, operators, and contributors to learn

### Current implementation anchor points

- `apps/web/app/globals.css`
- `apps/web/components/*`
- `docs/introduction.mdx`
- `docs/architecture.md`
- `docs/mint.json`
- `docs/`
- `scripts/*`
- `apps/api/tests/*`

### Target architecture

- design-token-backed cross-app experience
- feature-oriented docs IA
- consistent repo terminology and contributor navigation

### Data model expectations

- design tokens and semantic status mappings
- docs taxonomy and navigation metadata
- cleanup inventories for stale historical naming

### Schema expectations

- docs navigation structure
- optional design token schema or config artifacts
- cleanup tracking inventories where useful

### API contract changes

- generally minimal
- focus is on content systemization and UI foundations rather than new backend
  business APIs

### UI requirements

- stronger dark mode
- more intentional component styling
- consistent status, scope, and severity language
- embedded architectural cues where needed

### Cross-feature integration requirements

- every blueprint and major feature family
- help hub and onboarding
- docs and support assets

### Delivery-surface requirements

- docs
- scripts
- tests
- examples
- naming and terminology guidance

### Implementation phases

1. define vocabulary and IA
2. refresh experience foundations
3. finish repo cleanup

### Acceptance criteria

- dark mode and visual language feel intentional
- docs hierarchy is significantly clearer
- repo terminology is more product-centered and less history-shaped

### Product enhancement suggestions

- design token system
- architecture overview maps
- contributor/AI navigation guides

---

## Major-Feature Product Enhancement Ideas

These are high-level product and architectural suggestions for `Planned
Architecture Additions` beyond the minimum remediation plan.

1. `Runtime` Add a live gateway runtime map showing active nodes, health, throughput, retry paths, and fallback topology.
2. `Runtime` Add a per-request execution waterfall that shows each gateway stage from auth through enforcement through provider response.
3. `Runtime` Add adaptive request shaping in Rust that changes concurrency and backpressure behavior by route class.
4. `Runtime` Add first-class circuit-breaker primitives with operator-visible open, half-open, and closed states.
5. `Runtime` Add runtime canary route support for model or provider changes with built-in rollback triggers.
6. `Runtime` Add shadow traffic support for provider, prompt, or policy experiments without affecting live responses.
7. `Runtime` Add provider health scoring inside the Rust gateway so route selection can degrade gracefully before full outages.
8. `Runtime` Add a built-in gateway runtime benchmark harness that can replay representative traffic profiles.
9. `Runtime` Add route warm-up and cache prefill jobs for newly promoted models or providers.
10. `Runtime` Add request-path feature flags so advanced runtime capabilities can be rolled out incrementally by scope.
11. `Runtime` Add policy-aware fallback chains where the fallback path can change based on risk or sensitivity.
12. `Runtime` Add replayable runtime snapshots that let engineers reproduce gateway decisions against historical state.
13. `Runtime` Add a route simulation sandbox that predicts provider choice, latency, and budget effect before a policy is saved.
14. `Runtime` Add gateway runtime plug points for future policy engines or ML-based route scoring modules.
15. `Runtime` Add a route-decision journal optimized for post-incident analysis and cost attribution.
16. `Runtime` Add multi-region or multi-node runtime coordination primitives if the gateway is later deployed in clustered form.
17. `Runtime` Add streaming-aware enforcement so partial outputs can still be governed, metered, and interrupted safely.
18. `Runtime` Add structured runtime capability descriptors that let the UI and docs reflect deployment-specific behavior.
19. `Governance` Add scope-resolution traces that explain how workspace, org, access-group, and API-key policies combined on a request.
20. `Governance` Add a governance replay mode that tests new runtime rules against stored request sets before activation.
21. `Governance` Add policy confidence scores that estimate how often a new rule will trigger on real traffic.
22. `Governance` Add enforcement modes such as observe-only, warn, block, reroute, redact, and require-approval for a single policy family.
23. `Governance` Add policy bundles that can be applied by org type, workspace type, or compliance preset.
24. `Governance` Add operator-defined escalation ladders so high-risk denials or repeated violations automatically notify the right owners.
25. `Governance` Add runtime tag propagation so tags can participate in enforcement, audit, analytics, and FinOps attribution at once.
26. `Governance` Add policy-drift detection that warns when control-plane intent and runtime behavior diverge.
27. `Governance` Add budget-aware governance rules that can tighten permissions or fallback behavior during spend anomalies.
28. `Governance` Add tool-governance scorecards summarizing denial rates, approval rates, and high-friction policies by scope.
29. `Governance` Add governance-aware request sampling so evidence capture is strongest for risky or novel traffic classes.
30. `Pipeline` Add a flow-builder canvas where operators can author ingest, routing, enforcement, and reporting paths as reusable templates.
31. `Pipeline` Add pipeline nodes for MCP, OTLP, webhooks, OpenInference, and gateway branches so the visualization reflects the real platform.
32. `Pipeline` Add execution overlays on the pipeline graph that animate real traffic volume, latency, and failure hotspots.
33. `Pipeline` Add scenario mode in the pipeline studio that shows how a request would move under different policy, budget, or provider conditions.
34. `Pipeline` Add diffable pipeline versions so teams can compare architecture changes visually over time.
35. `Pipeline` Add export-to-diagram features for architecture reviews, customer onboarding, and incident reports.
36. `Pipeline` Add import-from-runtime introspection so the graph can be generated from the live platform before users author changes.
37. `Pipeline` Add a branch-cost overlay showing which parts of a pipeline are the most expensive or wasteful.
38. `API` Add generated Swagger examples that are seeded from the main manual labs and simulation scripts rather than static placeholders.
39. `API` Add authenticated API-console sessions that respect the user’s org, workspace, and role context automatically.
40. `API` Add API recipes for common workflows such as creating an org, setting up telemetry, defining provider profiles, and creating a budget.
41. `API` Add an API change log surface inside the explorer so operators can see new, deprecated, and changed endpoints by release.
42. `API` Add endpoint ownership badges that tell users whether an API belongs to control plane, data plane support, observability, or admin utilities.
43. `API` Add SDK snippet generation for Python, TypeScript, curl, and future SDK targets directly in the API explorer.
44. `API` Add API workflow collections that are generated from blueprint bundles so product structure and API exploration stay aligned.
45. `Help` Add task-aware contextual help that changes based on the current route, tab, and user role.
46. `Help` Add embedded “why this exists” panels on complex admin pages to explain the workflow-centered product model.
47. `Help` Add operator playbooks for common incidents such as gateway failure, telemetry gaps, spend spikes, or policy rollout issues.
48. `Help` Add a searchable in-app knowledge hub that indexes docs, labs, examples, blueprint summaries, and troubleshooting guides together.
49. `Help` Add guided setup tours for first platform bootstrap, first org onboarding, first telemetry pipeline, and first gateway route creation.
50. `Help` Add context-sensitive doc anchors that jump users from UI surfaces into the exact relevant section of the docs hierarchy.
51. `Design` Add a cross-app design token system for colors, spacing, typography, elevation, status, severity, and scope indicators.
52. `Design` Add a richer dark-mode palette with better contrast, more intentional accent use, and clearer operational-state differentiation.
53. `Design` Add consistent layout shells for platform admin, org admin, gateway admin, and observability surfaces.
54. `Design` Add data-density modes for heavy operator pages so users can toggle between executive and power-user views.
55. `Design` Add a visual language for scope so platform, org, workspace, access-group, and API-key contexts are instantly recognizable.
56. `Docs` Add a docs landing map that mirrors the major feature families and their bundle blueprints directly.
57. `Docs` Add mandatory Mermaid architecture blocks for every major subsystem and every bundle blueprint.
58. `Docs` Add customer-facing progressive disclosure docs that separate first-time onboarding, operator tasks, and deep architectural material.
59. `Docs` Add blueprint-to-doc crosswalks so feature changes can be audited back into docs more systematically.
60. `Docs` Add docs health checks that flag broken conceptual links when a feature moves, collapses, or changes ownership.
61. `Repo` Add repo vocabulary linting or review guidance that flags reintroduction of deprecated concepts like teams or projects where inappropriate.
62. `Repo` Add subsystem ownership maps for future contributors so code discovery starts from product architecture rather than filesystem guesswork.
63. `Repo` Add generated support matrices that show which docs, scripts, examples, and API collections cover each major feature family.
64. `Repo` Add historical-cleanup checklists that can be reused after each large migration or feature collapse.
65. `Platform` Add a bootstrap readiness checker that validates whether telemetry, gateway runtime, storage, backups, docs, and help surfaces are all ready for a real deployment.
66. `Platform` Add deployment-profile visualization that shows how self-hosted, homelab, and enterprise footprints differ in services and defaults.

## Bundle Acceptance Summary

`Planned Architecture Additions` is complete as a roadmap family when:

- the Rust gateway is the unambiguous live data plane
- Python remains the clean control plane
- scope-aware runtime governance is materially deeper than coarse tool/action
  matching
- pipeline studio, generated API explorer, and embedded help have coherent
  first-class product ownership
- design-system, docs IA, and repo terminology are significantly more coherent
  than they are today
- docs, generated API assets, scripts, examples, and architecture diagrams
  reflect the future-state platform model rather than transitional assumptions
