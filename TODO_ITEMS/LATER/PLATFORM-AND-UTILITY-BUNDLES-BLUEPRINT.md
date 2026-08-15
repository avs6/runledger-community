# RunLedger Platform and Utility Bundles Blueprint

Last updated: Friday, August 14, 2026

## Purpose

This file is the working blueprint for the combined `Platform` and `Additional
Admin / Utility Routes` major feature family in RunLedger.

It is derived from:

- [FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
- [DELIVERY-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/DELIVERY-AUDIT.md)

This blueprint converts the platform-admin audit, Feature Gap Matrix, delivery
crosswalk, and cohesion matrix into implementation bundles, technical specs,
and product-improvement ideas.

## Platform and Utility Vision

Platform and Utility should feel like one coherent platform-admin layer.

It should let platform operators:

- create, update, suspend, and reactivate organizations cleanly
- define platform-wide defaults and compliance posture in one clear home
- avoid spawning duplicate or ghost admin routes
- route discovery-only utility surfaces into the right user workflow instead of
  preserving them as separate product areas

The target outcome is:

`Platform / Utility = platform lifecycle + platform defaults + intentional utility collapse`

not

`Platform / Utility = umbrella settings plus stray legacy admin pages`

## Audit-First Rule

This blueprint is derived from the audit, not the reverse.

The required input order for this file was:

1. `FEATURE-AUDIT.md`
2. the `Platform` and `Additional Admin / Utility Routes` rows and related
   Feature Gap Matrix entries
3. the `Delivery Audit Crosswalk`
4. the `11.8 Platform / Utility Cohesion Matrix`
5. bundle derivation, technical specs, and implementation sequencing

If the feature rows or the `11.8` cohesion matrix change materially, this
blueprint should be updated.

## Feature-Audit to Bundle Mapping

This blueprint maps section `7` and section `8` of
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
into one combined platform-admin blueprint.

| Bundle | Bundle Name | Feature-AUDIT rows mapped into the bundle | Mapping notes |
|--------|-------------|--------------------------------------------|---------------|
| `Bundle A` | `Platform Lifecycle Control Plane` | `All organizations` | This is the real platform-admin lifecycle owner for organization create/update/suspend/reactivate behavior. |
| `Bundle B` | `Platform Settings Convergence` | `Platform settings` | This is the convergence surface for platform-wide compliance, retention, backup, storage posture, feature flags, and ops defaults. |
| `Bundle C` | `Utility Route Collapse and Discovery Ownership` | `Plugins` | `Plugins` is intentionally collapsed into Onboarding and should stay a compatibility-only route unless a future first-class management plane is introduced deliberately. |
| `Bundle D` | `Platform Posture Summaries and Admin Workflow Cohesion` | `All organizations`, `Platform settings`, `Plugins` | This bundle is the cross-cutting cohesion layer that keeps the platform-admin experience consistent and prevents drift across lifecycle, settings, and collapsed utility entry points. |

Material delivery-crosswalk support for this family comes from:

- `1.2` Organizations and tenants
- `1.7` Platform settings
- `8.6` Plugins
- supporting adjacency from `7.7`, `9.3`, `9.4`, `9.5`, `9.11`, `9.12`,
  `9.13`, and `9.14`

## Bundle Overview

The Platform and Utility family should be implemented and maintained in this
order:

1. `Bundle A` Platform Lifecycle Control Plane
2. `Bundle B` Platform Settings Convergence
3. `Bundle C` Utility Route Collapse and Discovery Ownership
4. `Bundle D` Platform Posture Summaries and Admin Workflow Cohesion

That order follows the platform-admin workflow:

1. manage organizations
2. define platform-wide defaults and compliance posture
3. keep discovery and utility entry points in the correct ownership surface
4. improve the overall admin flow and platform posture visibility

## Bundle A - Platform Lifecycle Control Plane

### Product goal

Make `All organizations` the clear and complete platform-admin lifecycle hub for
tenant management.

### Scope

- All organizations

### Derivation from the audit

This bundle is derived from:

- the feature row showing `/organizations` is operationally real and already the
  correct owner for create/list/update/delete plus suspend/reactivate
- the gap note that completion is blocked mainly by support-surface unevenness,
  not by missing core UI/API behavior
- delivery crosswalk rows `1.2` and `1.7`
- the `11.8` matrix, which shows All Organizations should remain the parent
  lifecycle owner and summarize downstream posture without absorbing other
  control planes

### Current state summary

- backend: real lifecycle coverage exists
- UI: real platform-admin lifecycle flows exist
- actions: create, update, delete, suspend, and reactivate are present
- docs/Postman/scripts/examples: support coverage is still uneven
- remaining gap: completion is mostly about delivery completeness and stronger
  platform-admin cohesion

### Bundle-level route ownership

- canonical route:
  - `/organizations`
- neighboring owner:
  - `/organization` remains the org-admin console after an org exists

### Operator or user workflow

1. platform admin creates an organization
2. platform admin updates lifecycle state or posture as needed
3. org operators continue setup in org-owned surfaces

### Matrix-derived gap inventory

#### Internal feature gaps

- support coverage outside the core UI/API needs to be tightened

#### Scope and ownership gaps

- downstream posture summaries can improve
- the route should remain the lifecycle parent, not a giant settings surface

#### Cross-feature gaps

- better summaries into budgets, ledger/compliance, and platform posture would
  help without moving ownership

### Architecture and ownership notes

This bundle owns:

- platform-level organization lifecycle

This bundle does not own:

- org-admin console behavior
- platform compliance defaults
- utility discovery routes

### Cross-feature integration requirements

- `Organization & Access` for handoff into org lifecycle
- `FinOps` for future organization-level billing or chargeback summaries
- `Platform settings` for default posture summaries
- `Observe` and `Governance` only as summary consumers, not direct owners

### Implementation phases

#### Phase A1 - Preserve lifecycle ownership

- keep `/organizations` as the canonical platform lifecycle home

#### Phase A2 - Tighten delivery completeness

- improve docs, scripts/examples, and broader support coverage

#### Phase A3 - Improve downstream posture summaries

- show platform-admin useful signals without absorbing downstream control planes

### Bundle polish opportunities

- stronger org-state badges
- better empty states for first platform bootstrap
- richer org posture summary cards

### Product enhancement ideas and suggestions

1. `Recommended next` Add organization posture summary cards showing onboarding state, security posture, telemetry status, and recent platform-admin actions.
2. `Recommended next` Add bulk lifecycle actions and filtered org-state views for larger multi-tenant operators.
3. `Optional future enhancement` Add org provisioning templates that pre-apply platform-default bundles during creation.

---

## Bundle B - Platform Settings Convergence

### Product goal

Turn `Platform settings` into a truly coherent platform-defaults and compliance
console rather than an umbrella route with uneven ownership.

### Scope

- Platform settings

### Derivation from the audit

This bundle is derived from:

- the feature row marking `/settings` as partial across backend, UI, actions,
  Postman, and scripts/examples
- the merge/collapse note that it should become the single home for Ledger,
  Retention, Backup, and ops/compliance surfaces
- delivery crosswalk row `1.7` plus adjacency from `7.7`, `9.3`, `9.4`, `9.5`,
  `9.11`, `9.12`, `9.13`, and `9.14`
- the `11.8` matrix, which shows Platform Settings is strategically important
  and already the clearest home for cross-cutting compliance and operational
  defaults, but still reads as an umbrella rather than one cohesive product area

### Current state summary

- some subareas are strong on their own
- the route as a whole does not yet behave like one finished platform feature
- docs exist, but broader API and support coverage is uneven
- ownership needs to become clearer so adjacent surfaces like Ledger remain
  absorbed correctly

### Bundle-level route ownership

- canonical route:
  - `/settings`
- absorbed or neighboring subareas:
  - retention
  - backup and restore posture
  - feature flags
  - storage posture and infra policy
  - local TLS and demo proxy
  - deployment profiles
  - compliance/ledger-adjacent surfaces

### Operator or user workflow

1. platform admin enters Platform Settings
2. configures platform-wide defaults and compliance posture
3. reviews operational settings across backup, deployment, infra, and policy
4. relies on adjacent admin surfaces only when they are intentionally separate

### Matrix-derived gap inventory

#### Internal feature gaps

- the route is still an umbrella instead of one cohesive managed area
- not all tabs or subareas present a consistent operator model

#### Scope and ownership gaps

- platform-wide defaults need clearer boundaries from org-level settings
- compliance and operations posture need clearer in-page ownership

#### Delivery gaps

- Postman and scripts/examples are still partial
- platform-wide docs can be more unified

### Architecture and ownership notes

This bundle owns:

- platform defaults
- platform compliance posture
- infra and operational setting convergence

This bundle does not own:

- organization lifecycle
- onboarding/discovery utility flows

### Cross-feature integration requirements

- `Ledger` and compliance evidence
- `Observe` Monitoring for platform operational posture summaries
- `Governance pack` for downstream compliance linkage
- `Organization & Access` for boundary clarity between platform and org settings

### Implementation phases

#### Phase B1 - Clarify settings ownership

- define the tabs and absorbed surfaces explicitly
- prevent drift into scattered admin routes

#### Phase B2 - Normalize operator experience

- make subareas feel consistent in UI, actions, and data model expectations

#### Phase B3 - Finish delivery completeness

- align Postman, scripts/examples, and broader docs with the converged platform
  settings story

### Bundle polish opportunities

- better tab taxonomy
- stronger platform-default summaries
- clearer compliance and infra posture dashboards

### Product enhancement ideas and suggestions

4. `Recommended next` Add a platform posture overview inside Settings that summarizes retention, backup health, storage policy, deployment profile, and compliance state in one view.
5. `Recommended next` Add change-history and impact hints for high-risk platform settings so operators understand downstream effects before saving.
6. `Optional future enhancement` Add settings bundles or preset profiles for small self-hosted, enterprise, and regulated deployments.

---

## Bundle C - Utility Route Collapse and Discovery Ownership

### Product goal

Keep utility surfaces intentionally collapsed so discovery-only flows live in
the right product area instead of reappearing as ghost admin pages.

### Scope

- Plugins

### Derivation from the audit

This bundle is derived from:

- the feature row showing `/plugins` is now a legacy UI route with backend
  capability still present behind it
- the collapse note that Plugins belongs in `Onboarding`
- delivery crosswalk row `8.6`
- the `11.8` matrix, which shows Plugins is now correctly collapsed under
  onboarding/discovery and should not live in a separate ops island

### Current state summary

- backend plugin CRUD and execution-log support still exists
- `/plugins` is a compatibility redirect only
- current gap is not CRUD completion; it is ownership discipline and support
  cleanup

### Bundle-level route ownership

- compatibility route:
  - `/plugins`
- intended user-facing owner:
  - `/onboarding`

### Operator or user workflow

1. user or operator wants to discover or connect tools/plugins
2. enters through onboarding/setup guidance
3. does not need to reason about a separate utility route

### Matrix-derived gap inventory

#### Internal feature gaps

- avoid preserving redirect-only routes as if they were still active products

#### Ownership gaps

- onboarding should remain the discovery owner
- any future dedicated plugin management surface should be introduced
  intentionally, not by drift

#### Delivery gaps

- docs and examples can better reflect the collapsed ownership

### Architecture and ownership notes

This bundle owns:

- the collapse rule and compatibility posture for Plugins

This bundle does not own:

- a first-class plugin-management surface
- platform settings
- onboarding implementation itself

### Cross-feature integration requirements

- `Onboarding` as the user-facing discovery home
- `Build & Improve` only if plugins later become part of builder workflows
- `Tool governance` if plugin execution policies deepen further

### Implementation phases

#### Phase C1 - Preserve collapse discipline

- keep `/plugins` as compatibility-only

#### Phase C2 - Tighten support coverage

- make docs and examples reflect onboarding ownership more clearly

#### Phase C3 - Guard against route drift

- do not re-expand the utility page unless product direction explicitly changes

### Bundle polish opportunities

- clearer compatibility messaging
- better onboarding handoff copy
- stronger removal of stale utility references

### Product enhancement ideas and suggestions

7. `Recommended next` Add a clearer onboarding card and setup guide for plugin and external-tool discovery so users never need to think about `/plugins`.
8. `Recommended next` Add compatibility messaging or redirect-state hints that explain where plugin discovery now lives.
9. `Optional future enhancement` If a real plugin-management plane is ever reintroduced, define it explicitly around governance, logs, and lifecycle rather than reviving the old route shape.

---

## Bundle D - Platform Posture Summaries and Admin Workflow Cohesion

### Product goal

Make the platform-admin experience feel cohesive across lifecycle, settings, and
collapsed utility entry points without creating duplicate control planes.

### Scope

- All organizations
- Platform settings
- Plugins

### Derivation from the audit

This bundle is derived from:

- the combined platform and utility rows
- the platform notes emphasizing lifecycle ownership, settings convergence, and
  utility collapse
- the `11.8` matrix, which repeatedly points to the need for summary-level
  cohesion rather than more top-level feature sprawl

### Current state summary

- the core owners are identifiable
- the admin workflow still feels fragmented in support coverage and surface
  consistency
- collapsed utility routes need continued discipline

### Bundle-level route ownership

- platform lifecycle: `/organizations`
- platform defaults and compliance: `/settings`
- collapsed discovery utility: `/plugins` -> `/onboarding`

### Operator or user workflow

1. platform admin manages org lifecycle
2. configures platform defaults
3. reviews platform posture
4. relies on onboarding for discovery-only utility experiences

### Matrix-derived gap inventory

#### Internal cohesion gaps

- platform surfaces need stronger shared summaries and consistent admin flow

#### Cross-feature gaps

- platform lifecycle and settings should summarize, not absorb, downstream
  Gateway, Observe, and Governance posture

#### Utility cleanup gaps

- avoid stale references to collapsed utility routes

### Architecture and ownership notes

This bundle owns:

- platform-admin workflow cohesion
- posture summary design
- collapse discipline across admin utilities

This bundle does not own:

- deep downstream control planes

### Cross-feature integration requirements

- `Organization & Access`
- `Observe`
- `Safety & Governance`
- `FinOps`
- `Onboarding`

### Implementation phases

#### Phase D1 - Strengthen shared platform-admin flow

- improve navigation and handoff between `/organizations` and `/settings`

#### Phase D2 - Add posture summaries

- show useful downstream signals without changing ownership boundaries

#### Phase D3 - Finish cleanup discipline

- scrub stale utility/admin references and keep route ownership explicit

### Bundle polish opportunities

- better platform-admin dashboards
- clearer top-level navigation language
- stronger first-boot guidance

### Product enhancement ideas and suggestions

10. `Recommended next` Add a lightweight platform admin home that summarizes org lifecycle, platform settings posture, and high-priority operational issues without competing with existing owners.
11. `Recommended next` Add stronger cross-feature posture rollups from security, monitoring, telemetry, and compliance into platform-admin summary cards.
12. `Optional future enhancement` Add platform bootstrap checklists that guide operators through first setup, org provisioning, compliance defaults, and observability readiness.

---

## Bundle A Technical Spec

### Technical goals

1. preserve `/organizations` as the platform lifecycle owner
2. finish delivery completeness around the existing strong UI/API
3. improve posture summaries without absorbing neighboring control planes

### Current implementation anchor points

- `apps/web/app/(dashboard)/organizations`
- backend organization lifecycle routers
- related docs, Postman, and bootstrap scripts

### Target architecture

- one lifecycle control plane for organizations
- clear handoff into org-admin surfaces after creation

### Data model expectations

- preserve org lifecycle entities and status transitions
- optionally enrich summary fields for platform-admin posture

### Schema expectations

- maintain lifecycle CRUD/suspend/reactivate contracts
- optionally add summary aggregates only if needed for platform-admin views

### API contract changes

- mostly delivery and support alignment
- no need for major new lifecycle APIs unless gaps are found during deeper build

### UI requirements

- strong list/detail lifecycle behavior
- clear org-state filters and actions
- helpful downstream posture summaries

### Cross-feature integration requirements

- org console handoff
- platform settings summaries
- optional billing/compliance summary linkage

### Delivery-surface requirements

- docs/Postman/scripts/examples should treat `/organizations` as the canonical
  platform lifecycle entry point

### Implementation phases

1. preserve lifecycle ownership
2. tighten delivery completeness
3. improve downstream posture summaries

### Acceptance criteria

- org lifecycle flows remain complete
- support coverage is no longer uneven
- handoff to org-admin surfaces is clearer

### Product enhancement suggestions

- org posture cards
- bulk org lifecycle tools
- provisioning templates

## Bundle B Technical Spec

### Technical goals

1. make `/settings` a coherent platform-defaults surface
2. keep absorbed compliance and ops surfaces under one owner
3. normalize UX and support coverage across settings subareas

### Current implementation anchor points

- `apps/web/app/(dashboard)/settings`
- platform settings tabs and backend routers for retention, backups, feature
  flags, storage posture, deployment profiles, and related ops/compliance areas

### Target architecture

- one platform settings shell
- explicit tab ownership
- absorbed platform defaults and compliance surfaces

### Data model expectations

- preserve underlying subdomain entities
- add shared summary or change metadata where useful for consistency

### Schema expectations

- keep existing subdomain contracts
- optionally add shared settings-shell summary objects

### API contract changes

- focus on normalization and completeness, not unnecessary new entities

### UI requirements

- consistent tab model
- consistent edit/save/validation patterns
- better platform posture summaries

### Cross-feature integration requirements

- governance/compliance evidence
- monitoring and operational posture
- org boundary clarity

### Delivery-surface requirements

- docs/Postman/scripts/examples should describe Platform Settings as the single
  home for the absorbed platform-default and compliance surfaces

### Implementation phases

1. clarify settings ownership
2. normalize operator experience
3. finish delivery completeness

### Acceptance criteria

- `/settings` feels like one coherent product area
- absorbed surfaces stay absorbed
- support coverage improves materially

### Product enhancement suggestions

- posture overview
- change impact hints
- settings bundles

## Bundle C Technical Spec

### Technical goals

1. keep utility route collapse intentional
2. reflect onboarding as the discovery owner
3. prevent legacy redirect surfaces from drifting back into active product areas

### Current implementation anchor points

- compatibility route for `/plugins`
- onboarding ownership for discovery and setup
- backend plugin-management capabilities retained behind the scenes

### Target architecture

- redirect-only compatibility route
- onboarding-owned user discovery flow
- optional future explicit plugin-management plane only if intentionally designed

### Data model expectations

- no new top-level utility entity family needed here

### Schema expectations

- compatibility-only route behavior
- current plugin-management APIs remain available without implying a top-level
  page owner

### API contract changes

- no major API changes required for the blueprint itself

### UI requirements

- clear redirect behavior
- stronger onboarding guidance
- no ghost utility pages

### Cross-feature integration requirements

- onboarding
- tool governance, if plugin policy depth increases later

### Delivery-surface requirements

- docs/examples should not talk about `/plugins` as an active first-class admin
  destination

### Implementation phases

1. preserve collapse discipline
2. tighten support coverage
3. guard against route drift

### Acceptance criteria

- `/plugins` remains collapsed
- onboarding ownership is explicit
- stale references are reduced

### Product enhancement suggestions

- better onboarding card
- redirect-state hints
- intentional future management-plane design if needed

## Bundle D Technical Spec

### Technical goals

1. improve overall platform-admin workflow cohesion
2. add summary-level posture views without changing ownership boundaries
3. keep collapsed utility routes disciplined

### Current implementation anchor points

- `/organizations`
- `/settings`
- `/plugins` compatibility route
- top-level navigation and admin entry points

### Target architecture

- coherent platform-admin journey
- clear separation between lifecycle, settings, and discovery
- posture summaries layered above, not across, downstream control planes

### Data model expectations

- mostly summary and integration metadata rather than new entities

### Schema expectations

- optional shared summary payloads for platform-admin overview or top-level
  posture cards

### API contract changes

- add summary endpoints only if they materially improve the admin workflow

### UI requirements

- better navigation and handoffs
- stronger summary rollups
- clearer admin language and first-boot guidance

### Cross-feature integration requirements

- summaries from FinOps, Observe, Governance, and org-admin surfaces
- strong ownership boundaries preserved

### Delivery-surface requirements

- docs, scripts, and examples should present Platform / Utility as one coherent
  admin story, not as disconnected leftovers

### Implementation phases

1. strengthen shared platform-admin flow
2. add posture summaries
3. finish cleanup discipline

### Acceptance criteria

- platform-admin navigation is clearer
- summary posture is more useful
- collapsed utility cleanup remains intentional

### Product enhancement suggestions

- lightweight admin home
- stronger cross-feature posture rollups
- bootstrap checklists

---

## Major-Feature Product Enhancement Ideas

These are high-level product suggestions for `Platform / Utility` beyond the
required implementation bar.

1. `Recommended next` Add a compact platform-admin overview page that summarizes org lifecycle, platform posture, compliance state, and operational issues.
2. `Recommended next` Add stronger first-run guidance for platform operators setting up the product for the first time.
3. `Recommended next` Add platform posture scorecards covering backup readiness, retention posture, storage policy, telemetry readiness, and security defaults.
4. `Recommended next` Add org provisioning flows that attach recommended defaults automatically at creation time.
5. `Recommended next` Add clearer summary relationships between platform settings and org-level settings so admins understand what is inherited versus overridden.
6. `Optional future enhancement` Add platform-admin audit summaries showing the highest-risk recent changes across org lifecycle and settings updates.
7. `Optional future enhancement` Add environment profiles that let operators compare or sync defaults across dev, homelab, and production deployments.
8. `Optional future enhancement` Add guided recovery and maintenance checklists for backup, restore, and deployment-profile review.
9. `Optional future enhancement` Add admin-specific saved views or bookmarks for large multi-tenant operations.
10. `Optional future enhancement` Add a richer platform notifications center for critical backup, compliance, and lifecycle events.
11. `Optional future enhancement` Add stronger in-product help for platform-only concepts such as retention, deployment profiles, and infra policy.
12. `Optional future enhancement` Add a platform bootstrap simulator that validates whether the stack is ready for first customer or first org activation.

## Bundle Acceptance Summary

`Platform / Utility` is complete as a major-feature family when:

- `/organizations` remains the canonical platform lifecycle owner
- `/settings` acts as the single converged home for platform defaults and
  absorbed compliance/ops surfaces
- `/plugins` remains intentionally collapsed into onboarding rather than
  re-emerging as a ghost admin route
- platform-admin workflow cohesion is stronger across lifecycle, settings, and
  discovery entry points
- docs, Postman, scripts, and examples reflect the real platform-admin story
  instead of historical route sprawl
