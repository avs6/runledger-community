# RunLedger Organization & Access Bundles Blueprint

Last updated: Friday, August 14, 2026

## Purpose

This file is the working blueprint for the `Organization & Access` feature family in RunLedger.

It is a product, architecture, and implementation guide derived from the shipped
feature audit in
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md).

This blueprint exists to turn the current `Organization & Access` audit,
crosswalk, and cohesion findings into implementation-ready bundle groupings.

## Organization & Access Vision

Organization & Access should feel like one cohesive administrative operating layer.

It should let a platform admin or org admin:

- create and recognize the right organization boundary
- establish users, workspaces, access groups, and API keys cleanly
- guide new adoption through onboarding rather than scattered setup pages
- connect MCP and model-access surfaces without duplicating ownership
- keep legacy `projects`, `team models`, and duplicate settings pages collapsed
- hand off naturally into Gateway, Observe, Safety & Governance, and FinOps

The target outcome is:

`Organization & Access = org foundation + identity + scope + setup + capability access`

not

`Organization & Access = a random list of admin pages`

## Audit-First Rule

This blueprint is derived from the audit, not the other way around.

The required input order for this file was:

1. `FEATURE-AUDIT.md`
2. `Organization & Access` feature rows and gap matrix
3. `Delivery Audit Crosswalk`
4. `Feature Cohesion Matrix`
5. bundle derivation and technical planning

If the `Organization & Access` section or the `11.3` cohesion matrix changes
materially, this blueprint should be updated.

## Feature-Audit to Bundle Mapping

This blueprint maps the `Organization & Access` rows from section `1` of
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
into four implementation bundles.

| Bundle | Bundle Name | Feature-AUDIT rows mapped into the bundle | Mapping notes |
|--------|-------------|--------------------------------------------|---------------|
| `Bundle A` | `Organization Foundation and Lifecycle` | `Organization profile`, `Org settings` | `Org settings` is legacy and remains collapsed into `Organization profile`; the bundle still owns the lifecycle and collapse discipline. |
| `Bundle B` | `Identity and Scope Control` | `Users`, `Workspaces`, `Access groups`, `API keys` | This is the strongest current operational bundle and already has the best completion state in the family. |
| `Bundle C` | `Onboarding and Connected Setup` | `Onboarding`, `Integrations`, `Telemetry`, `MCP registry` | `Integrations` is legacy and remains collapsed; `Telemetry` stays observability-owned but is included here because setup/discovery ownership begins in Org & Access. |
| `Bundle D` | `Workspace Capability Catalog and Legacy Transition` | `AI hub`, `Projects`, `Team models` | `Projects` and `Team models` stay retired/redirected; `AI hub` remains the active workspace capability catalog. |

Related crosswalk rows in
[DELIVERY-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/DELIVERY-AUDIT.md)
that materially support this family include:

- `1.2` Organizations and tenants
- `1.3` Workspaces
- `1.4` Users and memberships
- `1.5` API keys
- `1.6` RBAC and role-aware access
- `1.8` Onboarding and product tour
- `2.3` OTLP ingest
- `2.6` MCP ingest and control plane
- `8.7` Projects
- `8.8` AI hub
- `8.6` Plugins

## Bundle Overview

These bundles are derived from the audit and the `11.3 Organization & Access Cohesion Matrix`.

Recommended execution order:

1. `Bundle A` - Organization Foundation and Lifecycle
2. `Bundle B` - Identity and Scope Control
3. `Bundle C` - Onboarding and Connected Setup
4. `Bundle D` - Workspace Capability Catalog and Legacy Transition

Why this order:

1. the organization boundary and legacy collapse rules come first
2. identity and scope controls form the core runtime/admin primitives
3. onboarding and connected setup should sit on top of the settled org and access model
4. capability catalog and legacy cleanup should finish only after the underlying scope model is stable

---

## Bundle A - Organization Foundation and Lifecycle

### Product goal

Bundle A should establish the single coherent organization-admin home.

It should answer:

- where organization metadata is managed
- where org members, workspaces, and org-owned settings begin
- how platform lifecycle ownership differs from org lifecycle ownership
- which routes are canonical and which are compatibility redirects

### Scope

- `Organization profile`
- `Org settings`

### Derivation from the audit

From the feature rows:

- `Organization profile` is complete and is the canonical org-admin entry point
- `Org settings` is legacy and already collapsed into `/organization`

From the Delivery Audit Crosswalk:

- `1.2` and `1.7` already connect org lifecycle and settings coverage, but platform settings remain partial overall

From the cohesion matrix:

- `Organization profile` is strong with `Workspaces`, and partial with several downstream surfaces
- `Org settings` should remain collapsed and not re-emerge as a separate long-term feature

### Current state summary

Strengths:

- `/organization` is already a real org console
- org metadata and org-owned settings are aligned across backend, UI, docs, Postman, and scripts

Weaknesses:

- org rollups into FinOps, Observe, and Governance are still more summary-shaped than deeply operational
- platform vs org lifecycle boundaries need to stay explicit

### Bundle-level route ownership

- primary: `/organization`
- compatibility redirect only: `/org-settings`
- related but not owned here: `/organizations`

### Operator workflow

1. enter the organization console
2. review org metadata and org-level posture
3. manage org-scoped settings and members
4. hand off into workspaces, users, access groups, and API keys
5. consume cross-feature rollups without duplicating editing surfaces

### Matrix-derived gap inventory

Internal gaps:

- collapse discipline for `Org settings` must remain permanent

Cross-feature gaps:

- `Organization profile x Budget detail = GAP`
- `Organization profile x Analytics / governance / runtime posture = PARTIAL`
- org profile should summarize without absorbing downstream ownership

Platform gaps:

- boundary between `/organization` and `/organizations` must stay legible

### Architecture and ownership notes

Bundle A owns:

- org-admin home
- org metadata
- collapsed org-settings behavior

Bundle A does not own:

- platform org lifecycle creation/deletion
- budget editing
- gateway control-plane editing
- observability drilldowns

### Cross-feature integration requirements

- must consume budget and analytics rollups as summaries
- must link cleanly into workspaces, users, access groups, and API keys
- must not duplicate platform settings or platform org lifecycle surfaces

### Implementation phases

#### Phase A1 - Lock the canonical org-admin home

- keep `/organization` as the single org-admin home
- keep `/org-settings` as redirect-only
- tighten copy, tabs, and route ownership language

#### Phase A2 - Strengthen org rollup summaries

- add better read-only org posture summaries for spend, activity, and governance
- keep editing ownership in the downstream features

#### Phase A3 - Strengthen platform/org boundary clarity

- make explicit what stays in `/organizations`, `/organization`, and `/settings`

### Bundle polish opportunities

- better org summary cards
- clearer org-to-workspace handoff
- stronger empty states for newly created orgs

### Product enhancement ideas and suggestions

1. `Recommended next` Add an org readiness score that summarizes whether users, workspaces, access groups, API keys, and onboarding milestones are in place.
2. `Optional future enhancement` Add an org timeline that shows major administrative events like user imports, workspace creation, API-key rotation, and major settings changes.
3. `Optional future enhancement` Add a guided “org health walkthrough” that suggests the next best administrative action after initial setup.

---

## Bundle B - Identity and Scope Control

### Product goal

Bundle B should make identity and operational scope feel like one coherent system.

It should answer:

- who belongs to the organization
- which workspaces exist
- how access groups and API keys define operational scope
- how runtime, governance, and observability features inherit these scopes

### Scope

- `Users`
- `Workspaces`
- `Access groups`
- `API keys`

### Derivation from the audit

From the feature rows:

- all four features are complete and strong individually
- this is the most mature part of the family

From the Delivery Audit Crosswalk:

- `1.3`, `1.4`, `1.5`, and `1.6` all show strong backend/UI/docs/Postman/script coverage, with examples still somewhat indirect

From the cohesion matrix:

- `Workspaces` are the strongest cross-feature primitive
- `Access groups` are strategically important but still under-threaded
- `API keys` are operationally strong but still split between org and gateway stories
- `Users` need a stronger identity story that spans observability, governance, and build surfaces

### Current state summary

Strengths:

- CRUD is real and end-to-end
- roles and access behaviors are already aligned
- runtime-facing features already use workspaces and API keys meaningfully

Weaknesses:

- `Access groups` do not yet appear strongly enough in Observe and Build & Improve
- `API keys` are strong administratively but not yet a first-class investigation dimension everywhere
- user identity story still feels partially fragmented

### Bundle-level route ownership

- `/users`
- `/workspace`
- `/access-groups`
- `/api-keys`

### Operator workflow

1. create or review users
2. create workspaces
3. assign members and access groups
4. issue or rotate API keys
5. hand off to gateway, governance, and observability surfaces that consume these scopes

### Matrix-derived gap inventory

Internal gaps:

- identity and scope concepts are strong individually but not yet fully unified as one story

Observe gaps:

- `Access groups x Runs / Request Explorer / Request Flow = GAP or PARTIAL`
- `API keys x Observe = PARTIAL`

Governance gaps:

- `Users x Approvals / Audit / Security = PARTIAL`
- `API keys x policy evidence = PARTIAL`

Build gaps:

- `Access groups x Build surfaces = PARTIAL`
- `API keys x execution/evaluation surfaces = PARTIAL`

### Architecture and ownership notes

Bundle B owns:

- operational identity and scope primitives

Bundle B does not own:

- gateway technical quotas themselves
- downstream financial editing
- deep runtime observability pages

### Cross-feature integration requirements

- must remain the primary scope model for Gateway
- must feed FinOps scoping and allocation
- must become more visible in Observe and Build & Improve
- must participate clearly in Governance evidence and policy context

### Implementation phases

#### Phase B1 - Strengthen the scope model as a cross-suite primitive

- make workspace, access group, and API-key ownership language consistent
- remove remaining ambiguity where scope identity is implied rather than explicit

#### Phase B2 - Improve downstream visibility of access groups and API keys

- strengthen Observe usage of access groups and API-key identity
- add stronger links from API keys into runtime and investigation surfaces

#### Phase B3 - Tighten user and role cohesion

- strengthen user linkage into approvals, audit, and user analytics
- improve role-aware summaries across org-admin surfaces

### Bundle polish opportunities

- clearer scope badges and inherited ownership hints
- better identity-to-runtime drill-ins
- stronger “where is this used?” views

### Product enhancement ideas and suggestions

4. `Recommended next` Add a scope lineage view that shows how a user, workspace, access group, and API key relate to each other.
5. `Recommended next` Add an “impact before delete” preview for deleting workspaces, access groups, or API keys so admins understand downstream effects.
6. `Optional future enhancement` Add a cross-suite “where used” panel for any API key or access group spanning Gateway, Observe, FinOps, and Governance.

---

## Bundle C - Onboarding and Connected Setup

### Product goal

Bundle C should make first-run setup and connected-stack adoption feel intentional.

It should answer:

- how a new org should start using the platform
- where Claude, Codex, MCP, telemetry, and plugin discovery begin
- which setup surfaces are discovery-only versus true managed entities

### Scope

- `Onboarding`
- `Integrations`
- `Telemetry`
- `MCP registry`

### Derivation from the audit

From the feature rows:

- `Onboarding` is intentionally guide-shaped and still in progress
- `Integrations` is legacy and collapsed
- `Telemetry` is complete but observability-owned
- `MCP registry` is complete and consolidated

From the Delivery Audit Crosswalk:

- `1.8`, `2.3`, `2.6`, and `8.6` show that onboarding/setup coverage is broadly present but still partial in places, especially around README/examples/plugins

From the cohesion matrix:

- `Onboarding` is strong with Build & Improve entry points
- `MCP registry` is already strong in Governance and reasonably strong in org/workspace inheritance
- `Telemetry` should stay correctly owned by Observe while still being setup-discoverable here

### Current state summary

Strengths:

- setup/discovery ownership has already been rationalized
- MCP is consolidated
- Integrations is already collapsed

Weaknesses:

- onboarding is still not fully complete by its non-CRUD completion bar
- plugin/setup discovery remains partial
- telemetry and MCP setup handoff can still be more cohesive

### Bundle-level route ownership

- primary guide surface: `/onboarding`
- legacy redirect only: `/integrations`
- managed entity surface: `/mcp-registry`
- observability-owned setup handoff: `/monitoring/telemetry`

### Operator workflow

1. enter onboarding
2. choose connected setup path
3. move to MCP setup, telemetry setup, or external-tool discovery
4. complete managed setup in the owning surface
5. return to onboarding for next-step guidance

### Matrix-derived gap inventory

Internal gaps:

- onboarding is strong as a guide, but still incomplete as a coverage surface
- integrations collapse must stay durable

Cross-feature gaps:

- plugin discovery remains partial
- telemetry setup belongs here as discovery, but not as deep operations ownership
- MCP should feel more native in Build & Improve and Runtime workflows over time

### Architecture and ownership notes

Bundle C owns:

- setup discovery
- guided adoption
- route collapse discipline for old setup surfaces

Bundle C does not own:

- deep telemetry operations
- gateway control-plane editing
- plugin execution control planes

### Cross-feature integration requirements

- must hand off cleanly into MCP registry
- must hand off cleanly into Telemetry
- must remain the discovery entry point for plugin and external-tool setup
- must be explicit about what is guide-only versus CRUD-owned elsewhere

### Implementation phases

#### Phase C1 - Complete onboarding as a guide surface

- finish setup coverage for onboarding flows
- tighten recommendations and next-step logic

#### Phase C2 - Tighten managed-surface handoffs

- strengthen transitions from onboarding to MCP registry and telemetry
- make plugin discovery paths clearer

#### Phase C3 - Preserve collapse and ownership clarity

- keep integrations legacy
- keep telemetry observability-owned
- keep CRUD where it belongs

### Bundle polish opportunities

- richer onboarding progress model
- setup readiness summaries
- “what’s next?” guided flows

### Product enhancement ideas and suggestions

7. `Recommended next` Add an onboarding checklist that adapts based on which surfaces are already configured for an organization.
8. `Recommended next` Add setup health checks for MCP, telemetry, and plugin connectivity with “fix this now” links.
9. `Optional future enhancement` Add role-based onboarding paths so org admins, platform admins, and builders see different setup journeys.

---

## Bundle D - Workspace Capability Catalog and Legacy Transition

### Product goal

Bundle D should keep capability access modern while preventing legacy concepts from re-entering the product model.

It should answer:

- where workspace-level model access and capability discovery live
- how retired concepts stay retired
- how model access, provider access, and workspace scope stay coherent

### Scope

- `AI hub`
- `Projects`
- `Team models`

### Derivation from the audit

From the feature rows:

- `AI hub` is complete and strong
- `Projects` is retired and redirect-only
- `Team models` is retired and redirect-only

From the Delivery Audit Crosswalk:

- `8.8` is strong end-to-end
- `8.7` remains legacy but still needs cleanup discipline

From the cohesion matrix:

- `AI hub` is already strong with `Provider profiles`, `Model gateway`, and `Model usage`
- retired features must stay retired, not drift back into active product vocabulary

### Current state summary

Strengths:

- AI hub is a finished workspace model-catalog surface
- legacy routes are already out of the active workflow

Weaknesses:

- AI hub still needs clearer bridges into org-admin and approval/evidence flows
- legacy cleanup must remain an active discipline in docs/types/scripts

### Bundle-level route ownership

- `/ai-hub`
- redirect only: `/projects`
- redirect only: `/team-models`

### Operator workflow

1. discover or review available workspace capabilities in AI hub
2. manage provider sync, access requests, and deprecation
3. never use legacy project/team-model routes for new workflows

### Matrix-derived gap inventory

Internal gaps:

- AI hub is strong, but its relationship to the broader org-admin flow can still tighten
- legacy routes must stay minimized across docs and support surfaces

Cross-feature gaps:

- AI hub should integrate more clearly with approvals and evidence around model access
- AI hub should remain tightly linked to provider and model-intelligence surfaces

### Architecture and ownership notes

Bundle D owns:

- active workspace capability catalog
- legacy retirement discipline for related retired routes

Bundle D does not own:

- provider profile pricing surface
- gateway routing control
- model-usage analytics

### Cross-feature integration requirements

- must stay tightly linked to Provider Profiles and Gateway
- must bridge into Model Usage and Scorecards
- must keep retired concepts from reappearing in org/access workflows

### Implementation phases

#### Phase D1 - Protect the canonical capability-catalog story

- keep AI hub as the active workspace capability catalog
- keep model access language aligned to workspace-first primitives

#### Phase D2 - Deepen model-access governance links

- strengthen approval, deprecation, and evidence pathways
- improve org-admin discoverability of model capability posture

#### Phase D3 - Finish legacy cleanup discipline

- keep projects and team models redirect-only
- remove remaining support-surface dependence on those concepts where practical

### Bundle polish opportunities

- better capability inventory summaries
- clearer access-request history
- stronger provider-to-model-to-workspace drill-ins

### Product enhancement ideas and suggestions

10. `Recommended next` Add a capability posture dashboard in AI Hub that shows provider freshness, deprecations, pending access requests, and policy conflicts.
11. `Optional future enhancement` Add a model capability comparison view that blends AI Hub metadata with Gateway compatibility and usage signals.
12. `Optional future enhancement` Add a legacy-cleanup scanner that flags leftover `project` or `team_model` language across docs, scripts, and support assets.

---

## Bundle A Technical Spec

### Technical goals

1. preserve `/organization` as the single canonical org-admin home
2. keep `/org-settings` collapsed permanently
3. expose org-level summaries without duplicating downstream control-plane ownership

### Current implementation anchor points

- org console routes and components under `apps/web/app/(dashboard)/organization`
- compatibility redirect logic for `/org-settings`
- relevant org admin backend routers and schemas under `apps/api/runledger_api/routers`

### Target architecture

- one canonical org-admin shell
- redirect-only compatibility for collapsed settings route
- summary-driven integration with downstream feature families

### Data model expectations

- no new duplicate org-settings entity
- org metadata remains primary
- org-level summary fields may be computed/read-only aggregates

### Schema expectations

- preserve org metadata update contract
- add read-only org posture summary schema only if needed

### API contract changes

- preserve current org lifecycle contracts
- optional read-only org posture summary endpoint if summaries are not already practical from existing surfaces

### UI requirements

- `/organization` remains primary
- `/org-settings` redirects only
- clear tab ownership
- read-only summaries with drill-through links

### Cross-feature integration requirements

- links into workspaces, users, budgets, analytics, governance, and platform lifecycle must stay clear

### Delivery-surface requirements

- docs must say `/organization` is canonical
- Postman and scripts must not treat `/org-settings` as a primary route

### Implementation phases

1. lock route ownership
2. improve org summaries
3. clarify platform/org lifecycle boundaries

### Acceptance criteria

- `/organization` is the only active org-admin surface
- `/org-settings` stays redirect-only
- docs/support surfaces reflect that ownership

### Product enhancement suggestions

- org maturity scoring
- org admin event timeline
- org setup walkthrough

---

## Bundle B Technical Spec

### Technical goals

1. keep users, workspaces, access groups, and API keys as the core scope model
2. improve access-group and API-key visibility across the suite
3. strengthen the shared identity story across runtime, observability, and governance

### Current implementation anchor points

- `apps/web/app/(dashboard)/users`
- `apps/web/app/(dashboard)/workspace`
- `apps/web/app/(dashboard)/access-groups`
- `apps/web/app/(dashboard)/api-keys`
- corresponding API helpers/types and backend routers

### Target architecture

- one coherent identity and scope domain
- workspaces as primary operational boundary
- access groups and API keys as first-class derived scopes

### Data model expectations

- no new legacy scope primitives
- strengthen metadata and references that connect users, workspaces, access groups, and API keys

### Schema expectations

- preserve CRUD schemas
- expand supporting summary schemas where needed for downstream visibility

### API contract changes

- mostly preserve current CRUD
- add or normalize supporting “where used” or relationship summary endpoints only where needed

### UI requirements

- real CRUD remains
- stronger linkage between identities and their downstream usage
- better visibility of scope inheritance and operational impact

### Cross-feature integration requirements

- must feed Gateway, FinOps, Observe, Safety & Governance, and Build & Improve consistently

### Delivery-surface requirements

- docs and examples should describe workspaces/access groups/API keys as the real scope model
- support assets should avoid legacy `teams/projects` language

### Implementation phases

1. standardize scope language
2. improve access-group/API-key downstream visibility
3. improve user-role and identity cohesion

### Acceptance criteria

- CRUD remains complete
- downstream visibility of access groups and API keys improves materially
- user/workspace/access-key relationships are easier to understand operationally

### Product enhancement suggestions

- scope lineage view
- impact-before-delete preview
- cross-suite “where used” panel

---

## Bundle C Technical Spec

### Technical goals

1. make onboarding a complete guide surface
2. preserve integrations collapse and ownership clarity
3. keep MCP and telemetry setup discovery strong while leaving deep operations in the owning surfaces

### Current implementation anchor points

- `apps/web/app/(dashboard)/onboarding`
- `apps/web/app/(dashboard)/mcp-registry`
- telemetry handoff routes under `apps/web/app/(dashboard)/monitoring/telemetry`
- collapsed integrations/plugin discovery references

### Target architecture

- onboarding as discovery shell
- MCP registry as managed setup surface
- telemetry as observability-owned but setup-discoverable
- integrations as redirect-only compatibility

### Data model expectations

- onboarding remains guide-oriented, not a managed entity
- MCP registry remains the real CRUD domain in this bundle

### Schema expectations

- onboarding may need progress/health summary schemas
- MCP schemas should preserve full lifecycle support

### API contract changes

- preserve current MCP lifecycle contracts
- optional onboarding/setup readiness or setup-health contracts if needed

### UI requirements

- stronger setup checklist and health signaling
- better next-step guidance
- explicit ownership handoff from onboarding to the actual managed surface

### Cross-feature integration requirements

- must connect to plugins, MCP, telemetry, and external-tool setup guidance
- must not recreate deep operations surfaces

### Delivery-surface requirements

- docs, labs, and examples should treat onboarding as the guide surface
- support materials should treat integrations as legacy

### Implementation phases

1. complete onboarding coverage
2. improve setup handoffs and health checks
3. preserve route collapse discipline

### Acceptance criteria

- onboarding is complete by its guide-surface completion bar
- integrations remains collapsed
- MCP and telemetry setup handoffs are explicit and cohesive

### Product enhancement suggestions

- adaptive onboarding checklist
- setup health checks
- role-based onboarding paths

---

## Bundle D Technical Spec

### Technical goals

1. keep AI Hub as the active workspace capability catalog
2. keep `Projects` and `Team models` retired
3. improve model-access and capability visibility without reopening legacy abstractions

### Current implementation anchor points

- `apps/web/app/(dashboard)/ai-hub`
- compatibility routes for `/projects` and `/team-models`
- related backend/type cleanup for retired concepts

### Target architecture

- AI Hub as the active capability catalog
- retired compatibility routes only for legacy entries
- stronger bridges to provider, gateway, and model-intelligence surfaces

### Data model expectations

- no new `project` or `team_model` dependence
- AI Hub remains workspace-scoped and provider-aware

### Schema expectations

- preserve real AI Hub CRUD and sync behavior
- no new public schemas that deepen retired concepts

### API contract changes

- preserve AI Hub CRUD and sync contracts
- preserve redirect/compatibility behavior for retired routes only where still needed

### UI requirements

- AI Hub remains a first-class active page
- retired routes do not reappear as active navigation concepts
- stronger model-access governance and posture visibility

### Cross-feature integration requirements

- must stay linked to Provider Profiles, Gateway, Model Usage, and Model Scorecards
- must support org-admin visibility without moving ownership out of AI Hub

### Delivery-surface requirements

- docs/scripts/examples must not reintroduce projects/team-models as active product areas
- AI Hub support coverage should remain complete

### Implementation phases

1. preserve AI Hub ownership
2. improve governance/access posture links
3. continue legacy cleanup discipline

### Acceptance criteria

- AI Hub remains complete and cohesive
- projects and team models remain retired
- support surfaces do not reintroduce those concepts

### Product enhancement suggestions

- capability posture dashboard
- model capability comparison view
- legacy language scanner

---

## Major-Feature Product Enhancement Ideas

These are high-level product suggestions for `Organization & Access` beyond the required implementation bar.

1. `Recommended next` Add a unified “scope map” page that visually connects organizations, workspaces, access groups, API keys, MCP servers, and AI Hub capabilities.
2. `Recommended next` Add an admin search bar that can find any user, workspace, access group, API key, MCP server, or model capability from one place.
3. `Recommended next` Add posture badges across the family for “configured”, “partially configured”, “inactive”, and “needs attention”.
4. `Recommended next` Add stronger read-only org summaries for FinOps, Gateway, and Governance posture directly inside `/organization`.
5. `Recommended next` Add a scope-impact report before deleting or disabling any identity or access object.
6. `Optional future enhancement` Add bulk import/export for users, workspaces, access groups, and API keys with dry-run validation.
7. `Optional future enhancement` Add policy recommendations that suggest where to create access groups based on repeated user-to-workspace patterns.
8. `Optional future enhancement` Add model-access simulation from AI Hub that shows what a specific user, access group, or API key can actually reach.
9. `Optional future enhancement` Add “first 24 hours” onboarding mode for brand-new organizations with explicit next-step handoffs.
10. `Optional future enhancement` Add more embedded documentation and side-panel help for each admin surface.
11. `Optional future enhancement` Add audit-friendly change summaries whenever admins alter access structures or key assignments.
12. `Optional future enhancement` Add a workspace-template model so new orgs can stamp out a standard initial setup quickly.

## Bundle Acceptance Summary

`Organization & Access` is complete as a major-feature family when:

- canonical route ownership is clear and legacy redirects stay collapsed
- users, workspaces, access groups, and API keys remain strong end-to-end managed entities
- onboarding is complete by its guide-surface bar
- MCP and telemetry setup handoffs are cohesive
- AI Hub remains the active capability catalog
- projects and team models remain retired
- docs, Postman, scripts, examples, and support language stay aligned to the workspace-first model
