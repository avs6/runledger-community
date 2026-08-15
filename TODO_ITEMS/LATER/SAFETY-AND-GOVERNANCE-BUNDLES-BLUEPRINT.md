# RunLedger Safety and Governance Bundles Blueprint

Last updated: Friday, August 14, 2026

## Purpose

This file is the working blueprint for the `Safety & Governance` major feature
family in RunLedger.

It is derived from:

- [FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
- [DELIVERY-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/DELIVERY-AUDIT.md)

This blueprint converts the current Safety and Governance audit, Feature Gap
Matrix findings, delivery crosswalk, and cohesion matrix into implementation
bundles, technical specs, and product-improvement ideas.

## Safety and Governance Vision

Safety and Governance should feel like one cohesive control and evidence layer
for the whole suite.

It should let operators:

- define what tools, actions, and data-handling behaviors are allowed
- simulate and test policy behavior before enforcing it
- manage exceptions and human approval paths
- protect data, identity, and workspace boundaries
- detect and respond to operational or compliance issues
- prove what happened through evidence, audit trails, and governance exports

The target outcome is:

`Safety & Governance = runtime controls + exception workflows + data protection + evidence closure`

not

`Safety & Governance = separate admin pages with weak runtime linkage`

## Audit-First Rule

This blueprint is derived from the audit, not the reverse.

The required input order for this file was:

1. `FEATURE-AUDIT.md`
2. the `Safety & Governance` rows and related Feature Gap Matrix entries
3. the `Delivery Audit Crosswalk`
4. the `11.6 Safety & Governance Cohesion Matrix`
5. bundle derivation, technical specs, and implementation sequencing

If the feature rows or the `11.6` cohesion matrix change materially, this
blueprint should be updated.

## Feature-Audit to Bundle Mapping

This blueprint maps the `Safety & Governance` rows from section `4` of
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
into four implementation bundles.

| Bundle | Bundle Name | Feature-AUDIT rows mapped into the bundle | Mapping notes |
|--------|-------------|--------------------------------------------|---------------|
| `Bundle A` | `Tool Governance Control Plane` | `MCP servers`, `Search tools`, `Tool registry`, `Tool policies`, `Policy dry run` | `MCP servers`, `Search tools`, and `Policy dry run` are compatibility-only collapsed surfaces. Long-term ownership lives in `MCP registry`, `Tool registry`, and `Tool policies`. |
| `Bundle B` | `Exception and Response Workflows` | `Approvals`, `Alert rules` | These are the action and exception layer for governance: one human-in-the-loop path and one automated response path. |
| `Bundle C` | `Data Protection, Security, and Taxonomy` | `Data capture`, `Security`, `Tags` | These form the scoped policy posture layer for privacy, access protection, and shared classification. |
| `Bundle D` | `Evidence, Audit, and Compliance Closure` | `Audit log`, `Governance pack` | These are downstream evidence and compliance surfaces that should consume upstream governance activity cleanly. |

Material delivery-crosswalk support for this family comes from:

- `7.5` Approvals
- `7.6` Alerts
- `7.8` Policy dry-run
- `7.9` Governance pack and audit
- `7.10` Data capture studio
- `7.11` Tag management
- `7.12` Search tools
- `7.13` Tool registry
- `7.14` Tool policies
- `7.16` Security settings
- supporting adjacency from `2.6`, `4.1`, `4.5`, and `8.5`

## Bundle Overview

The Safety and Governance family should be implemented and maintained in this
order:

1. `Bundle A` Tool Governance Control Plane
2. `Bundle B` Exception and Response Workflows
3. `Bundle C` Data Protection, Security, and Taxonomy
4. `Bundle D` Evidence, Audit, and Compliance Closure

That order follows the operator workflow:

1. define runtime governance rules and registry posture
2. manage exceptions and active response behavior
3. enforce data and security posture at the right scopes
4. prove and export what happened through evidence and audit surfaces

## Bundle A - Tool Governance Control Plane

### Product goal

Make tool-governance ownership explicit and cohesive so operators can manage
what tools exist, what policies apply, and how dry-run validation works without
splitting across legacy pages.

### Scope

- MCP servers
- Search tools
- Tool registry
- Tool policies
- Policy dry run

### Derivation from the audit

This bundle is derived from:

- the feature rows that mark `Tool registry` and `Tool policies` as complete
  primary surfaces
- the collapse notes showing that `MCP servers`, `Search tools`, and
  `Policy dry run` are compatibility routes rather than long-term owners
- the delivery crosswalk rows `7.8`, `7.12`, `7.13`, and `7.14`, plus adjacent
  support from `2.6` and `8.5`
- the `11.6` cohesion matrix, which shows strong ties to Gateway runtime, MCP,
  and governance itself, but only partial ties to scope-aware identity and
  financial posture

### Current state summary

- backend: complete for active surfaces
- UI: complete for active surfaces
- actions: real create, edit, deactivate, testing, and simulation flows exist
- docs/Postman/scripts/examples: aligned for the current operator surface
- residual gap: runtime governance is stronger than before, but deeper
  scope-aware enforcement on the hot path is still tracked as a later phase

### Bundle-level route ownership

- canonical control planes:
  - `/tool-registry`
  - `/tool-policies`
- compatibility routes:
  - `/mcp` -> `/mcp-registry?tab=setup`
  - `/search-tools` -> `/tool-registry?tab=search`
  - `/policy-dry-run` -> `/tool-policies?tab=dry-run`
- neighboring owner:
  - `/mcp-registry` remains the real MCP server setup and lifecycle surface

### Operator workflow

1. register or review runtime tools and search providers
2. define or update tool policies
3. simulate policy impact in dry-run mode
4. connect the result to runtime gateway enforcement and downstream evidence

### Matrix-derived gap inventory

#### Internal feature gaps

- keep collapsed routes from re-expanding into duplicate control planes
- preserve shared ownership between registry and policy surfaces clearly

#### Scope and ownership gaps

- stronger workspace, access-group, and API-key context propagation is still
  needed in some policy stories
- MCP governance remains adjacent and strong, but should stay clearly partitioned

#### Runtime gaps

- richer scope-aware hot-path enforcement is still future work
- runtime matching is still more tool/action-centric than full scope-context
  aware

#### FinOps and identity gaps

- approvals and budget-related governance relationships are still only partial
- financial and identity posture should surface more directly in governance views

### Architecture and ownership notes

This bundle owns:

- tool and search-provider registry posture
- policy authoring and policy simulation
- compatibility handling for collapsed dry-run and search pages

This bundle does not own:

- MCP server lifecycle as a top-level management area
- gateway route CRUD
- evidence export and compliance packs

### Cross-feature integration requirements

- `Gateway & Routing` for live tool/action governance
- `Organization & Access` for workspace, access-group, and API-key scope
- `Observe` for runtime traces and request investigation
- `FinOps` for future budget-aware exception or policy relationships
- `MCP registry` as the neighboring setup and lifecycle owner

### Implementation phases

#### Phase A1 - Preserve control-plane ownership

- keep Tool Registry and Tool Policies as the canonical governance control planes
- keep the collapsed routes as compatibility-only entry points

#### Phase A2 - Deepen runtime cohesion

- strengthen handoff from policy authoring to runtime enforcement evidence
- make tool-governance decisions easier to trace into request analysis

#### Phase A3 - Deepen scope awareness

- plan the future pass for workspace/access-group-aware runtime policy
  enforcement without reopening the completed CRUD surfaces

### Bundle polish opportunities

- better policy-to-runtime impact summaries
- clearer dry-run result comparisons
- richer registry health and usage posture cards

### Product enhancement ideas and suggestions

1. `Recommended next` Add a policy impact summary that explains which workspaces, tools, and request classes will be affected before a policy is activated.
2. `Recommended next` Add richer dry-run diff views that compare current behavior versus proposed policy behavior side by side.
3. `Optional future enhancement` Add a scope-aware policy inheritance viewer so operators can see global, org, workspace, and access-group governance resolution in one place.

---

## Bundle B - Exception and Response Workflows

### Product goal

Make governance actionable by combining human exception handling and automated
response workflows into one cohesive operator story.

### Scope

- Approvals
- Alert rules

### Derivation from the audit

This bundle is derived from:

- the feature rows showing both surfaces are complete and operationally real
- the Feature Gap Matrix emphasis that the remaining need is cohesion and
  broader adoption rather than missing CRUD
- delivery crosswalk rows `7.5` and `7.6`
- the `11.6` matrix, which shows approvals need stronger ties to budgets,
  model access, and scope governance, while alerts already bridge monitoring and
  runtime signals more strongly

### Current state summary

- approvals now has real auto-approval policy lifecycle and runtime application
- alert rules now has real edit-in-place lifecycle and operator-ready updates
- support coverage is aligned
- remaining gap is not baseline functionality; it is broader cross-suite
  adoption and clearer linkage to other exception-causing surfaces

### Bundle-level route ownership

- canonical routes:
  - `/approvals`
  - `/alert-rules`
- neighboring owners:
  - budgets and overrides remain in FinOps
  - monitoring and telemetry remain in Observe

### Operator workflow

1. define what can auto-approve and what requires review
2. receive alerts when policy, quality, cost, or runtime conditions breach
3. review or resolve approval requests
4. use the outcomes to refine governance and operating posture

### Matrix-derived gap inventory

#### Internal feature gaps

- approvals and alerts both work, but still read as separate tools more than one
  joint governance action layer

#### Scope and ownership gaps

- approvals should connect more clearly to model access, budget overrides, and
  high-risk tool actions
- alerts should express scope identity more consistently in org/workspace terms

#### Runtime and observability gaps

- stronger pivots into request investigation and monitoring context would help
- alert conditions should increasingly reflect policy and budget posture too

#### Governance-adoption gaps

- approvals is still underused as a general exception path
- alert rules can become the stronger action layer for cross-feature posture

### Architecture and ownership notes

This bundle owns:

- exception workflows
- human review paths
- automated response triggers

This bundle does not own:

- deep evidence export
- budget-management source of truth
- monitoring dashboards themselves

### Cross-feature integration requirements

- `FinOps` for budget overrides and budget breach exception paths
- `Organization & Access` for model access and scope-sensitive approval contexts
- `Observe` for alert-driven drill-ins
- `Gateway & Routing` for runtime-policy and rate/traffic-driven conditions
- `Build & Improve` for future evaluation or rollout approvals if introduced

### Implementation phases

#### Phase B1 - Preserve completed lifecycle depth

- keep approvals and alerts functionally complete
- do not regress into create-only or delete-and-recreate flows

#### Phase B2 - Strengthen exception cohesion

- improve links between approvals and budget/model/tool governance
- make alerts easier to interpret in context

#### Phase B3 - Grow suite-wide adoption

- use approvals as the standard exception path
- use alerts as the common governance response layer

### Bundle polish opportunities

- better queue prioritization
- stronger alert severity visualization
- clearer approval reason and impact summaries

### Product enhancement ideas and suggestions

4. `Recommended next` Add a unified governance action inbox that shows approvals, alert acknowledgements, and recent policy-triggered exceptions in one place.
5. `Recommended next` Add alert-to-investigation pivots that open the relevant request, run, or telemetry context pre-filtered.
6. `Optional future enhancement` Add approval templates for common scenarios such as model access, temporary budget override, risky tool use, or external integration enablement.

---

## Bundle C - Data Protection, Security, and Taxonomy

### Product goal

Create one cohesive scoped-policy layer for privacy, security posture, and
shared classification without turning those surfaces into isolated islands.

### Scope

- Data capture
- Security
- Tags

### Derivation from the audit

This bundle is derived from:

- the feature rows showing all three surfaces are complete and operator-usable
- the Feature Gap Matrix emphasis that the remaining work is cohesion, not CRUD
- delivery crosswalk rows `7.10`, `7.11`, and `7.16`
- the `11.6` matrix, which shows Security is one of the strongest governance
  blocks, Data Capture still risks reading as privacy-only, and Tags is a
  strategically important shared scoping primitive

### Current state summary

- data capture has complete scoped override lifecycle
- security has complete managed-entity depth across posture, OIDC, and IP ACLs
- tags has full taxonomy and auto-tagging lifecycle
- remaining gaps are cross-feature: consistent scope usage, stronger runtime
  evidence linkage, and broader use of tags as a shared product primitive

### Bundle-level route ownership

- canonical routes:
  - `/data-capture`
  - `/security`
  - `/tags`
- neighboring owners:
  - organization profile remains the org-admin summary shell
  - platform settings remains home for some platform-level compliance posture

### Operator workflow

1. define data-handling posture by scope
2. define security posture, identity providers, and network controls
3. define or update tags and auto-tagging rules
4. let those choices propagate into runtime, evidence, and analytics surfaces

### Matrix-derived gap inventory

#### Internal feature gaps

- data capture, security, and tags are each strong alone, but not always
  presented as one coherent scoped-policy layer

#### Scope and ownership gaps

- stronger shared use of workspace, access-group, and API-key identity is needed
- tags should become a clearer shared classification primitive across the suite

#### Runtime gaps

- data-capture and tag posture should connect more directly to runtime decisions
- security posture should keep feeding gateway and monitoring views more clearly

#### Evidence and analytics gaps

- stronger links into audit log, governance pack, and observability would help
- tags should show up more explicitly in attribution and evidence flows

### Architecture and ownership notes

This bundle owns:

- scoped privacy/data-capture posture
- scoped security configuration
- taxonomy and auto-tagging lifecycle

This bundle does not own:

- runtime request analysis
- final evidence export
- budget or billing policy

### Cross-feature integration requirements

- `Organization & Access` for scope and ownership
- `Gateway & Routing` for runtime posture influence
- `Observe` for monitoring and request-analysis evidence
- `FinOps` for attribution and chargeback enrichment through tags
- `Governance pack` and `Audit log` for downstream evidence usage

### Implementation phases

#### Phase C1 - Preserve scoped-policy ownership

- keep data capture, security, and tags as the clear source of truth for their
  respective domains

#### Phase C2 - Deepen shared scope posture

- make workspace, access-group, and org posture more visible and consistent
- make tags a more clearly shared cross-feature primitive

#### Phase C3 - Strengthen downstream usage

- improve how these surfaces feed runtime, evidence, and attribution layers

### Bundle polish opportunities

- better policy posture dashboards
- richer hierarchy and inheritance explainers
- stronger tag-usage summaries across the suite

### Product enhancement ideas and suggestions

7. `Recommended next` Add a scope posture map that shows security, data-capture, and tag policy state side by side for platform, org, workspace, and access-group scopes.
8. `Recommended next` Add a tag-usage explorer that shows where tags are influencing alerts, attribution, guardrails, or analytics.
9. `Optional future enhancement` Add change previews for security and data-capture updates so operators can see downstream impact before saving.

---

## Bundle D - Evidence, Audit, and Compliance Closure

### Product goal

Make governance evidence feel downstream, trustworthy, and easy to export so
operators can prove compliance and reconstruct what happened without confusing
audit surfaces with control planes.

### Scope

- Audit log
- Governance pack

### Derivation from the audit

This bundle is derived from:

- the feature rows showing both surfaces are complete for their actual product
  class
- the merge/collapse notes that group them together as evidence and compliance
  surfaces rather than separate governance primitives
- delivery crosswalk row `7.9`
- the `11.6` matrix, which shows both are strong downstream evidence layers but
  could gain better upstream linking from policy, security, and operations
  surfaces

### Current state summary

- audit log is complete as an investigative read and export surface
- governance pack is complete as an evidence and export surface
- support coverage is aligned
- remaining gap is upstream cohesion: more features should link into these
  evidence destinations intentionally

### Bundle-level route ownership

- canonical routes:
  - `/audit`
  - `/governance-pack`
- neighboring owners:
  - `/settings` for platform-level compliance posture
  - upstream governance control planes for source behavior

### Operator workflow

1. review a governance or runtime event
2. inspect detailed evidence in Audit Log
3. export or assemble broader compliance evidence through Governance Pack
4. route findings back into policy, security, or operating improvements

### Matrix-derived gap inventory

#### Internal feature gaps

- both surfaces are complete, but should feel more tightly related in-page
- evidence summaries can become more operator-friendly

#### Upstream-linkage gaps

- upstream pages should link into audit evidence more explicitly
- governance pack should more clearly show which upstream sources it consumes

#### Scope and compliance gaps

- clearer scope filtering and evidence lineage would help
- stronger ties to platform settings and ledger-style compliance closure remain
  useful

### Architecture and ownership notes

This bundle owns:

- evidence review
- governance export
- compliance-oriented downstream packaging

This bundle does not own:

- policy authoring
- approvals and alert actions
- platform compliance configuration

### Cross-feature integration requirements

- `Tool registry` and `Tool policies` for policy-source evidence
- `Approvals` and `Alert rules` for action evidence
- `Data capture`, `Security`, and `Tags` for posture evidence
- `Observe` for runtime and incident evidence
- `Platform settings` and `Ledger` for broader compliance closure

### Implementation phases

#### Phase D1 - Preserve evidence ownership

- keep audit and governance-pack ownership downstream
- prevent control-plane drift into these pages

#### Phase D2 - Improve evidence linkage

- make upstream pivots into audit and governance pack more explicit
- improve evidence lineage and source visibility

#### Phase D3 - Strengthen compliance closure

- improve integration with platform-admin compliance and export workflows

### Bundle polish opportunities

- better evidence timelines
- richer export summaries
- stronger cross-linking to originating policy or event sources

### Product enhancement ideas and suggestions

10. `Recommended next` Add an evidence lineage view that shows which policy, approval, alert, or runtime event produced each audit or governance artifact.
11. `Recommended next` Add scoped export presets for common audit packages such as security review, tool-governance review, or privacy posture review.
12. `Optional future enhancement` Add a compliance narrative generator that summarizes the key events, controls, and evidence for a selected period.

---

## Bundle A Technical Spec

### Technical goals

1. preserve Tool Registry and Tool Policies as canonical tool-governance owners
2. keep collapsed routes as compatibility-only
3. deepen runtime and scope-aware cohesion without reopening completed CRUD work

### Current implementation anchor points

- `apps/web/app/(dashboard)/tool-registry`
- `apps/web/app/(dashboard)/tool-policies`
- compatibility route handlers for `/search-tools` and `/policy-dry-run`
- MCP-adjacent ownership in `apps/web/app/(dashboard)/mcp-registry`
- backend governance routers and helpers under `apps/api/runledger_api/routers`

### Target architecture

- one registry control plane
- one policy control plane
- dry-run/testing embedded in the policy surface
- runtime-governance linkage visible but not duplicative

### Data model expectations

- preserve managed entities for registry entries and policies
- preserve deactivation and status lifecycle
- enrich with clearer scope metadata where needed

### Schema expectations

- no duplicate dry-run or search-provider schema families
- optional expansion for richer policy impact summaries

### API contract changes

- maintain full CRUD for registry and policy entities
- maintain dry-run/test endpoints
- optionally add summary endpoints for scope impact and runtime linkage

### UI requirements

- registry list/detail/edit/deactivate flows
- policy list/detail/edit/deactivate flows
- embedded dry-run/test tabs
- clear compatibility redirects from collapsed routes

### Cross-feature integration requirements

- Gateway runtime linkage
- Organization and Access scope metadata
- Observe pivots for evidence and investigation

### Delivery-surface requirements

- docs/Postman/scripts/examples must continue to describe Tool Registry and Tool
  Policies as the primary owners
- collapsed routes must be documented as compatibility-only

### Implementation phases

1. preserve ownership
2. deepen runtime cohesion
3. deepen scope-aware policy context

### Acceptance criteria

- no duplicate tool-governance control planes reappear
- registry and policy surfaces stay complete
- dry-run/testing remains embedded and coherent
- runtime traceability improves without moving ownership

### Product enhancement suggestions

- policy impact summaries
- richer dry-run diffs
- inheritance viewer

## Bundle B Technical Spec

### Technical goals

1. keep approvals and alert rules as the active governance action layer
2. improve exception-path cohesion with budgets, model access, and runtime
3. preserve end-to-end create/update/delete behavior already implemented

### Current implementation anchor points

- `apps/web/app/(dashboard)/approvals`
- `apps/web/app/(dashboard)/alert-rules`
- related backend routers for approval policies, approval requests, and alert
  rules

### Target architecture

- approvals as the human exception path
- alerts as the automated response path
- both tied into runtime, monitoring, and evidence flows

### Data model expectations

- preserve approval policy and approval request entities
- preserve alert rule lifecycle
- enrich with scope and linked-source context where useful

### Schema expectations

- keep full managed-entity request/response contracts
- optionally expand linked-context payloads for related run, budget, or policy
  evidence

### API contract changes

- maintain full CRUD/update flows
- optionally add richer linked-context endpoints

### UI requirements

- queue and status views
- edit-in-place for alert and approval policies
- linked investigation and exception context

### Cross-feature integration requirements

- FinOps for budget overrides
- Org and Access for model and scope-sensitive approvals
- Observe for monitoring-driven drilldowns
- Gateway for runtime-governance conditions

### Delivery-surface requirements

- docs/Postman/scripts/examples should describe approvals and alerts as one
  actionable governance layer, not isolated utilities

### Implementation phases

1. preserve completed lifecycle depth
2. strengthen exception cohesion
3. grow suite-wide adoption

### Acceptance criteria

- approvals and alerts stay fully manageable
- cross-feature exception paths improve materially
- operators can move from alert or approval into the right adjacent context

### Product enhancement suggestions

- unified governance action inbox
- alert-to-investigation pivots
- approval templates

## Bundle C Technical Spec

### Technical goals

1. preserve Data Capture, Security, and Tags as scoped-policy source-of-truth
   surfaces
2. improve shared scope and taxonomy usage across the suite
3. strengthen downstream evidence and runtime usage

### Current implementation anchor points

- `apps/web/app/(dashboard)/data-capture`
- `apps/web/app/(dashboard)/security`
- `apps/web/app/(dashboard)/tags`
- related backend routers for capture overrides, OIDC/IP ACL/security posture,
  tags, and auto-tagging rules

### Target architecture

- data-capture posture owner
- security posture owner
- taxonomy and classification owner
- shared scope model threaded through all three

### Data model expectations

- preserve scoped override entities
- preserve security managed entities and policy objects
- preserve tag taxonomy and auto-rule entities
- optionally add stronger usage metadata and downstream linkage summaries

### Schema expectations

- keep full lifecycle contracts intact
- optionally add shared scope posture and usage-summary objects

### API contract changes

- maintain current CRUD and simulation contracts
- optionally add summary or usage endpoints for posture and tag propagation

### UI requirements

- edit-in-place for scoped policies
- better posture summary cards
- clearer hierarchy and inheritance visualization
- better visibility into downstream tag and policy usage

### Cross-feature integration requirements

- Organization and Access for scope model
- Gateway for runtime policy influence
- Observe for monitoring and evidence
- FinOps for attribution using tags

### Delivery-surface requirements

- docs/Postman/scripts/examples should show these features as part of one scoped
  governance posture story, not three unrelated tools

### Implementation phases

1. preserve scoped-policy ownership
2. deepen shared scope posture
3. strengthen downstream usage

### Acceptance criteria

- Data Capture, Security, and Tags remain complete
- shared scope identity is clearer across all three surfaces
- downstream evidence and attribution usage is easier to understand

### Product enhancement suggestions

- scope posture map
- tag-usage explorer
- change previews

## Bundle D Technical Spec

### Technical goals

1. preserve Audit Log and Governance Pack as downstream evidence owners
2. improve upstream pivots and evidence lineage
3. strengthen compliance closure with platform-level surfaces

### Current implementation anchor points

- `apps/web/app/(dashboard)/audit`
- `apps/web/app/(dashboard)/governance-pack`
- related backend routers for audit events, exports, and governance evidence

### Target architecture

- Audit Log as detailed evidence review
- Governance Pack as packaged compliance export
- strong but downstream linkage to the rest of the governance suite

### Data model expectations

- preserve event, evidence, and export objects
- optionally add lineage metadata and richer scope association

### Schema expectations

- maintain read/filter/export contracts
- optionally expand with evidence lineage and linked-source summaries

### API contract changes

- maintain existing read/filter/export endpoints
- optionally add lineage or source-summary APIs

### UI requirements

- strong filtering and export
- clearer evidence origin links
- governance-pack summaries that show upstream source coverage

### Cross-feature integration requirements

- upstream links from policy, approval, alert, security, and request-analysis
  surfaces
- downstream links into platform compliance workflows

### Delivery-surface requirements

- docs/Postman/scripts/examples must show audit and governance pack as evidence
  surfaces, not control-plane substitutes

### Implementation phases

1. preserve evidence ownership
2. improve evidence linkage
3. strengthen compliance closure

### Acceptance criteria

- Audit Log and Governance Pack remain complete
- evidence lineage and pivots improve
- compliance packaging feels more intentional and downstream

### Product enhancement suggestions

- evidence lineage view
- export presets
- compliance narrative generator

---

## Major-Feature Product Enhancement Ideas

These are high-level product suggestions for `Safety & Governance` beyond the
required implementation bar.

1. `Recommended next` Add a suite-wide governance posture overview that summarizes policy, security, data-capture, approval, and evidence health by scope.
2. `Recommended next` Add stronger scope-resolution explainers so operators can understand why a policy or security rule applied to a request.
3. `Recommended next` Add a runtime governance correlation panel that links policy decisions, alerts, approvals, and request evidence together.
4. `Recommended next` Add richer simulation coverage beyond tool policies, including approval-routing, security posture, and tag-rule previews.
5. `Recommended next` Add a governance change feed showing the most recent policy, security, and taxonomy updates with downstream impact hints.
6. `Optional future enhancement` Add saved review packs for weekly governance review, privacy review, and security posture review.
7. `Optional future enhancement` Add operator guidance cards that recommend next steps after a policy violation, audit finding, or alert breach.
8. `Optional future enhancement` Add richer drilldowns from governance pages into specific runs, sessions, and telemetry spikes.
9. `Optional future enhancement` Add scope-aware approval escalation paths and SLA tracking for pending high-risk requests.
10. `Optional future enhancement` Add governance scorecards that summarize posture maturity by workspace or org.
11. `Optional future enhancement` Add tag-driven policy and evidence grouping so operators can review governance by shared taxonomy themes.
12. `Optional future enhancement` Add exportable governance review snapshots for executive, audit, and engineering audiences.

## Bundle Acceptance Summary

`Safety & Governance` is complete as a major-feature family when:

- Tool Registry and Tool Policies remain the canonical governance control planes
- collapsed routes such as `/mcp`, `/search-tools`, and `/policy-dry-run`
  remain compatibility-only
- approvals and alert rules work as a cohesive governance action layer
- Data Capture, Security, and Tags form a clear scoped-policy posture layer
- Audit Log and Governance Pack remain downstream evidence and compliance owners
- cross-feature ties to Gateway, Organization and Access, Observe, and FinOps
  are stronger than they are today
- docs, Postman, scripts, and examples reflect the real user workflow through
  the Safety and Governance family
