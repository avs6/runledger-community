# RunLedger FinOps Bundles Blueprint

Last updated: Friday, August 14, 2026

## Purpose

This file is the working blueprint for the FinOps feature family in RunLedger.

It is not only a page audit. It is a product-architecture and implementation guide
for how the FinOps surface should evolve so it becomes one of the strongest,
most cohesive feature sets in the suite.

This blueprint is organized around four bundles:

1. `Bundle A` - Spend Control Plane
2. `Bundle B` - Billing and Reconciliation
3. `Bundle C` - Attribution and Allocation
4. `Bundle D` - Compliance Closure

These bundles are ordered intentionally by user workflow and runtime dependency:

1. define spend policy
2. operate accounting periods
3. allocate costs
4. close and verify compliance artifacts

Important framing:

- the `Feature Cohesion Matrix` in
  [FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
  is the driver
- the FinOps bundles in this file are derived from the matrix findings, gaps, and
  cross-feature dependency patterns
- the bundles are execution groupings for implementation, not the thing that
  defines what the audit should say

### Feature-Audit to Bundle Mapping

The bundle boundaries in this file are mapped directly from the FinOps rows in
section `5` of
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md).

| Bundle | Bundle Name | Feature-AUDIT rows mapped into the bundle | Mapping notes |
|--------|-------------|--------------------------------------------|---------------|
| `Bundle A` | `Spend Control Plane` | `Budgets`, `Budget detail`, `Budget overrides` | `Budget tiers` and `Model budgets` support Bundle A indirectly, but remain intentionally collapsed under Gateway and API-key quota controls rather than being reopened as standalone FinOps surfaces. |
| `Bundle B` | `Billing and Reconciliation` | `Billing periods`, `Billing period detail` | This is the accounting-period and reconciliation layer that consumes Bundle A outcomes and feeds Bundle C and D. |
| `Bundle C` | `Attribution and Allocation` | `Chargeback` | This is the allocation and ownership layer and should align to workspaces, access groups, workflows, feature tags, API keys, and provider profiles rather than legacy team/project dimensions. |
| `Bundle D` | `Compliance Closure` | `Ledger` | This is the evidence and verification layer. It stays FinOps-linked, but the matrix and audit both indicate it belongs conceptually under Platform Settings / Compliance. |

The cohesion matrices in section `11` of
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
then determine how those mapped feature rows should be grouped, sequenced, and
implemented:

- `11.2 FinOps Cohesion Matrix` drives the internal FinOps grouping
- `11.3+` cross-feature matrices explain the dependencies between FinOps and the rest of the suite
- the bundles in this file are therefore the implementation groupings derived from those audited relationships

---

## FinOps Vision

FinOps in RunLedger should not feel like a few disconnected spend pages.

It should feel like a single operating system for AI cost control:

- define financial guardrails before traffic runs
- enforce spend policy on the runtime path
- grant time-boxed exceptions through governed workflows
- understand spend by workspace, key, access group, workflow, provider, and model
- close billing periods cleanly
- allocate cost to the right owners
- verify evidence and ledger integrity for compliance

The crown-jewel outcome is:

`FinOps = enforcement + visibility + exception handling + allocation + closeout`

not

`FinOps = tables of costs and a few create forms`

---

## Cross-Feature Cohesion Rules

### Matrix-first rule

FinOps implementation should flow in this order:

1. audit the shipped feature surfaces in `FEATURE-AUDIT.md`
2. populate the `Feature Cohesion Matrix`
3. identify the strongest and weakest cross-feature relationships
4. derive implementation bundles from those relationships
5. write the bundle plan and technical spec

That means:

- matrix findings and gaps drive the bundle boundaries
- bundle phases are remediation tracks for matrix failures
- if the matrix changes materially, the bundles should be updated to match

All four FinOps bundles must stay aligned to the real product primitives.

### Primary control primitives

- `organization`
- `workspace`
- `access_group`
- `api_key`
- `workflow`
- `feature_tag`
- `provider_profile`
- `model`
- `end_user`

### Must not deepen legacy concepts

Do not introduce or expand:

- `team`
- `project`
- `team_model`

If legacy budget or cost paths still reference those concepts, they should be
cleaned up or re-homed into workflow-centered or access-centered primitives.

### FinOps ownership split

- `Gateway` owns technical request-path quotas and route-level model controls
- `FinOps` owns spend-governance policy and exception management
- `Approvals` owns human sign-off workflows for risky exceptions
- `Chargeback` owns downstream allocation of finalized cost
- `Billing` owns period management and reconciliation
- `Platform Compliance` owns ledger verification and evidence closure

### Runtime expectation

FinOps features must not be decorative.

If a limit exists in the UI, it should either:

- affect live runtime enforcement
- affect closeout or accounting behavior
- affect approval and evidence workflow

If it does none of the above, it should not be a first-class FinOps control.

---

## Bundle Overview

These bundles are not independent feature theories.

They are the implementation groupings derived from the current FinOps cohesion
audit:

- `Bundle A` is derived from the strongest and weakest policy-plane relationships
  around `Budgets`, `Budget detail`, `Budget overrides`, and `Budget notifications`
- `Bundle B` is derived from the billing and reconciliation relationships already
  visible in Observe and downstream finance operations
- `Bundle C` is derived from the allocation and ownership relationships visible
  across `Chargeback`, workflows, access groups, and optimization surfaces
- `Bundle D` is derived from the evidence and closure relationships centered on
  `Ledger`, `Governance pack`, `Audit log`, and platform compliance surfaces

### Bundle A - Spend Control Plane

Scope:

- `Budgets`
- `Budget detail`
- `Budget overrides`

Role:

- the primary spend-governance layer
- defines what spend is allowed
- determines what happens when spend limits are hit
- manages temporary exceptions
- bridges runtime enforcement to admin operations

This is the foundational bundle and should be implemented first.

### Bundle B - Billing and Reconciliation

Scope:

- `Billing periods`
- `Billing period detail`

Role:

- accounting and period operations
- close/export/adjustment flows
- shared-cost treatment
- reconciliation of metering into billable periods

This bundle depends on Bundle A being clean, because spending policy and exception
states should feed into billing interpretation and operator workflows.

### Bundle C - Attribution and Allocation

Scope:

- `Chargeback`

Role:

- assign cost to the right owners
- allocate spend across workspaces, access groups, workflows, and feature tags
- turn raw spend into accountable ownership views

This bundle should align to access and workflow primitives, not legacy team/project
dimensions.

### Bundle D - Compliance Closure

Scope:

- `Ledger`

Role:

- compliance verification
- immutable or verifiable snapshots
- end-of-period integrity checks
- evidence support for audit and reporting

This should ultimately live more naturally under Platform Settings or Compliance,
not as a first-class standalone FinOps page.

---

## Bundle A - Spend Control Plane

### Bundle A product goal

Bundle A should become the central operating surface for AI spend policy in RunLedger.

It should answer:

- What spend policies exist?
- What scopes do they govern?
- Which scopes have no protection?
- Which budgets are healthy, at risk, breached, or overridden?
- What will happen when each budget is exceeded?
- Who is allowed to create exceptions?
- Are notifications and escalation channels working?
- How does spend governance align with access control and gateway routing?

### Bundle A current state

#### Backend strengths already present

The backend already has meaningful runtime substance:

- Redis-backed spend tracking
- hot-path budget checks
- budget rollups
- breach recording
- override lifecycle
- notification channel and delivery support
- some billing summary/export support under the budgets router

Key current files:

- [apps/api/runledger_api/services/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/services/budgets.py)
- [apps/api/runledger_api/routers/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/routers/budgets.py)
- [apps/api/runledger_api/schemas/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/schemas/budgets.py)
- [apps/api/runledger_api/models/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/models/budgets.py)
- [apps/api/runledger_api/models/budget_overrides.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/models/budget_overrides.py)

#### UI weaknesses today

The UI is materially behind the runtime model:

- [apps/web/app/(dashboard)/budgets/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/budgets/page.tsx)
  is mostly a launcher plus a simple list
- [apps/web/app/(dashboard)/budgets/[id]/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/budgets/[id]/page.tsx)
  is only breach history, not a true detail page
- [apps/web/app/(dashboard)/budget-overrides/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/budget-overrides/page.tsx)
  is isolated from budget context
- [apps/web/components/budgets/BudgetList.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/components/budgets/BudgetList.tsx)
  only supports display plus deactivate
- [apps/web/components/budgets/CreateBudgetModal.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/components/budgets/CreateBudgetModal.tsx)
  only supports a narrow create workflow

### Bundle A core design position

Bundle A should not be treated as:

- a CRUD page for budgets
- a redirect hub to quota pages
- a breach log

Bundle A should be treated as:

`RunLedger Spend Control Plane`

That means it must unify:

- spend policy definition
- runtime enforcement semantics
- exception management
- breach operations
- notification health
- access-aware financial governance

### Bundle A scope hierarchy

Budget enforcement should be capable of operating at the following levels:

1. `organization`
   - aggregate cap across all workspaces in an org
2. `workspace`
   - default operational boundary
3. `access_group`
   - controlled user cohort or persona cluster
4. `api_key`
   - service account, app, or integration identity
5. `workflow`
   - defined workflow entity
6. `feature_tag`
   - business path or product slice
7. `provider_profile`
   - provider-scoped financial envelope
8. `model`
   - model family or explicit model policy
9. `end_user`
   - user-level cost control where needed

This scope model is required to align FinOps to Organization & Access, API Keys,
Gateway, and Provider Profiles.

### Bundle A enforcement layering

Runtime evaluation should conceptually work like this:

1. resolve organization and workspace
2. resolve access group context if applicable
3. resolve API key identity
4. resolve workflow and feature tag
5. resolve provider profile and model
6. collect applicable budgets
7. evaluate in priority order
8. return enforcement result and audit trail

This gives a single request a full financial-governance chain rather than a
single flat budget match.

### Bundle A policy object

Recommended budget domain shape:

- `id`
- `name`
- `description`
- `scope_type`
- `scope_id`
- `period_type`
- `limit_usd`
- `warning_threshold_pct`
- `critical_threshold_pct`
- `action`
- `fallback_model`
- `downgrade_to_model`
- `owner_type`
- `owner_id`
- `priority`
- `requires_approval_for_override`
- `is_active`
- `created_at`
- `updated_at`

Recommended actions:

- `notify`
- `block`
- `downgrade`
- `throttle`
- `fallback`

### Bundle A route ownership

Recommended route ownership:

- `/budgets`
  - primary Spend Control Plane
- `/budgets/[id]`
  - real budget detail
- `/budget-overrides`
  - compatibility redirect or alias into `/budgets?tab=overrides`

Do not keep budget overrides as a completely independent long-term surface.

### Bundle A tab structure

Recommended `/budgets` tabs:

1. `Overview`
2. `Policies`
3. `Overrides`
4. `Breaches`
5. `Notifications`

#### Overview

Purpose:

- top-level FinOps operational summary

Should show:

- total protected spend
- active budgets
- at-risk budgets
- breached budgets
- active overrides
- notification health
- uncovered spend

#### Policies

Purpose:

- manage budget definitions

Should support:

- create
- edit
- archive
- reactivate
- filter by scope
- filter by action
- filter by owner
- filter by active status
- bulk operations where useful

#### Overrides

Purpose:

- manage all temporary exceptions

Should support:

- pending
- active
- expired
- revoked
- create
- review
- revoke
- approval linkage for high-risk changes

#### Breaches

Purpose:

- incident-style view of spend control failures

Should support:

- timeline
- filters
- severity state
- scope grouping
- pivots into budget detail and related runtime context

#### Notifications

Purpose:

- manage operational delivery channels

Should support:

- create/edit/delete destination
- activate/deactivate
- test destination
- view delivery history
- inspect failures

### Bundle A detail page

Recommended `/budgets/[id]` tabs:

1. `Summary`
2. `Breaches`
3. `Overrides`
4. `Notifications`
5. `History`

#### Summary

Should include:

- budget metadata
- current utilization
- threshold posture
- linked scope entity
- linked access/gateway/provider context
- next projected exhaustion if forecast exists

#### Breaches

Should include:

- breach history table
- event timeline
- actions taken
- notification outcome

#### Overrides

Should include:

- active override
- future scheduled overrides
- past overrides
- approval trail

#### Notifications

Should include:

- attached notification channels
- recent delivery logs
- test action

#### History

Should include:

- audit stream of:
  - create
  - edit
  - archive
  - override create
  - override revoke
  - breach
  - notification test/update

### Bundle A charts

Recommended charts:

1. `Budget Utilization Trend`
   - spend vs limit over time
   - warning and critical thresholds
2. `Coverage by Scope`
   - protected spend by scope type
3. `At-Risk Heatmap`
   - budgets vs recent days or periods
4. `Override Timeline`
   - active and scheduled overrides
5. `Breach Timeline`
   - breach, notify, override, revoke events
6. `Policy Action Mix`
   - notify/block/downgrade/throttle/fallback
7. `Unprotected Spend`
   - traffic or spend without policy coverage
8. `Top Breached Scopes`
   - by workspace/access group/key/workflow/provider/model
9. `Projected Exhaustion`
   - forecast-driven days to breach
10. `Notification Reliability`
   - delivery success/failure rate by destination

### Bundle A required backend improvements

#### API contracts

Add:

- `GET /budgets/{id}`
- `PUT /budgets/{id}`
- optional:
  - `POST /budgets/{id}/archive`
  - `POST /budgets/{id}/reactivate`

Potential future:

- `GET /budgets/coverage`
- `GET /budgets/projections`
- `GET /budgets/{id}/timeline`

#### Data model

Expand budget scope support and metadata.

Current scope support is too narrow and does not reflect the rest of the suite.

#### Override model

Overrides should support:

- scheduled activation
- clear status transitions
- approval relationship when required
- richer operator visibility

#### Runtime enrichment

Budget evaluation should capture:

- which budget matched
- what scope resolution chain was used
- what action was applied
- what downstream effect happened

This should feed auditability and later observability.

### Bundle A required UI improvements

- replace list-only layout with a real control plane shell
- add full edit flow
- replace breach-only detail page
- integrate overrides into budget lifecycle
- integrate notifications into budget lifecycle
- expose rollup data at workspace, org, and platform scope
- add real charts and risk views

### Bundle A relationship to other features

#### Organization profile

- org budgets should be visible as rollup context
- budget management should still remain centered in Budgets

#### Workspaces

- workspace budgets are first-class budget scopes

#### Access groups

- access groups should support linked budget posture
- budget detail should link to access group detail where relevant

#### API keys

- key detail should show applicable budgets
- budget breaches involving an API key should be discoverable there

#### Gateway

- Gateway owns technical quota and route-level controls
- Budget Control Plane owns spend-governance policy
- the UX should explain this distinction clearly

#### Provider profiles

- provider-level budgets should be supported for provider financial envelopes

#### Approvals

- high-risk overrides should route through approval workflows

#### Chargeback

- Bundle C should consume Bundle A scope quality and attribution signals

### Bundle A derivation from the Feature Cohesion Matrix

The current FinOps-first cohesion audit in
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md)
is what defines Bundle A.

Bundle A exists because the matrix shows a coherent cluster of policy-plane
strengths and failures around these surfaces:

- `Budgets`
- `Budget detail`
- `Budget overrides`
- `Budget notifications`

The matrix produced the following implementation findings, and those findings are
the reason Bundle A should be implemented as one grouped pass:

1. `Budgets` must become access-aware.
   Workspace is the only strong current operational scope, but Bundle A needs first-class support for access groups and API keys.
2. `Budgets` must become gateway-aware without becoming gateway-owned.
   Gateway quota tiers and model quotas are adjacent technical controls; Spend Control Plane should own financial policy and exception handling.
3. `Budget detail` is currently the largest cohesion failure.
   Because the shipped route is only breach history, operators cannot see budget relationships to organization rollups, access scopes, API keys, providers, or approvals.
4. `Budget overrides` must become approval-aware.
   The mechanics exist, but the lifecycle is not yet governed the way a crown-jewel FinOps surface should be.
5. `Budget notifications` are stronger in backend than in UI.
   This makes notifications a high-value early win for the Bundle A pass because the underlying delivery and audit behavior already exists.
6. `Provider profiles` and `Tags / workflows` are not yet first-class budget dimensions.
   This is a major cohesion gap if FinOps is meant to align to the rest of the platform rather than remain workspace-only.
7. `Audit log` and `Governance pack` already point in the right evidence direction.
   Bundle A should integrate with those evidence owners instead of creating a parallel proof surface.
8. `Organization profile` should consume budget rollups, but budget editing should remain centered in Bundle A.
   This preserves clear ownership while still making org-level financial posture visible.

### Bundle A implementation phases

These phases are ordered by matrix severity and dependency, not by UI convenience.

#### Phase A1 - Close the biggest structural matrix gaps in the domain model

- enrich budget model
- broaden scope model
- add `GET /budgets/{id}`
- add `PUT /budgets/{id}`
- make `access_group` and `api_key` first-class budget scopes
- prepare `provider_profile`, `workflow`, and `feature_tag` to become first-class policy dimensions

Matrix failures being addressed first:

- `Budgets x Access groups = GAP`
- `Budgets x API keys = GAP`
- `Budgets x Provider profiles = GAP`
- internal `Budgets x Budget detail = GAP` backend foundation

#### Phase A2 - Close the largest operator-facing cohesion failure

- turn `/budgets/[id]` into a real detail experience
- stop treating budget detail as breach history only
- show linked scopes, active overrides, notifications, evidence, and related runtime posture

Matrix failures being addressed:

- `Budget detail` as the largest overall cohesion failure
- `Budget detail x Organization profile = GAP`
- `Budget detail x Request flow / Request explorer = GAP`
- `Budget detail x Workflow detail = GAP`

#### Phase A3 - Pull the fragmented policy surfaces into one control plane

- overview
- policies
- overrides
- breaches
- notifications
- coverage
- uncovered spend

Matrix failures being addressed:

- `Budgets x Budget overrides = PARTIAL`
- `Budgets x Budget notifications = PARTIAL`
- the current split between `/budgets` and `/budget-overrides`

#### Phase A4 - Close the governed-exception and evidence gaps

- approval links
- audit log links
- governance pack links
- override lifecycle governance
- notification and breach evidence timeline

Matrix failures being addressed:

- `Budget overrides x Approvals = GAP`
- `Budget detail x Audit log / Governance pack = PARTIAL or GAP`
- weak override and exception proof trail

#### Phase A5 - Close the runtime and downstream-consumer cohesion gaps

- API key links
- access group links
- gateway links
- provider profile links
- workflow and tag links
- organization and platform rollups

Matrix failures being addressed:

- `Budgets x Model gateway = PARTIAL`
- `Budget detail x Response cache / Rate limits = GAP`
- `Budgets x Tags / workflows = PARTIAL`
- `Budget detail x All organizations = GAP`

#### Phase A6 - FinOps polish after matrix gaps are closed

- charts
- risk scoring
- override timeline
- uncovered spend
- notification health
- next-action suggestions
- operator summary views

---

## Bundle B - Billing and Reconciliation

### Product goal

Bundle B should become the accounting operations layer for FinOps.

It should answer:

- which billing periods are open, closing, or closed
- what adjustments were applied
- what shared costs were allocated
- what can be exported or reconciled
- what period is ready to close

### Bundle B derivation from the Feature Cohesion Matrix

Bundle B is derived from the matrix cluster around:

- `Billing periods`
- `Billing period detail`

And from the section `5` FinOps audit findings in
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md):

- backend supports period create/list/get/close/export plus adjustments and shared-cost policies
- UI is still mostly list/close/export
- billing adjustments and richer reconciliation operations are not surfaced well enough in the detail flow

The section `11` cohesion matrix shows that Billing already has some of the
strongest downstream relationships in FinOps, especially with:

- `Analytics economics`
- `Cost and savings`
- `Billing summary`

But it remains only `PARTIAL` across many of the operator, scope, evidence, and
platform relationships that a real billing and reconciliation layer must own.

### Current state summary

The backend appears richer than the current UI. The page currently emphasizes
list, close, and export, but not the fuller management model.

### Recommended route ownership

- `/billing`
  - parent billing workspace
- `/billing/[period_id]`
  - true period detail and reconciliation page

### Recommended `/billing` tabs

1. `Periods`
2. `Draft / Open`
3. `Closed`
4. `Exports`

### Recommended `/billing/[period_id]` tabs

1. `Summary`
2. `Adjustments`
3. `Shared Costs`
4. `Reconciliation`
5. `Exports`
6. `Audit`

### Bundle B matrix-derived gap inventory

#### Billing domain gaps from section 5

- `/billing` is only `PARTIAL` across backend, UI, actions, docs, and scripts
- `/billing/{period_id}` is only `PARTIAL` and currently acts more like a read path than a true operator detail page
- adjustments and shared-cost policies exist, but remain underexposed in the UI

#### Internal Bundle B cohesion gaps

- `Billing periods x Billing period detail = STRONG`
  The structure is directionally right, but not yet operationally complete.
- period management exists without a strong enough adjustment, reconciliation, and evidence workflow

#### Bundle B x Bundle A gaps

- `Billing periods x Budgets = PARTIAL`
- `Billing detail x Budget overrides = PARTIAL`
- `Billing detail x Budget notifications = PARTIAL`

Bundle B should consume Bundle A outcomes, not merely coexist beside them.

#### Scope and ownership gaps

- `Billing periods x Workspaces = STRONG`
- `Billing periods x Access groups = GAP`
- `Billing periods x API keys = PARTIAL`
- `Billing periods x Provider profiles = PARTIAL`

This shows Billing is already workspace-strong, but weak on the finer ownership
dimensions needed for trustworthy allocation and review.

#### Observe and downstream-consumer gaps

- `Billing periods x Analytics economics = STRONG`
- `Billing periods x Cost and savings = STRONG`
- `Billing detail x Request / run investigation surfaces = PARTIAL`

Observe is already a strong downstream reader of billing data, but the operator
workflow between finance and investigation is still thin.

#### Governance and platform gaps

- `Billing x Audit log / Governance pack = PARTIAL`
- `Billing x Platform settings = PARTIAL`
- `Billing detail x All organizations = PARTIAL`

Billing still needs stronger evidence, close-review, and platform-scale posture.

### Key improvements

- make adjustments manageable from the UI
- expose shared-cost policies clearly
- improve period close workflow
- show unresolved reconciliation issues
- link closed period data back to budgets and chargeback

### Recommended charts

- cost composition by category
- billable vs non-billable trend
- adjustment impact waterfall
- workspace share by period
- reconciliation status indicators

### Cohesion requirements

- must reflect Bundle A override and breach context where relevant
- must feed Bundle C allocation quality
- must feed Bundle D compliance closure

### Bundle B implementation phases

These phases are ordered from the matrix and audit gaps outward.

#### Phase B1 - Expose the real billing domain

- bring adjustments into the UI
- bring shared-cost policy operations into the UI
- normalize `/billing/[period_id]` as a true operator detail page
- make reconciliation state first-class rather than implied

Gaps being closed:

- backend richer than UI
- partial detail-page operator flow
- partial actions for period management

#### Phase B2 - Build the reconciliation workflow

- add `Summary`, `Adjustments`, `Shared Costs`, `Reconciliation`, `Exports`, and `Audit` tabs
- surface unresolved reconciliation issues
- make close blockers and close readiness explicit
- show budget breach and override context where relevant

Gaps being closed:

- `Billing detail x Budget overrides = PARTIAL`
- `Billing detail x Budget notifications = PARTIAL`
- weak close/review workflow

#### Phase B3 - Strengthen scope-aware billing

- expose workspace, access-group, API-key, provider, workflow, and tag-aware breakdowns where the data model supports them
- surface missing attribution or low-confidence attribution in period detail
- prepare Bundle B outputs for Bundle C

Gaps being closed:

- `Billing periods x Access groups = GAP`
- `Billing periods x API keys = PARTIAL`
- `Billing periods x Provider profiles = PARTIAL`

#### Phase B4 - Strengthen evidence and platform review

- add audit links
- add governance-pack linkage
- add platform-scale rollups and close-review posture
- ensure exports carry the right evidence and close metadata

Gaps being closed:

- `Billing x Audit log / Governance pack = PARTIAL`
- `Billing x Platform settings = PARTIAL`
- `Billing detail x All organizations = PARTIAL`

#### Phase B5 - Billing operator polish

- add reconciliation charts
- add adjustment waterfall views
- add period health and export-health views
- add “ready to close” and “blocked close” summaries

---

## Bundle C - Attribution and Allocation

### Product goal

Bundle C should turn cost into ownership.

It should answer:

- who owns the cost
- how spend should be split
- whether cost is mapped to the right workspace, access group, workflow, and feature

### Bundle C derivation from the Feature Cohesion Matrix

Bundle C is derived from the matrix cluster around:

- `Chargeback`

And from the section `5` FinOps audit findings in
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md):

- rules and reports are shipped
- the active dimension list no longer advertises legacy `team`
- rule management still lacks update/edit
- deeper cohesion with access groups and workflow attribution is still missing

The section `11` matrix shows Chargeback is already naturally close to:

- workspaces
- workflows
- economics surfaces
- optimization surfaces

But still remains only `PARTIAL` for several of the ownership and governance
dimensions it should ultimately master.

### Scope

- `Chargeback`

### Recommended dimension model

Prefer:

- workspace
- access_group
- workflow
- feature_tag
- api_key
- provider_profile

Avoid:

- team
- project
- team_model

### Product shape

Recommended `/chargeback` tabs:

1. `Overview`
2. `Rules`
3. `Allocations`
4. `Exceptions`
5. `Exports`

### Bundle C matrix-derived gap inventory

#### Chargeback domain gaps from section 5

- `/chargeback` is still only `PARTIAL` across backend, UI, actions, and completion
- rule management lacks update/edit
- deeper alignment to access groups and workflows is still missing

#### Scope-model gaps

- `Chargeback x Workspaces = STRONG`
- `Chargeback x Access groups = PARTIAL`
- `Chargeback x API keys = PARTIAL`
- `Chargeback x Workflow detail = STRONG`
- `Chargeback x Tags = PARTIAL`

Chargeback has the right direction but not the full ownership-quality model yet.

#### Upstream FinOps gaps

- `Chargeback x Budgets = PARTIAL`
- `Chargeback x Billing periods = PARTIAL`
- `Chargeback x Billing detail = PARTIAL`

Bundle C should consume Bundle A scope quality and Bundle B close outputs more
explicitly than it does today.

#### Observe and optimization gaps

- `Chargeback x Analytics economics = STRONG`
- `Chargeback x Cost and savings = STRONG`
- `Chargeback x Optimization surfaces = PARTIAL`

These are already strong downstream relationships and should be preserved while
the allocation core is tightened.

#### Governance gaps

- `Chargeback x Audit log / Governance pack = PARTIAL`
- `Chargeback x Tags = PARTIAL`

Allocation decisions need a clearer evidence and exception trail.

### Key improvements

- full rule lifecycle including edit
- better attribution dimensions
- alignment to access groups and workflows
- visibility into unallocated spend
- stronger export and billing integration

### Recommended charts

- cost by workspace
- cost by access group
- cost by workflow
- allocation waterfall
- unallocated cost trend

### Cohesion requirements

- must consume Bundle A scope quality
- must align to Bundle B period close outputs
- should not invent duplicate organizational concepts

### Bundle C implementation phases

#### Phase C1 - Complete the rule lifecycle

- add rule edit/update support
- normalize rule detail and exception handling
- make rule precedence and validity visible

Gaps being closed:

- rule management lacks update/edit
- internal chargeback controls weaker than the reporting surface

#### Phase C2 - Deepen the attribution model

- strengthen support for access groups, API keys, workflows, provider profiles, and feature tags
- show attribution confidence and unresolved ownership
- make unallocated spend first-class

Gaps being closed:

- `Chargeback x Access groups = PARTIAL`
- `Chargeback x API keys = PARTIAL`
- `Chargeback x Tags = PARTIAL`

#### Phase C3 - Consume upstream FinOps quality

- pull Bundle A scope quality into chargeback views
- pull Bundle B period-close and reconciliation outputs into allocation status
- show when upstream budget or billing weakness reduces allocation confidence

Gaps being closed:

- `Chargeback x Budgets = PARTIAL`
- `Chargeback x Billing periods = PARTIAL`
- `Chargeback x Billing detail = PARTIAL`

#### Phase C4 - Strengthen downstream optimization and evidence flows

- link allocation findings into workflow detail, economics, and optimization surfaces
- expose rule and export evidence in audit-friendly ways
- add exception and export history

Gaps being closed:

- `Chargeback x Optimization surfaces = PARTIAL`
- `Chargeback x Audit log / Governance pack = PARTIAL`

#### Phase C5 - Allocation operator polish

- add allocation waterfall visuals
- add unallocated trend views
- add attribution-confidence views
- add “top ownership gaps” summaries

---

## Bundle D - Compliance Closure

### Product goal

Bundle D should close the FinOps loop with verifiable evidence and integrity.

It should answer:

- can we verify the snapshot
- is the accounting state internally consistent
- can we produce defensible evidence for audit

### Bundle D derivation from the Feature Cohesion Matrix

Bundle D is derived from the matrix cluster around:

- `Ledger`

And from the section `5` FinOps audit findings in
[FEATURE-AUDIT.md](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/FEATURE-AUDIT.md):

- snapshot generation and verification exist
- `/ledger` itself is not really a cohesive first-class page
- the active conceptual ownership is closer to `Platform settings -> Compliance`

The section `11` matrices show Ledger is strongest where it intersects with:

- `Platform settings`
- `Governance pack`
- downstream evidence closure

and comparatively weak as a day-to-day FinOps operator page. That is why Bundle D
should be implemented as a closure and evidence bundle, not as another budgeting
or billing workspace.

### Scope

- `Ledger`

### Product position

This is best treated as a compliance and platform integrity surface, not as a
front-line FinOps working page.

### Recommended ownership

- move conceptual ownership under Platform Settings or Compliance
- keep FinOps linkage through billing and evidence references

### Key capabilities

- snapshot generation
- verification
- integrity status
- period-linked evidence
- export and audit support

### Recommended charts or views

- snapshot history timeline
- verification pass/fail trend
- mismatch or anomaly summary
- period-to-snapshot linkage

### Cohesion requirements

- should consume Bundle B closed periods
- should reflect Bundle C finalized allocations
- should be linkable from Governance evidence surfaces

### Bundle D matrix-derived gap inventory

#### Ownership and route gaps

- `/ledger` is currently a thin or redirect-oriented surface
- `Ledger x Platform settings = STRONG`
- `Ledger x Governance pack = STRONG`

The product direction is already clear even if the implementation is still partial.

#### Upstream dependency gaps

- `Ledger x Billing periods = PARTIAL`
- `Ledger x Billing detail = PARTIAL`
- `Ledger x Chargeback = PARTIAL`
- `Ledger x Budget detail = GAP`

Ledger should consume the right finalized upstream outputs, but today that chain
is still underexposed.

#### Evidence gaps

- verification exists, but evidence packaging and linkage are still not strong enough as one end-to-end story
- audit, governance-pack, and platform-close posture should feel like one closure workflow

### Bundle D implementation phases

#### Phase D1 - Re-home the ownership model

- keep FinOps linkage, but make Platform Settings / Compliance the real conceptual home
- make `/ledger` a compatibility entry, not a competing owner
- clarify route ownership and navigation

Gaps being closed:

- ledger not being a cohesive active page
- `Ledger x Platform settings = STRONG` should become explicit product ownership

#### Phase D2 - Strengthen the verification domain

- formalize snapshot, verification, integrity status, and anomaly summary as first-class contracts
- show period linkage and close-state provenance
- normalize export and verification result detail

Gaps being closed:

- partial verification and thin operator surface
- weak period-to-ledger close narrative

#### Phase D3 - Build the evidence chain

- link Bundle B close outputs into Ledger
- link Bundle C ownership exports where relevant
- link Audit log and Governance pack directly
- show what evidence is present vs missing for a period close

Gaps being closed:

- `Ledger x Billing periods = PARTIAL`
- `Ledger x Billing detail = PARTIAL`
- `Ledger x Chargeback = PARTIAL`
- evidence packaging still fragmented

#### Phase D4 - Closure and compliance polish

- snapshot timeline
- verification trend
- mismatch summary
- “close readiness” and “evidence completeness” status

---

## Recommended Build Sequence

### Phase 1

Build `Bundle A` as the Spend Control Plane.

Why:

- foundational runtime and admin layer
- highest strategic value
- strongest dependency for all downstream FinOps work

### Phase 2

Build `Bundle B` for billing and reconciliation.

Why:

- period close and accounting should sit on a cleaner budget foundation

### Phase 3

Build `Bundle C` for attribution and allocation.

Why:

- allocation quality depends on scope cohesion from A and period clarity from B

### Phase 4

Build `Bundle D` for compliance closure.

Why:

- this is the final closeout layer, not the starting point

---

## Bundle A Next-Step Spec Hook

When implementation starts, the next planning artifact should define:

- exact backend contract changes
- exact UI tab layout
- exact field set for each budget policy
- exact scope-resolution semantics
- chart-by-chart implementation priority
- approval integration rules for overrides
- relationship to API key, access group, workflow, provider profile, and gateway pages

This file is the product blueprint.
The next file should be the build-ready technical spec for Bundle A.

---

## Bundle A Technical Spec

This section is the build-ready technical spec for `Bundle A - Spend Control Plane`.

It is intended to be implementable directly from the current codebase and should
be used as the primary guide when coding the Bundle A pass.

### Technical goals

Bundle A implementation must achieve all of the following:

1. make budgets a real managed policy domain, not a create/list/delete stub
2. align budget scopes to the actual RunLedger ownership and runtime model
3. connect live budget enforcement to UI-visible state and audit trails
4. unify budget policies, overrides, breaches, and notification operations into one control plane
5. preserve cohesion with Gateway, API Keys, Access Groups, Provider Profiles, Approvals, and Billing

### Current implementation anchor points

Current relevant backend files:

- [apps/api/runledger_api/routers/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/routers/budgets.py)
- [apps/api/runledger_api/services/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/services/budgets.py)
- [apps/api/runledger_api/schemas/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/schemas/budgets.py)
- [apps/api/runledger_api/schemas/budget_overrides.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/schemas/budget_overrides.py)
- [apps/api/runledger_api/models/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/models/budgets.py)
- [apps/api/runledger_api/models/budget_overrides.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/models/budget_overrides.py)

Current relevant web files:

- [apps/web/app/(dashboard)/budgets/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/budgets/page.tsx)
- [apps/web/app/(dashboard)/budgets/[id]/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/budgets/[id]/page.tsx)
- [apps/web/app/(dashboard)/budget-overrides/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/budget-overrides/page.tsx)
- [apps/web/components/budgets/BudgetManager.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/components/budgets/BudgetManager.tsx)
- [apps/web/components/budgets/BudgetList.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/components/budgets/BudgetList.tsx)
- [apps/web/components/budgets/CreateBudgetModal.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/components/budgets/CreateBudgetModal.tsx)
- [apps/web/lib/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/lib/api.ts)
- [apps/web/types/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/types/api.ts)

### Target architecture

Bundle A should be implemented as one cohesive domain:

- `Budget policies`
- `Budget overrides`
- `Budget breaches`
- `Budget notifications`
- `Budget rollups`
- `Budget coverage`
- `Budget history`

The route ownership should remain:

- `/budgets`
- `/budgets/[id]`

And the compatibility route should remain:

- `/budget-overrides` -> should become a redirect or embedded alias into `/budgets?tab=overrides`

### Data model changes

#### Budget model

Current `Budget` should be expanded from a thin record into a richer managed policy.

Recommended new fields:

- `name: str`
- `description: str | None`
- `scope_type: str`
- `scope_id: str | None`
- `period_type: str`
- `limit_usd: Decimal`
- `warning_threshold_pct: Decimal | None`
- `critical_threshold_pct: Decimal | None`
- `action: str`
- `downgrade_to_model: str | None`
- `fallback_model: str | None`
- `owner_type: str | None`
- `owner_id: str | None`
- `priority: int`
- `requires_approval_for_override: bool`
- `is_active: bool`
- `created_at: datetime`
- `updated_at: datetime`

Notes:

- `warning_threshold_pct` default recommended: `80`
- `critical_threshold_pct` default recommended: `100`
- `priority` supports deterministic evaluation when multiple policies match
- `owner_type` and `owner_id` are administrative metadata, not runtime match dimensions

#### Budget scope type expansion

Current supported scope types are too narrow.

Target scope type enum:

- `organization`
- `workspace`
- `access_group`
- `api_key`
- `workflow`
- `feature_tag`
- `provider_profile`
- `model`
- `end_user`

Migration note:

- preserve support for current values:
  - `workspace`
  - `end_user`
  - `feature_tag`
  - `app`
- treat `app` as transitional and migrate toward `workflow` or `api_key` depending on usage

#### Budget override model

Keep current core fields, but expand semantics and optionally schema later with:

- `status`
  - `pending`
  - `active`
  - `expired`
  - `revoked`
- `approved_by`
- `approval_id: str | None`
- `requested_by: str | None`
- `revoked_at: datetime | None`
- `revoked_by: str | None`

Required behavior changes:

- future-dated overrides should start as `pending`
- active window should be computed from `starts_at` and `expires_at`
- expired overrides should be surfaced cleanly in list views
- revocation should stamp actor and timestamp

### Schema changes

#### New or expanded schemas in `schemas/budgets.py`

Add:

- `BudgetUpdate`
- `BudgetDetailResponse`
- `BudgetCoverageResponse`
- `BudgetTimelineEvent`
- `BudgetTimelineResponse`
- `BudgetProjectionResponse`

Suggested `BudgetUpdate`:

- `name?: str`
- `description?: str | None`
- `scope_type?: str`
- `scope_id?: str | None`
- `period_type?: str`
- `limit_usd?: Decimal`
- `warning_threshold_pct?: Decimal | None`
- `critical_threshold_pct?: Decimal | None`
- `action?: str`
- `downgrade_to_model?: str | None`
- `fallback_model?: str | None`
- `owner_type?: str | None`
- `owner_id?: str | None`
- `priority?: int`
- `requires_approval_for_override?: bool`
- `is_active?: bool`

Suggested `BudgetDetailResponse`:

- base budget policy fields
- `current_spend_usd`
- `remaining_usd`
- `pct_used`
- `status`
  - `healthy`
  - `warning`
  - `critical`
  - `breached`
  - `overridden`
- `active_override`
- `recent_breaches_count`
- `notification_count`
- `affected_runtime_scope_summary`

#### Expanded override schemas in `schemas/budget_overrides.py`

Add:

- `BudgetOverrideUpdate`
- `BudgetOverrideDetailResponse`

Even if edit is deferred, define the schema shape early for consistency.

### API contract changes

#### Budget policy lifecycle

Add:

- `GET /budgets/{budget_id}`
- `PUT /budgets/{budget_id}`

Optional but recommended:

- `POST /budgets/{budget_id}/archive`
- `POST /budgets/{budget_id}/reactivate`

Keep:

- `POST /budgets`
- `GET /budgets`
- `DELETE /budgets/{budget_id}`

Implementation preference:

- keep soft-delete semantics
- use explicit archive/reactivate if introducing more operator clarity

#### Budget detail support

Add:

- `GET /budgets/{budget_id}/timeline`
- `GET /budgets/{budget_id}/coverage`

Optional later:

- `GET /budgets/{budget_id}/projection`

#### Existing budget pages that should remain

Keep:

- `GET /budgets/{budget_id}/breaches`
- `POST /budgets/{budget_id}/override`
- `GET /budgets/{budget_id}/overrides`
- `POST /budgets/{budget_id}/override/{override_id}/revoke`
- `GET /budgets/notifications`
- `POST /budgets/notifications`
- `PUT /budgets/notifications/{notification_id}`
- `DELETE /budgets/notifications/{notification_id}`
- `POST /budgets/notifications/{notification_id}/test`
- `GET /budgets/notifications/{notification_id}/deliveries`
- `GET /budgets/rollup`

#### Coverage and governance additions

Recommended:

- `GET /budgets/coverage`
  - returns protected vs unprotected spend by scope
- `GET /budgets/policy-matrix`
  - optional advanced endpoint for “what budgets apply to what”

### Runtime evaluation changes

Current matching in [services/budgets.py](C:/Users/Abi/Desktop/github/runledger-community/apps/api/runledger_api/services/budgets.py)
is too narrow and only directly accounts for workspace, end-user, and feature-tag style matches.

Target runtime inputs should include:

- `organization_id`
- `workspace_id`
- `access_group_ids`
- `api_key_id`
- `workflow_id`
- `feature_tag`
- `provider_profile_id`
- `model`
- `end_user_id`

Recommended internal runtime evaluation shape:

```text
resolve_scope_context(request)
  -> organization
  -> workspace
  -> access groups
  -> api key
  -> workflow / feature tag
  -> provider profile
  -> model
  -> end user

collect_matching_budgets(context)
sort_by_priority_and_scope_specificity()
evaluate_limits()
emit_runtime_result()
```

Required runtime outputs:

- matched budget id
- matched scope type
- current spend
- limit
- action applied
- whether override was in effect

This output should be available for:

- audit
- breach recording
- later observability and FinOps analytics

### UI architecture

#### `/budgets`

Convert to a client-driven control-plane page with tabs.

Recommended top section:

- title: `Spend Control Plane`
- scope selector: `workspace | org | platform`
- date window selector if needed for charts
- quick-create action

Recommended summary cards:

- `Protected Spend`
- `Active Policies`
- `At Risk`
- `Breached`
- `Active Overrides`
- `Notification Health`

Recommended tabs:

1. `Overview`
2. `Policies`
3. `Overrides`
4. `Breaches`
5. `Notifications`

#### `/budgets` Overview tab

Show:

- rollup cards
- budget utilization trend
- coverage by scope
- at-risk heatmap
- active override timeline
- unprotected spend callout

#### `/budgets` Policies tab

Replace the current simple list with:

- searchable table
- filters:
  - scope type
  - action
  - status
  - owner
- columns:
  - name
  - scope
  - period
  - limit
  - current spend
  - thresholds
  - action
  - status
  - active override badge
- row click -> detail page
- row actions:
  - edit
  - archive
  - reactivate
  - create override

#### `/budgets` Overrides tab

Show:

- active
- pending
- expired
- revoked

Columns:

- budget
- scope
- original limit
- override limit
- start
- expiry
- reason
- status
- approval
- actions

Actions:

- create
- revoke
- inspect

#### `/budgets` Breaches tab

Show:

- breach timeline or table
- filters by scope and severity
- action taken
- whether notification succeeded
- whether an override followed

#### `/budgets` Notifications tab

Show:

- destination cards or table
- channel type
- event set
- active status
- delivery success/failure counts
- last success
- last failure
- test action

#### `/budgets/[id]`

Replace current breach-only page with true detail tabs:

1. `Summary`
2. `Breaches`
3. `Overrides`
4. `Notifications`
5. `History`

The route should still support direct linking to breach history views, but it should
not remain breach-history-only.

### Chart implementation plan

Phase 1 charts:

1. `Budget Utilization Trend`
2. `Coverage by Scope`
3. `At-Risk Heatmap`

Phase 2 charts:

4. `Override Timeline`
5. `Breach Timeline`
6. `Policy Action Mix`

Phase 3 charts:

7. `Projected Exhaustion`
8. `Notification Reliability`
9. `Top Breached Scopes`
10. `Unprotected Spend`

### Web API helper changes

Add to [apps/web/lib/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/lib/api.ts):

- `getBudget(id)`
- `updateBudget(id, body)`
- `archiveBudget(id)` or `reactivateBudget(id)` if explicit routes added
- `getBudgetTimeline(id)`
- `getBudgetCoverage()`
- `getBudgetProjection(id)` if implemented

Preserve existing helpers and rewire pages to use the richer contracts.

Add corresponding types to [apps/web/types/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/types/api.ts).

### Access and identity integration

Bundle A must visibly integrate with the existing access model.

#### Access groups

Budget creation and detail should support access-group scopes directly.

Desired UX:

- select an access group as a budget scope
- view linked access group from the budget detail page
- optionally show inherited or related budget coverage on the access-group page later

#### API keys

Budget creation should support API key scope directly.

Desired UX:

- select an API key as a scope
- link from API key detail to applicable budgets
- show breach association when a key is affected

#### Organization and workspace

Rollups should support:

- workspace
- org
- platform

Budget policy creation may remain workspace-owned operationally at first, but the
data model and rollup model should support org-level governance cleanly.

### Gateway and provider cohesion

#### Gateway

Clarify ownership:

- gateway quotas = technical rate and model request controls
- budgets = spend policy and financial governance

Cross-links should exist both ways:

- from budgets to gateway quota sections
- from gateway quota sections to budgets

#### Provider profiles

Bundle A should support provider-profile-scoped policies.

Example:

- all OpenAI premium traffic
- all Anthropic traffic
- all provider X traffic in workspace Y

This is especially useful for negotiated provider envelopes and procurement controls.

#### Model-level spend governance

Do not reopen standalone model budget product surfaces.

Instead:

- keep gateway UI as the technical home for model quotas
- make Bundle A able to show related model-scoped spend policies
- provide a bridge between provider/model quotas and financial budgets

### Approval integration

Budget overrides should be able to require approval.

Target behavior:

- low-risk overrides can be created directly if policy allows
- high-risk overrides should create an approval request
- approval decision should activate the override or deny it

Recommended approval request metadata:

- budget id
- scope type
- scope id
- original limit
- requested override limit
- start
- end
- reason

### Audit and observability requirements

Bundle A should emit or preserve evidence for:

- budget created
- budget updated
- budget archived
- budget reactivated
- override created
- override revoked
- breach detected
- notification tested
- notification updated
- runtime budget action applied

Bundle A should be visible or linkable from:

- Audit log
- Governance pack
- future FinOps or observability drilldowns

### Postman, docs, scripts, examples

Completion bar for Bundle A requires:

- updated Postman collection
- docs for Spend Control Plane
- scenario coverage in `scripts/scenarios`
- at least one runnable example for budget control and override behavior

Recommended docs additions or updates:

- FinOps budgets page
- how budgets relate to gateway quotas
- how overrides relate to approvals

### Migration and compatibility notes

#### Route compatibility

- keep `/budget-overrides` alive as compatibility entry point
- redirect or embed into `/budgets?tab=overrides`

#### Existing budget records

Migration should:

- preserve existing budget rows
- backfill:
  - `name`
  - thresholds
  - priority
  - updated_at`

Example backfill:

- `name = "{scope_type}:{scope_id or workspace} {period_type} budget"`
- `warning_threshold_pct = 80`
- `critical_threshold_pct = 100`
- `priority = 100`

#### Existing scope value `app`

Handle as transitional:

- preserve in DB initially
- map in UI as legacy or hidden
- migrate toward `workflow` or `api_key` once the real source usage is known

### Implementation phases

#### Phase A1 - backend domain expansion

- expand budget schema and model
- add detail and update endpoints
- add scope expansion support
- preserve compatibility

#### Phase A2 - true budget detail page

- replace breach-only detail route
- add summary, overrides, breaches, notifications, history

#### Phase A3 - `/budgets` control-plane shell

- add tabbed layout
- add overview cards
- add policies tab
- add override tab
- add breach tab
- add notifications tab

#### Phase A4 - cross-feature cohesion

- access group scope support
- API key scope support
- provider profile scope support
- gateway cross-links
- approval integration

#### Phase A5 - visualization and polish

- add charts
- add risk views
- add coverage views
- add notification health

### Acceptance criteria

Bundle A is complete when:

- backend has real create/list/get/update/archive semantics for budgets
- UI supports full lifecycle for budgets
- `/budgets/[id]` is a true detail page
- overrides are integrated into the main budget lifecycle
- notifications are first-class in the budget UI
- scope model aligns to org/workspace/access group/api key/workflow/provider/model
- gateway and API-key relationships are visible and coherent
- approvals can govern risky overrides
- docs/Postman/scripts/examples are aligned

### Recommended next step after this spec

Start with `Phase A1 - backend domain expansion` and implement the target
contracts first before redesigning the web surface.

---

## Bundle B Technical Spec

This section is the build-ready technical spec for `Bundle B - Billing and Reconciliation`.

### Technical goals

Bundle B implementation must achieve all of the following:

1. turn billing from a partial list/close/export page into a real accounting operations surface
2. expose the richer backend adjustment and shared-cost model in the UI
3. make period detail actionable rather than read-mostly
4. preserve strong downstream cohesion with economics surfaces while improving upstream cohesion with budgets
5. produce period outputs that Bundle C and Bundle D can trust

### Current implementation anchor points

Current relevant backend files should be verified around the billing router,
services, schemas, and models that support:

- billing periods
- adjustments
- shared-cost policies
- exports
- close operations

Current relevant web files should be verified around:

- [apps/web/app/(dashboard)/billing/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/billing/page.tsx)
- [apps/web/app/(dashboard)/billing/[period_id]/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/billing/[period_id]/page.tsx)
- billing-related API helpers in [apps/web/lib/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/lib/api.ts)
- billing-related types in [apps/web/types/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/types/api.ts)

### Target architecture

Bundle B should be implemented as one cohesive domain:

- `Billing periods`
- `Billing adjustments`
- `Shared-cost policies`
- `Reconciliation issues`
- `Billing exports`
- `Billing close status`
- `Billing evidence links`

The route ownership should remain:

- `/billing`
- `/billing/[period_id]`

### Data model and schema expectations

Bundle B should make the following entities explicit in contracts and UI:

- `BillingPeriod`
- `BillingAdjustment`
- `SharedCostPolicy`
- `ReconciliationIssue`
- `BillingExport`

Recommended period-level computed fields:

- `status`
  - `draft`
  - `open`
  - `closing`
  - `closed`
  - `blocked`
- `reconciliation_status`
  - `clean`
  - `warning`
  - `blocked`
- `adjustment_count`
- `unresolved_issue_count`
- `shared_cost_policy_count`
- `linked_budget_event_count`

### API contract changes

Bundle B should expose or normalize:

- `GET /billing`
- `POST /billing`
- `GET /billing/{period_id}`
- `POST /billing/{period_id}/close`
- `GET /billing/{period_id}/adjustments`
- `POST /billing/{period_id}/adjustments`
- `PUT /billing/{period_id}/adjustments/{adjustment_id}`
- `DELETE /billing/{period_id}/adjustments/{adjustment_id}`
- `GET /billing/{period_id}/shared-costs`
- `POST /billing/{period_id}/shared-costs`
- `PUT /billing/{period_id}/shared-costs/{policy_id}`
- `DELETE /billing/{period_id}/shared-costs/{policy_id}`
- `GET /billing/{period_id}/reconciliation`
- `GET /billing/{period_id}/exports`
- `POST /billing/{period_id}/export`

Recommended additions:

- `GET /billing/{period_id}/evidence`
- `GET /billing/{period_id}/allocation-readiness`

### UI requirements

`/billing` should provide:

- period list with status and readiness indicators
- draft/open/closed filtering
- export visibility
- platform/org/workspace scope controls where supported

`/billing/[period_id]` should provide:

- `Summary`
- `Adjustments`
- `Shared Costs`
- `Reconciliation`
- `Exports`
- `Audit`

### Cross-feature integration requirements

Bundle B must visibly integrate with:

- Bundle A budget breach and override context
- Bundle C allocation-readiness and downstream chargeback quality
- Bundle D ledger and evidence closure
- Observe economics surfaces as read-only downstream consumers

### Implementation phases

#### Phase B1 - backend and contract normalization

- normalize period detail contract
- normalize adjustment and shared-cost lifecycle contracts
- add reconciliation and readiness summaries

#### Phase B2 - operator detail UI

- build actionable period detail tabs
- surface reconciliation issues and close blockers
- add adjustment and shared-cost edit flows

#### Phase B3 - cross-feature linkage

- add budget-event context
- add allocation-readiness handoff
- add evidence handoff to ledger/compliance

#### Phase B4 - support-surface completion

- update docs
- update Postman
- update scenarios and scripts
- add or refresh example coverage where externally meaningful

### Acceptance criteria

Bundle B is complete when:

- billing periods have real create/list/get/close behavior in backend and UI
- adjustments and shared-cost policies are manageable in the UI
- reconciliation state is explicit and actionable
- period detail feeds Bundle C and Bundle D cleanly
- docs/Postman/scripts/examples are aligned

---

## Bundle C Technical Spec

This section is the build-ready technical spec for `Bundle C - Attribution and Allocation`.

### Technical goals

Bundle C implementation must achieve all of the following:

1. make chargeback a true allocation engine rather than a partial rule/report page
2. align allocation to workspace, access-group, workflow, feature-tag, API-key, and provider-profile primitives
3. expose allocation confidence and unallocated spend explicitly
4. consume upstream Bundle A and Bundle B quality signals
5. provide trustworthy downstream ownership outputs for economics, exports, and compliance

### Current implementation anchor points

Current relevant web entry point:

- [apps/web/app/(dashboard)/chargeback/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/chargeback/page.tsx)

Supporting API/types should be verified in:

- [apps/web/lib/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/lib/api.ts)
- [apps/web/types/api.ts](C:/Users/Abi/Desktop/github/runledger-community/apps/web/types/api.ts)

Backend router, service, schema, and model files for chargeback and allocation
should be treated as the implementation anchors for:

- allocation rules
- allocation reports
- export outputs
- attribution dimensions

### Target architecture

Bundle C should be implemented as one cohesive domain:

- `Allocation rules`
- `Allocation outputs`
- `Attribution confidence`
- `Unallocated spend`
- `Allocation exceptions`
- `Chargeback exports`

The route ownership should remain:

- `/chargeback`

### Data model and schema expectations

Recommended first-class concepts:

- `ChargebackRule`
- `AllocationRecord`
- `AllocationException`
- `AllocationExport`

Recommended important fields:

- `dimension_type`
  - `workspace`
  - `access_group`
  - `workflow`
  - `feature_tag`
  - `api_key`
  - `provider_profile`
- `confidence_score`
- `allocation_status`
  - `allocated`
  - `partially_allocated`
  - `unallocated`
  - `conflicted`
- `source_period_id`
- `source_budget_quality_status`

### API contract changes

Bundle C should expose or normalize:

- `GET /chargeback`
- `GET /chargeback/rules`
- `POST /chargeback/rules`
- `PUT /chargeback/rules/{rule_id}`
- `DELETE /chargeback/rules/{rule_id}`
- `GET /chargeback/allocations`
- `GET /chargeback/exceptions`
- `GET /chargeback/exports`
- `POST /chargeback/export`

Recommended additions:

- `GET /chargeback/confidence`
- `GET /chargeback/unallocated`
- `GET /chargeback/allocation-matrix`

### UI requirements

`/chargeback` should provide:

- `Overview`
- `Rules`
- `Allocations`
- `Exceptions`
- `Exports`

The UI must make the following visible:

- editable rule lifecycle
- top ownership dimensions
- unallocated or low-confidence cost
- downstream export readiness

### Cross-feature integration requirements

Bundle C must visibly integrate with:

- Bundle A scope quality and budget coverage posture
- Bundle B closed-period outputs
- workflow detail, economics, and optimization surfaces
- audit and governance evidence for allocation decisions

### Implementation phases

#### Phase C1 - rule lifecycle completion

- add update/edit for rules
- normalize rule detail and precedence

#### Phase C2 - attribution model expansion

- deepen access-group, API-key, workflow, provider-profile, and tag support
- surface confidence and unallocated states

#### Phase C3 - upstream and downstream handoffs

- consume budget and billing quality signals
- feed economics and compliance outputs

#### Phase C4 - support-surface completion

- update docs
- update Postman
- update scenarios and scripts
- align exports and evidence outputs

### Acceptance criteria

Bundle C is complete when:

- chargeback rules are fully manageable in the UI and backend
- unallocated and low-confidence ownership is visible
- allocation outputs reflect the real modern scope model
- Bundle A and Bundle B quality signals are consumed visibly
- docs/Postman/scripts/examples are aligned

---

## Bundle D Technical Spec

This section is the build-ready technical spec for `Bundle D - Compliance Closure`.

### Technical goals

Bundle D implementation must achieve all of the following:

1. make ledger and verification a real closure workflow, not a thin redirect surface
2. align conceptual ownership to Platform Settings / Compliance while preserving FinOps linkage
3. connect billing close outputs, chargeback outputs, and evidence outputs into one closure chain
4. make verification state and anomaly posture explicit
5. provide defensible audit-facing evidence packaging

### Current implementation anchor points

Current relevant user-facing anchors include:

- [apps/web/app/(dashboard)/ledger/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/ledger/page.tsx)
- [apps/web/app/(dashboard)/settings/page.tsx](C:/Users/Abi/Desktop/github/runledger-community/apps/web/app/(dashboard)/settings/page.tsx)

Backend router, service, schema, and model files supporting ledger snapshot,
verification, and compliance posture should be treated as the implementation anchors.

### Target architecture

Bundle D should be implemented as one cohesive domain:

- `Snapshots`
- `Verification results`
- `Integrity anomalies`
- `Period evidence linkage`
- `Compliance exports`

Conceptual ownership should move under:

- `Platform Settings / Compliance`

Compatibility linkage should remain through:

- FinOps navigation
- billing and evidence references

### Data model and schema expectations

Recommended first-class concepts:

- `LedgerSnapshot`
- `VerificationResult`
- `IntegrityAnomaly`
- `PeriodEvidenceLink`

Recommended important fields:

- `verification_status`
  - `pending`
  - `passed`
  - `failed`
  - `warning`
- `period_id`
- `allocation_export_id`
- `evidence_status`
  - `complete`
  - `partial`
  - `missing`

### API contract changes

Bundle D should expose or normalize:

- `GET /ledger`
- `POST /ledger/snapshots`
- `GET /ledger/snapshots`
- `GET /ledger/snapshots/{snapshot_id}`
- `POST /ledger/snapshots/{snapshot_id}/verify`
- `GET /ledger/snapshots/{snapshot_id}/anomalies`
- `GET /ledger/snapshots/{snapshot_id}/evidence`

Recommended additions:

- `GET /ledger/close-readiness`
- `GET /ledger/periods/{period_id}/closure`

### UI requirements

The real operator flow should live under Platform Settings / Compliance and provide:

- snapshot history
- verification status
- anomaly review
- period linkage
- evidence completeness

The `/ledger` route may remain as a compatibility entry, but should not behave
like a competing primary owner.

### Cross-feature integration requirements

Bundle D must visibly integrate with:

- Bundle B close state and exports
- Bundle C finalized allocation outputs
- Audit Log and Governance Pack evidence surfaces
- platform-level compliance and integrity posture

### Implementation phases

#### Phase D1 - route and ownership normalization

- re-home conceptual ownership under Platform Settings / Compliance
- keep compatibility linkage from FinOps

#### Phase D2 - verification and anomaly domain completion

- normalize snapshot, verify, anomaly, and evidence contracts
- make verification state explicit in the UI

#### Phase D3 - evidence-chain integration

- link billing close outputs
- link chargeback exports
- link governance and audit evidence

#### Phase D4 - support-surface completion

- update docs
- update Postman
- update scenarios and scripts
- make closure and evidence story auditable end to end

### Acceptance criteria

Bundle D is complete when:

- the closure workflow is conceptually owned by Platform Settings / Compliance
- ledger verification and anomaly flows are explicit and operator-usable
- billing and chargeback outputs link cleanly into closure
- evidence completeness can be reviewed and exported
- docs/Postman/scripts/examples are aligned
