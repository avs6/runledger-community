# RunLedger Gateway and Routing Bundles Blueprint

Last updated: Friday, August 14, 2026

## Purpose

This file is the working blueprint for the `Gateway & Routing` feature family in RunLedger.

It is derived from the shipped-surface audit, the delivery audit crosswalk, and
the cohesion matrices in
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md).

This blueprint turns the current Gateway audit into implementation-ready bundle
groupings, architecture rules, technical specs, and product-improvement ideas.

## Gateway & Routing Vision

Gateway & Routing should feel like one coherent runtime operating system.

It should let operators:

- define provider and model access cleanly
- configure routes, routing groups, policies, and pass-through behavior
- understand what the runtime will do before traffic arrives
- enforce routing, fallback, throttling, and cache behavior on live traffic
- govern runtime safety without scattering policy surfaces
- investigate runtime behavior through linked observability and economics surfaces

The target outcome is:

`Gateway & Routing = provider control + runtime execution + policy enforcement + performance controls`

not

`Gateway & Routing = a management page plus a few disconnected sub-features`

## Audit-First Rule

This blueprint is derived from the audit, not the reverse.

The required input order for this file was:

1. `FEATURE-AUDIT.md`
2. `Gateway & Routing` feature rows and gap matrix
3. `Delivery Audit Crosswalk`
4. `11.4 Gateway & Routing Cohesion Matrix`
5. bundle derivation and technical planning

If the `Gateway & Routing` section or the `11.4` cohesion matrix changes
materially, this blueprint should be updated.

## Feature-Audit to Bundle Mapping

This blueprint maps the `Gateway & Routing` rows from section `2` of
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
into four implementation bundles.

| Bundle | Bundle Name | Feature-AUDIT rows mapped into the bundle | Mapping notes |
|--------|-------------|--------------------------------------------|---------------|
| `Bundle A` | `Provider Catalog and Routing Control Plane` | `Provider profiles`, `Model gateway` | This is the primary gateway admin and runtime-configuration bundle. It also carries the Rust/Python ownership model for the data plane vs control plane. |
| `Bundle B` | `Runtime Protection and Enforcement` | `Guardrails` | Guardrails remains a distinct operator surface, but it is tightly coupled to gateway runtime behavior and governance outcomes. |
| `Bundle C` | `Performance and Traffic Controls` | `Response cache`, `Rate limits` | Both rows are already collapsed into Gateway and should remain sub-features rather than re-emerging as separate products. |
| `Bundle D` | `Runtime Architecture and Consumer Alignment` | `Model gateway`, `Response cache`, `Rate limits` | This bundle is derived from the same shipped surfaces plus the audit note that the Rust gateway is now the active data plane. It focuses on the runtime ownership, consumer alignment, and control-plane/data-plane discipline rather than inventing a new user-facing page. |

Related `DELIVERY-AUDIT.md` rows that materially support this family include:

- `4.1` Gateway routes
- `4.2` Provider profiles
- `4.9` Rate limits
- `5.1` Exact cache
- `5.2` Semantic cache
- `6.5` Budget tiers
- `6.7` Model budgets

## Bundle Overview

These bundles are derived from the feature rows, delivery crosswalk, and the
`11.4 Gateway & Routing Cohesion Matrix`.

Recommended execution order:

1. `Bundle A` - Provider Catalog and Routing Control Plane
2. `Bundle B` - Runtime Protection and Enforcement
3. `Bundle C` - Performance and Traffic Controls
4. `Bundle D` - Runtime Architecture and Consumer Alignment

Why this order:

1. provider and routing control define the core admin/runtime model
2. enforcement and protection must sit on top of the canonical runtime path
3. cache and throttling controls must remain subordinate to the gateway control plane
4. architecture and consumer alignment should harden the runtime split and keep stale consumers from drifting back toward the old model

---

## Bundle A - Provider Catalog and Routing Control Plane

### Product goal

Bundle A should make provider configuration and routing behavior feel like one coherent operator system.

It should answer:

- which providers are available and at what scope
- which routes, routing groups, and policies exist
- how pass-through and fallback behavior work
- how API-key, workspace, and AI-hub concepts connect to runtime selection

### Scope

- `Provider profiles`
- `Model gateway`

### Derivation from the audit

From the feature rows:

- both `Provider profiles` and `Model gateway` are complete and strong
- `Model gateway` already absorbed route, policy, pass-through, rate-overview, cache-profile, quota-tier, and model-quota ownership

From the delivery crosswalk:

- `4.1` and `4.2` are already strong across backend/UI/docs/Postman/scripts/examples

From the cohesion matrix:

- `Provider profiles x FinOps = GAP` around provider-cost posture
- `Model gateway x FinOps = PARTIAL`
- `Model gateway x Observe = STRONG`
- `Model gateway x Tool registry / Tool policies / Security / Alert rules = STRONG`
- `Model gateway x API keys / Workspaces / AI hub = STRONG`

### Current state summary

Strengths:

- the control plane is already complete on the shipped surface
- provider profiles are full CRUD and strongly linked to workspace/global scope
- gateway control plane is broad and real across routes, policies, pass-through, cache profiles, and quotas
- docs and support surfaces already reflect the Rust data-plane split well

Weaknesses:

- provider-cost posture is still weakly connected to FinOps
- the user-facing explanation of technical quota vs financial policy can still improve
- some remaining consumers and support assets still need to stay aligned to the Rust runtime model

### Implementation update - Friday, August 14, 2026

This bundle has now started closing the highest-value Gateway x FinOps seams:

- provider-profile list responses now include attached budget counts from the backend
- `/provider-profiles` now shows active and total budget posture per profile and links directly into scoped budget views and scoped budget creation
- `/budgets` now accepts scoped deep links for `provider_profile` budgets and can auto-open the create flow with the scope prefilled
- `/budgets/{id}` now links operators back to the owning surface for provider profiles, API keys, and access groups
- `/gateway` now explains the runtime-throttle versus spend-policy split more clearly and links directly to the Budgets control plane

### Bundle-level route ownership

- `/provider-profiles`
- `/gateway`

### Operator workflow

1. define or sync provider profiles
2. build routes, routing groups, routing policies, and pass-through targets
3. assign technical quota and model controls where needed
4. observe runtime behavior through linked observability surfaces
5. refine routing or provider posture based on runtime and economics outcomes

### Matrix-derived gap inventory

FinOps gaps:

- `Provider profiles x Budgets = PARTIAL`
- `Provider profiles x Budget detail = PARTIAL`
- `Model gateway x Budgets = PARTIAL`
- `Model gateway x Budget detail = PARTIAL`

These are strong signs that Gateway and FinOps still need a clearer operator relationship.

Organization & Access gaps:

- `Provider profiles x Organization profile = PARTIAL`
- `Provider profiles x API keys = PARTIAL`
- `Model gateway x Access groups = PARTIAL`

Observe strengths and gaps:

- `Model gateway x Runs / Run detail / Request Flow / Request Explorer = STRONG`
- `Provider profiles x Analytics overview / Engineering = PARTIAL`

Governance strengths:

- `Model gateway x Tool registry / Tool policies = STRONG`
- `Model gateway x Security / Alert rules = STRONG`

### Architecture and ownership notes

Bundle A owns:

- provider catalog behavior
- route and policy control-plane behavior
- pass-through control
- runtime config surfaces needed by operators

Bundle A does not own:

- financial spend policy
- chargeback allocation
- deep investigative analytics ownership

Current architecture rule:

- `runledger-gateway-rs` is the active data plane for live gateway execution
- Python remains the management and supporting control-plane layer where still intended
- the blueprint must not drift back toward an implicit Python-hosted gateway runtime

### Cross-feature integration requirements

- must stay strongly linked to Workspaces, API keys, and AI hub
- must link more clearly to FinOps without ceding technical-control ownership
- must stay one of the strongest bridges into Observe and runtime investigation
- must stay tightly integrated with governance and runtime policy surfaces

### Implementation phases

#### Phase A1 - Strengthen provider and routing explainability

- improve route/provider summaries
- clarify scope ownership and runtime effects
- improve operator visibility into route-policy composition

#### Phase A2 - Tighten FinOps and capability-catalog bridges

- improve links to AI hub, provider cost posture, and technical-vs-financial control distinctions
- make provider/routing cost implications easier to understand

#### Phase A3 - Harden runtime control-plane consistency

- keep all route, policy, pass-through, cache-profile, and quota controls visibly centralized in `/gateway`
- avoid parallel config drift across older compatibility surfaces

### Bundle polish opportunities

- better route-summary cards
- clearer fallback and retry explanations
- richer provider-scope visualizations

### Product enhancement ideas and suggestions

1. `Recommended next` Add a “route explain” panel that shows why a request would resolve to a given provider, route, or fallback branch.
2. `Recommended next` Add a provider posture dashboard showing freshness, price posture, fallback coverage, and route usage concentration.
3. `Optional future enhancement` Add route versioning and configuration snapshots so operators can compare runtime behavior across policy changes.

---

## Bundle B - Runtime Protection and Enforcement

### Product goal

Bundle B should make runtime protection feel like an enforceable operating layer, not an isolated policy page.

It should answer:

- which guardrails exist
- which are enabled or disabled
- what happens when a guardrail is violated
- how violations are logged and reviewed
- how guardrail enforcement connects to the live gateway path

### Scope

- `Guardrails`

### Derivation from the audit

From the feature rows:

- `Guardrails` is complete and feature-rich on backend, UI, docs, Postman, scripts, and examples
- the dedicated violations log exists and is filterable/paginated
- runtime enforcement remains intentionally Python-based in this phase

From the cohesion matrix:

- `Guardrails x Access groups = STRONG`
- `Guardrails x Tool policies / Alert rules / Audit log = STRONG or PARTIAL`
- `Guardrails x Request-analysis surfaces = PARTIAL`
- `Guardrails x FinOps = mostly N/A or indirect`

### Current state summary

Strengths:

- complete operator surface
- strong testing, template, violation, and feedback workflows
- meaningful ties to governance surfaces

Weaknesses:

- runtime effects could still be easier to trace in request-analysis flows
- enforcement-path ownership needs to remain explicit as the Rust gateway data plane evolves

### Bundle-level route ownership

- `/guardrails`
- `/guardrails/violations`

### Operator workflow

1. create or choose guardrails
2. test and validate them
3. enable them on live traffic
4. review violations and feedback
5. refine enforcement rules based on outcomes

### Matrix-derived gap inventory

Observe gaps:

- `Guardrails x Request flow / Request explorer = PARTIAL`
- guardrail impact should be easier to trace through the request-analysis journey

Gateway/governance strengths:

- `Guardrails x Tool policies = STRONG`
- `Guardrails x Alert rules = STRONG`
- `Guardrails x Audit log = STRONG`

Organization gaps:

- access-group linkage is meaningful, but can still become more explicit in operator summaries

### Architecture and ownership notes

Bundle B owns:

- runtime protection surfaces
- test/playground flows
- violations and feedback surfaces

Bundle B does not own:

- general route selection
- provider pricing posture
- financial limit enforcement

Current runtime rule:

- guardrails remain Python-enforced in this phase even though the primary gateway data plane has moved to Rust
- the blueprint should treat this as an intentional split, not accidental drift

### Cross-feature integration requirements

- must stay tightly linked to gateway runtime and governance evidence
- should become easier to inspect from request-analysis and monitoring surfaces
- should continue to respect access-group scoping

### Implementation phases

#### Phase B1 - Improve runtime traceability

- make guardrail outcomes easier to trace from request-analysis pages
- improve links between violation records and live request investigations

#### Phase B2 - Harden enforcement-path clarity

- document and surface how Python-based guardrail enforcement fits with the Rust gateway data plane
- avoid operator confusion about which runtime layer enforces what

#### Phase B3 - Strengthen summary and feedback UX

- improve operator summaries
- improve review flows from violations to policy change

### Bundle polish opportunities

- better guardrail outcome summaries
- clearer false-positive review loops
- stronger violation clustering views

### Product enhancement ideas and suggestions

4. `Recommended next` Add a “violation impact” lens that shows which guardrails caused the most blocks, downgrades, or user-visible friction.
5. `Optional future enhancement` Add guardrail bundles or presets by risk posture, industry, or workflow type.
6. `Optional future enhancement` Add side-by-side request playback showing before/after guardrail impact for a sampled traffic slice.

---

## Bundle C - Performance and Traffic Controls

### Product goal

Bundle C should keep cache and throttling behavior inside the main gateway experience and make those controls legible to operators.

It should answer:

- what cache profiles exist
- how semantic or exact cache behavior affects traffic
- how throttling and quota tiers are applied
- how performance controls relate to runtime outcomes and economics

### Scope

- `Response cache`
- `Rate limits`

### Derivation from the audit

From the feature rows:

- both surfaces are intentionally collapsed into `/gateway`
- backend ownership is real and complete enough
- the standalone routes are legacy/compatibility only

From the delivery crosswalk:

- `4.9`, `5.1`, `5.2`, `6.5`, and `6.7` all show that the supporting contracts and delivery surfaces are strong enough to treat these as embedded gateway capabilities

From the cohesion matrix:

- `Response cache x Optimization simulator = STRONG`
- `Rate limits x API keys = STRONG`
- `Response cache` and `Rate limits` remain only `PARTIAL` across many observability and FinOps relationships

### Current state summary

Strengths:

- cache profile lifecycle and stats exist
- rate-limit overview and quota controls are already embedded in Gateway
- compatibility redirects are already in place

Weaknesses:

- economics and runtime effects are still only moderately surfaced
- throttling and cache behavior are not yet easy enough to inspect through request-analysis journeys

### Bundle-level route ownership

- primary owner: `/gateway`
- compatibility only: `/response-cache`
- compatibility only: `/rate-limits`

### Operator workflow

1. stay inside `/gateway`
2. manage cache profiles and route cache behavior
3. manage runtime throttles, quota tiers, and model quotas
4. inspect operational outcomes through monitoring and request-analysis surfaces

### Matrix-derived gap inventory

FinOps gaps:

- `Response cache x Budget detail = GAP`
- `Rate limits x Budget detail = GAP`
- the economics impact of these controls is still under-explained

Observe gaps:

- `Response cache x Runs / Request explorer / Monitoring = PARTIAL`
- `Rate limits x Runs / Monitoring = PARTIAL`

Identity/scope strengths:

- `Rate limits x API keys = STRONG`
- `Response cache x Workspaces = PARTIAL`

### Architecture and ownership notes

Bundle C owns:

- performance and traffic-control subfeatures as embedded gateway controls

Bundle C does not own:

- standalone top-level product routes for cache or rate limits

Collapse rule:

- neither response cache nor rate limits should re-emerge as an independent long-term product area

### Cross-feature integration requirements

- must stay embedded in Gateway
- should become more visible in Observe and economics views
- should remain clearly distinct from FinOps policy ownership

### Implementation phases

#### Phase C1 - Keep embedded ownership coherent

- keep all cache and rate-limit controls inside `/gateway`
- clean any remaining stray ownership language

#### Phase C2 - Improve runtime and economics visibility

- improve links from cache/throttle settings into monitoring, request analysis, and economics outcomes

#### Phase C3 - Strengthen API-key and model-control understanding

- make quota-tier and model-quota implications easier to understand from the API-key and gateway angles

### Bundle polish opportunities

- better cache hit/miss summaries
- clearer throttle and quota health views
- better route-level performance-control summaries

### Product enhancement ideas and suggestions

7. `Recommended next` Add route-level cache and throttle diagnostics that explain why a request was cached, bypassed, or throttled.
8. `Recommended next` Add a performance-control simulator that estimates latency, hit-rate, and cost effects before saving a config change.
9. `Optional future enhancement` Add adaptive cache-policy recommendations based on repeated request patterns and response sizes.

---

## Bundle D - Runtime Architecture and Consumer Alignment

### Product goal

Bundle D should keep the runtime ownership model explicit and prevent the product from drifting back toward an unclear gateway architecture.

It should answer:

- which parts of gateway execution live in Rust
- which parts remain Python control-plane or support surfaces
- which consumer examples, docs, scripts, and compatibility routes still matter
- how operators should think about the data plane versus the control plane

### Scope

- `Model gateway`
- `Response cache`
- `Rate limits`

### Derivation from the audit

From the feature rows:

- `Model gateway` notes already explicitly mention the Rust data-plane split
- `Response cache` and `Rate limits` are already collapsed into `/gateway`

From the delivery crosswalk:

- gateway routes, cache, and rate-limit support coverage are all strong enough to treat the runtime architecture as a real product assumption rather than a hidden implementation detail

From the cohesion matrix:

- gateway is central to Build & Improve, Observe, and Governance
- platform and support alignment around the runtime model remains only partial in places

### Current state summary

Strengths:

- the active runtime model is already reflected in the main gateway surface
- docs/support coverage for gateway routes is strong

Weaknesses:

- architecture drift is still a risk in support assets, examples, and future feature work
- operators may still confuse data-plane and control-plane ownership if not documented and surfaced clearly

### Bundle-level route ownership

- active operator surface: `/gateway`
- architecture principle: Rust data plane, Python control plane/support surfaces where still intentionally retained

### Operator workflow

1. configure runtime behavior in `/gateway`
2. trust that live execution is on the Rust data plane
3. use monitoring, request-analysis, and support assets that reflect the same ownership model

### Matrix-derived gap inventory

Architecture-consistency gaps:

- platform/support understanding of runtime ownership is still only `PARTIAL`
- some relationships to economics and downstream interpretation remain only moderate

Consumer-alignment gaps:

- docs/examples/scripts can drift if the runtime ownership model is not kept explicit
- compatibility surfaces must stay clearly subordinate

### Architecture and ownership notes

Current architecture rule:

- Rust gateway is the live request-path data plane
- Python is not the primary gateway runtime any more
- Python remains only where intentionally retained for control-plane support, management APIs, or non-hot-path supporting behavior

This bundle exists to keep that rule stable in product thinking, docs, and future implementation work.

### Cross-feature integration requirements

- must stay aligned with Gateway control-plane UX
- must stay visible in docs, Postman, examples, and scripts
- must support downstream observability, optimization, and governance without architecture ambiguity

### Implementation phases

#### Phase D1 - Make runtime ownership explicit everywhere

- keep docs, examples, and support language aligned to the Rust runtime model
- make data-plane vs control-plane boundaries explicit

#### Phase D2 - Remove or minimize old-path ambiguity

- keep compatibility routes and supporting paths subordinate
- avoid any new feature work that implicitly resurrects an older Python runtime assumption

#### Phase D3 - Strengthen operator-facing architecture clarity

- add clearer architecture explanations and runtime posture summaries where useful

### Bundle polish opportunities

- clearer architecture summaries in gateway docs/help
- stronger “how this executes” operator explanations
- better support-asset consistency checks

### Product enhancement ideas and suggestions

10. `Recommended next` Add a runtime-ownership explainer in the Gateway UI that shows which concerns are data-plane, control-plane, or supporting services.
11. `Optional future enhancement` Add a configuration consistency checker that flags settings or scripts still referencing deprecated runtime assumptions.
12. `Optional future enhancement` Add a gateway architecture map with drilldowns into routing, enforcement, cache, throttling, and observability handoffs.

---

## Bundle A Technical Spec

### Technical goals

1. keep `/gateway` and `/provider-profiles` as the canonical gateway admin surfaces
2. preserve the Rust gateway as the active data plane
3. keep provider and routing control coherent across routes, groups, policies, pass-through, and quotas

### Current implementation anchor points

- `apps/web/app/(dashboard)/gateway`
- `apps/web/app/(dashboard)/provider-profiles`
- gateway-related helpers in `apps/web/lib/api.ts`
- gateway-related types in `apps/web/types/api.ts`
- Rust runtime docs and service references under `docs/gateway/*` and the gateway runtime service tree
- supporting Python control-plane routers under `apps/api/runledger_api/routers/gateway*.py`

### Target architecture

- Rust data plane for live execution
- Python control-plane and support surfaces where intentionally retained
- `/gateway` as the active operator control plane
- `/provider-profiles` as the active provider catalog

### Data model expectations

- no duplicate provider or route-control domains outside the canonical surfaces
- provider metadata remains scope-aware
- route/policy objects remain explicit and operator-editable

### Schema expectations

- preserve complete provider and route lifecycle schemas
- expand summary schemas only where needed for explainability

### API contract changes

- preserve full provider CRUD
- preserve route/group/policy/pass-through lifecycle
- preserve embedded quota, cache-profile, and model-quota support

### UI requirements

- clear operator summaries for routes, providers, policies, and pass-through targets
- stronger explainability for route decisions and provider posture
- no scattered parallel control surfaces

### Cross-feature integration requirements

- must link clearly to AI hub, API keys, Observe, and Governance
- must link more clearly to FinOps cost posture without ceding financial ownership

### Delivery-surface requirements

- docs/Postman/scripts/examples must reflect the Rust data-plane split
- support assets must not imply Python is still the primary live gateway runtime

### Implementation phases

1. improve provider/routing explainability
2. improve FinOps and AI-hub bridges
3. harden runtime control-plane consistency

### Acceptance criteria

- operator-facing provider and routing control remains complete and coherent
- support assets consistently reflect the Rust runtime model
- cross-feature linkage to Observe, Governance, and Org & Access is stronger

### Product enhancement suggestions

- route explain panel
- provider posture dashboard
- config snapshots and comparison

---

## Bundle B Technical Spec

### Technical goals

1. keep guardrails as a complete runtime-protection operator surface
2. make guardrail effects easier to trace through request-analysis workflows
3. keep enforcement ownership clear relative to the Rust gateway data plane

### Current implementation anchor points

- `apps/web/app/(dashboard)/guardrails`
- violations log and related guardrail components
- backend guardrail routers/services and related policy/evidence hooks

### Target architecture

- guardrail management surface remains distinct
- runtime outcomes remain visible through violations and analysis surfaces
- Python-based enforcement stays explicit where still intentionally retained

### Data model expectations

- preserve rule, template, test, violation, and feedback entities
- expand summary and linkage entities where needed for traceability

### Schema expectations

- preserve rule CRUD and violation investigation contracts
- add or normalize link-summary payloads where needed for request-flow traceability

### API contract changes

- preserve current guardrail lifecycle
- optional linkage endpoints for richer request/run cross-navigation

### UI requirements

- maintain full guardrail lifecycle
- improve request-analysis and monitoring handoffs
- improve violation-to-policy-to-request traceability

### Cross-feature integration requirements

- must stay tightly linked to Tool Policies, Alert Rules, Audit Log, and Gateway runtime
- should improve linkage into Request Flow and Request Explorer

### Delivery-surface requirements

- docs/Postman/scripts/examples must continue reflecting the stronger guardrail lifecycle and violations workflow

### Implementation phases

1. improve runtime traceability
2. harden enforcement-path clarity
3. improve summary and feedback UX

### Acceptance criteria

- guardrails remains complete
- runtime traceability improves materially
- support assets stay aligned to actual enforcement behavior

### Product enhancement suggestions

- violation impact lens
- guardrail presets
- side-by-side request playback

---

## Bundle C Technical Spec

### Technical goals

1. keep cache and throttling controls embedded in Gateway
2. make performance-control outcomes easier to understand
3. strengthen the connection between these controls and runtime/observability/economics outcomes

### Current implementation anchor points

- `/gateway` embedded cache and rate-limit controls
- compatibility routes for `/response-cache` and `/rate-limits`
- supporting backend/runtime contracts for cache profiles, stats, rate overviews, quota tiers, and model quotas

### Target architecture

- no standalone cache or rate-limit product area
- cache and throttle controls live inside the gateway control plane
- observability and economics are downstream readers, not competing owners

### Data model expectations

- cache-profile lifecycle remains explicit
- throttle/overview/quota concepts remain embedded subdomains

### Schema expectations

- preserve cache profile CRUD and stats
- preserve rate overview, quota-tier, and model-quota contracts

### API contract changes

- no separate long-term top-level ownership contracts for cache/rate-limit surfaces
- optional analytics/diagnostics endpoints only if they strengthen embedded gateway ownership

### UI requirements

- all meaningful controls remain in `/gateway`
- compatibility routes remain redirect-only
- operators can understand runtime impact from the embedded surfaces

### Cross-feature integration requirements

- stronger links into Monitoring, Request Explorer, and Optimization surfaces
- clearer distinction from FinOps policy ownership

### Delivery-surface requirements

- docs/Postman/scripts/examples should consistently treat cache and rate limits as embedded Gateway capabilities

### Implementation phases

1. preserve embedded ownership
2. improve runtime/economics visibility
3. improve API-key and model-control understanding

### Acceptance criteria

- cache and rate limits remain embedded in `/gateway`
- runtime effects are easier to inspect
- support surfaces do not drift back toward standalone ownership

### Product enhancement suggestions

- route-level diagnostics
- performance-control simulator
- adaptive cache recommendations

---

## Bundle D Technical Spec

### Technical goals

1. keep the Rust data-plane ownership model explicit across the feature family
2. prevent architecture drift in docs, examples, scripts, and support surfaces
3. keep consumer understanding aligned with the shipped runtime model

### Current implementation anchor points

- gateway docs and runtime references
- `/gateway` operator surface
- compatibility routes for collapsed subfeatures
- support assets that still describe or exercise gateway behavior

### Target architecture

- live traffic executes on the Rust data plane
- Python control-plane and support surfaces remain only where intentionally retained
- product language stays consistent with that split

### Data model expectations

- no new data-plane confusion introduced through support assets or helper layers

### Schema expectations

- preserve operator-facing schemas
- architecture clarity comes mostly through docs, naming, and ownership discipline rather than new entity shapes

### API contract changes

- avoid reintroducing contracts that imply the old runtime ownership model
- align support assets to the real gateway API shape

### UI requirements

- Gateway UI can explain runtime ownership at a high level without turning into an architecture page

### Cross-feature integration requirements

- must stay aligned with Observe, Build & Improve, and Governance as they consume gateway behavior

### Delivery-surface requirements

- docs/examples/scripts/Postman/help surfaces must all reflect the Rust runtime model consistently

### Implementation phases

1. make runtime ownership explicit
2. remove old-path ambiguity
3. improve operator-facing architecture clarity

### Acceptance criteria

- Rust runtime ownership is clearly reflected across product and support surfaces
- no major support asset implies the old gateway runtime model
- operator understanding of the runtime split is materially clearer

### Product enhancement suggestions

- runtime ownership explainer
- consistency checker
- gateway architecture map

---

## Major-Feature Product Enhancement Ideas

These are high-level product suggestions for `Gateway & Routing` beyond the required implementation bar.

1. `Recommended next` Add a live routing decision preview that shows which route, provider, fallback, cache policy, and guardrail set would apply to a sample request.
2. `Recommended next` Add a unified “runtime posture” dashboard for providers, routes, cache, throttles, and guardrails from one top-level gateway overview.
3. `Recommended next` Add a route change impact preview before save, estimating likely latency, cost, and fallback effects.
4. `Recommended next` Add stronger provider economics views that tie provider profiles to model usage and route concentration.
5. `Recommended next` Add route-level anomaly detection that highlights sudden changes in latency, failures, or fallback frequency.
6. `Recommended next` Add side-by-side environment comparison for gateway config snapshots.
7. `Optional future enhancement` Add a flow-map view of runtime execution from ingress to route decision to provider response to downstream telemetry.
8. `Optional future enhancement` Add policy simulation that combines route policy, cache policy, rate controls, and guardrail posture in one preview.
9. `Optional future enhancement` Add per-workspace gateway posture summaries so org admins can compare runtime maturity across workspaces.
10. `Optional future enhancement` Add provider recommendation hints based on cost, latency, reliability, and model-usage outcomes.
11. `Optional future enhancement` Add an embedded Swagger/API explorer panel specifically for gateway and provider contracts.
12. `Optional future enhancement` Add a drift detector that flags when docs/examples/scripts/Postman stop matching the active Rust gateway runtime model.

## Bundle Acceptance Summary

`Gateway & Routing` is complete as a major-feature family when:

- `/provider-profiles` and `/gateway` remain the canonical active operator surfaces
- `Guardrails` remains complete and clearly integrated into runtime enforcement and evidence flows
- `Response cache` and `Rate limits` remain embedded gateway capabilities, not independent products
- the Rust gateway is clearly understood and preserved as the active data plane
- cross-feature cohesion with Org & Access, Observe, Governance, and Build & Improve remains strong or improves
- docs, Postman, scripts, and examples stay aligned to the shipped runtime model
