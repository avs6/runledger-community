# RunLedger Feature Audit and Bundle Blueprint Rules

Last updated: Friday, August 14, 2026

## Purpose

This file defines the required workflow for auditing a major feature family and
turning that audit into a bundle blueprint.

This process exists so features are not designed in isolation, not implemented
from guesses, and not turned into bundle plans before the real product surface
has been audited.

## Primary Rule

`FEATURE-AUDIT.md` is the main entry point.

Do not start from:

- old planning notes
- random docs
- isolated pages
- backend files in isolation
- a bundle blueprint first

Start from `FEATURE-AUDIT.md`, then follow the flow below.

## Fresh Audit Trigger Rule

Every feature request must trigger a fresh audit before implementation work continues.

This applies even when:

- the feature was worked on earlier
- the feature previously showed `COMPLETE`, `IN PROGRESS`, or similar fix-state history
- a bundle blueprint already exists
- a prior pass claimed the feature was finished

The reason is simple:

- the `Feature Gap Matrix` and `Feature Cohesion Matrix` are now the primary audit and remediation drivers
- older `Fix Status` values may predate that matrix-driven workflow
- feature work must be re-grounded in the current matrix state, not inherited from older momentum

For this reason:

- treat `Fix Status = RE-AUDIT REQUIRED` as the default starting posture unless a fresh audit in the current request proves otherwise
- do not resume implementation directly from a historical `Fix Status` value without re-checking the matrices first

## Cohesion Completion Goal

The goal is not only to make individual pages or APIs work in isolation.

The goal is to close the matrices.

That means the intended end state for an audited feature family is:

- no unresolved `PARTIAL` relationships in the relevant `Feature Cohesion Matrix` scope
- no unresolved `GAP` relationships in the relevant `Feature Cohesion Matrix` scope
- remaining cells should resolve to either:
  - `STRONG`, when the relationship should exist and is now cohesive
  - `N/A`, when the relationship truly does not need to exist

If a feature row looks complete in the Feature Gap Matrix but its cohesion block still carries unresolved `PARTIAL` or `GAP` cells, the feature family is not actually finished.

Use this rule when deciding whether to:

- keep implementing
- keep the bundle open
- move to the next feature family

## Cross-Feature Pairing Rule

If a `Feature Cohesion Matrix` cell is marked `PARTIAL` or `GAP`, that relationship
must be treated as shared delivery work by both feature families named in the cell.

This means:

- if `Feature Family A x Feature Family B` has a weak relationship
- and work is picked up under `Feature Family A`
- then the implementation pass must also include the `Feature Family B` side of that relationship
  where needed to close the matrix cell

The same rule applies in reverse:

- if work is picked up under `Feature Family B`
- the paired `Feature Family A` side must also be implemented where needed

Do not treat weak cohesion cells as:

- someone else’s future problem
- a note to defer indefinitely
- a one-sided feature polish item

They are joint remediation requirements.

### Example

If `Gateway & Routing x FinOps` shows `PARTIAL` or `GAP` for the relationship between:

- `Rate limits`
- and `Budgets`

then that relationship must be implemented as one cross-feature change set:

- either when `Gateway & Routing` is taken up
- or when `FinOps` is taken up

but not left half-fixed on only one side.

The same logic applies to:

- `Provider profiles x Budgets`
- `Model gateway x Budget detail`
- `Response cache x Billing periods`
- and any other weak cell in the matrix

### Implementation expectation

When a request touches a feature family, the audit must identify:

1. which `PARTIAL` or `GAP` cells involve that family
2. which paired feature family owns the other side
3. whether this request is expected to close that relationship now
4. what backend, UI, docs, Postman, scripts, and examples need to change on both sides

If the relationship is in scope for the current request, both sides must be updated together.

## Required Flow

When taking up any major feature family, the workflow must be:

1. Read `FEATURE-AUDIT.md` first.
2. Locate the major feature family section.
   Example: `Organization & Access`, `Gateway & Routing`, `Observe`, `Safety & Governance`, `FinOps`, `Build & Improve`, or `Platform / Utility`.
3. Read the feature rows for that major feature carefully.
   Understand:
   - routes
   - backend state
   - UI state
   - actions
   - docs/postman/scripts state
   - complete/cohesion state
   - merge/collapse notes
   - fix order
   - fix status
   - notes
4. Read the Feature Gap Matrix for that feature family.
   This is the gap-capture view inside `FEATURE-AUDIT.md` that explains what is incomplete, partial, legacy, collapsed, or structurally weak before bundle planning begins.
5. Read the `Delivery Audit Crosswalk` for that feature family.
   Use this to understand how the shipped feature surface maps to the broader delivery-surface audit in `DELIVERY-AUDIT.md`.
6. Read the `Feature Cohesion Matrix`.
   Understand:
   - how the major feature relates to other major and minor features
   - what internal gaps exist inside the feature family
   - which relationships are `STRONG`, `PARTIAL`, `GAP`, or `N/A`
7. Reconcile the current request against both matrices.
   Confirm:
   - which gaps are still real in the Feature Gap Matrix
   - which cross-feature relationships are still weak in the Feature Cohesion Matrix
   - whether the existing `Fix Status` is still valid or must be reset/updated
   - what must change for the relevant cohesion cells to move from `PARTIAL` or `GAP` to `STRONG` or justified `N/A`
8. Only after steps `1-7`, create or update a major-feature bundle blueprint file or begin implementation.

## Per-Request Audit Rule

For every implementation request, follow this minimum audit loop before making feature claims or continuing work:

1. locate the feature row in the `Feature Gap Matrix`
2. read the current route, status columns, merge/collapse notes, and notes
3. read the related `Delivery Audit Crosswalk` rows
4. read the relevant block in the `Feature Cohesion Matrix`
5. restate the current gap in matrix terms
6. identify which `PARTIAL` and `GAP` cohesion cells this request is expected to close
7. only then implement or update the blueprint

This is mandatory for:

- new feature work
- continuation of earlier feature work
- polish passes
- cleanup passes
- architecture passes
- collapse or merge decisions

Do not skip the matrix audit just because the same feature was touched earlier in the project.

## Bundle Blueprint Naming

After the audit steps above are complete, create:

- `{FEATURE}-BUNDLES-BLUEPRINT.md`

Examples:

- `FINOPS-BUNDLES-BLUEPRINT.md`
- `ORG-AND-ACCESS-BUNDLES-BLUEPRINT.md`
- `GATEWAY-AND-ROUTING-BUNDLES-BLUEPRINT.md`
- `OBSERVE-BUNDLES-BLUEPRINT.md`
- `SAFETY-AND-GOVERNANCE-BUNDLES-BLUEPRINT.md`

Use uppercase, hyphenated file names in `TODO_ITEMS/`.

## Bundle Blueprint Rule

A bundle blueprint must be derived from the audit.

The audit drives the blueprint.

The blueprint does not drive the audit.

That means:

- section rows in `FEATURE-AUDIT.md` define what feature surfaces exist
- the Feature Gap Matrix defines what is weak or incomplete
- the Delivery Audit Crosswalk explains broader delivery coverage
- the Feature Cohesion Matrix defines how features relate internally and externally
- bundles are implementation groupings derived from those findings

If the cohesion matrix changes materially, the bundle blueprint must be updated.

If an implementation pass changes the real feature state materially, update:

- the relevant row in `FEATURE-AUDIT.md`
- the relevant bundle blueprint
- the `Fix Status` value after the fresh audit, not before it
- the relevant `Feature Cohesion Matrix` cells so the matrix records whether the relationship is now `STRONG`, remains `PARTIAL`, or is truly `N/A`

## Required Bundle Blueprint Contents

Every `{FEATURE}-BUNDLES-BLUEPRINT.md` must contain a full explicit structure.

At minimum, it must contain these top-level sections:

1. Title
   The title should name the major feature family clearly.
2. Last updated date
3. Purpose
   Explain that the file is a working blueprint for that major feature family.
4. Major-feature vision
   Explain what the major feature family should feel like as a cohesive product area.
5. Audit-first or matrix-first rule
   State clearly that `FEATURE-AUDIT.md` drives the blueprint.
6. Feature-to-bundle mapping
   Show exactly which `FEATURE-AUDIT.md` feature rows map into which bundle.
7. Bundle overview
   Define all bundles at a high level and explain the workflow or dependency order.
8. Bundle sections
   Each bundle must get its own full blueprint section.
9. Technical spec sections
   Each bundle must get its own technical spec section.
10. Acceptance criteria
   Each bundle must define what “complete” means.

## Required Bundle Section Structure

Each bundle section must contain all of the following:

1. Bundle name
2. Product goal
3. Scope
   List the exact `FEATURE-AUDIT.md` rows included in the bundle.
4. Derivation from the audit
   Explain how the bundle is derived from:
   - the feature rows
   - the Feature Gap Matrix
   - the Delivery Audit Crosswalk
   - the Feature Cohesion Matrix
5. Current state summary
   Describe what is already real in backend/UI and what is partial, legacy, or missing.
6. Bundle-level route ownership
   Show the main routes, detail routes, redirects, collapsed routes, or compatibility routes.
7. Operator or user workflow
   Explain how a user actually moves through the bundle in the product.
8. Matrix-derived gap inventory
   Break the gaps into meaningful groups such as:
   - internal feature gaps
   - scope and ownership gaps
   - runtime gaps
   - detail-view gaps
   - governance gaps
   - observability gaps
   - platform gaps
9. Architecture and ownership notes
   Explain what this bundle owns and what neighboring features own.
10. Cross-feature integration requirements
   Explain what other major features this bundle must work with.
11. Implementation phases
   Define a phased plan derived from the audit and matrix findings.
12. Bundle polish opportunities
   Charts, dashboards, empty states, operator guidance, or other final-pass improvements.
13. Product enhancement ideas and suggestions
   This section is mandatory. Capture additional product improvements that go beyond the minimum remediation plan, while keeping them clearly separated from audit-required work.

## Required Technical Spec Structure

Each bundle must also have a dedicated technical spec section.

That technical spec must contain:

1. Technical goals
2. Current implementation anchor points
   Reference the key backend files, UI files, API helpers, types, docs, scripts, or examples.
3. Target architecture
   Explain the target conceptual and runtime shape.
4. Data model expectations
   Explain entity changes, new fields, lifecycle state, ownership fields, or computed fields.
5. Schema expectations
   Explain request/response contracts, new schema objects, or expanded schema objects.
6. API contract changes
   List required create/list/get/update/delete or investigative endpoints.
7. UI requirements
   Define list pages, detail pages, tabs, drill-ins, actions, filters, exports, or status states.
8. Cross-feature integration requirements
   Explain exactly how the bundle connects to adjacent major features.
9. Delivery-surface requirements
   Explain required updates to:
   - docs
   - Postman
   - scripts
   - examples
   - README when relevant
10. Implementation phases
    Restate the technical build order in a build-ready way.
11. Acceptance criteria
    State exactly what must be true before the bundle is considered complete.
12. Product enhancement suggestions
    This subsection is mandatory. Record high-level future-facing improvements, richer UX, deeper analytics, stronger automation, or later architectural upgrades that are valuable but not required for the first completion bar.

## Product Enhancement Suggestions Rule

Blueprints must include product enhancement ideas and suggestions.

These should be captured in a dedicated section so they do not get confused with:

- current audit findings
- required remediation work
- must-have technical completion criteria

### Purpose of this section

Use the product enhancement section to capture:

- stronger charts and dashboards
- richer drilldowns
- better empty states and operator guidance
- more advanced workflow or automation ideas
- future integrations
- deeper observability or reporting ideas
- later architectural upgrades
- premium or advanced UX ideas that are not required for the first pass

### Mandatory quantity and level

Every `{FEATURE}-BUNDLES-BLUEPRINT.md` must include:

- at least `10` product enhancement ideas
- ideally `10-20` high-level ideas

These ideas should stay high level.

Do not turn this section into:

- a giant low-level task list
- implementation pseudocode
- backend method-by-method notes
- duplicate acceptance criteria

The goal is to improve product thinking, not to bury the blueprint in speculative detail.

### Rules for product enhancement suggestions

1. Keep enhancement ideas separate from required implementation phases.
2. Mark clearly whether an idea is:
   - required now
   - recommended next
   - optional future enhancement
3. Do not let speculative ideas overwrite the core audit findings.
4. Do not treat enhancement ideas as part of the completion bar unless they are explicitly promoted into required work.
5. If an enhancement idea depends on first fixing an audit gap, say that explicitly.
6. Include enough ideas to broaden product thinking, not just two or three minor polish notes.
7. Prefer high-signal ideas that improve cohesion, usability, reporting, governance, scale, or operator confidence.

### Recommended structure for the enhancement section

Each bundle blueprint must include a section such as:

- `Product enhancement ideas`
- `Recommended improvements`
- `Future deepening opportunities`

That section should group ideas into categories like:

- operator UX improvements
- charts and visualization improvements
- automation and workflow ideas
- analytics and reporting ideas
- architecture or scale improvements
- governance or compliance deepening

Recommended format:

- a flat numbered list of `10-20` ideas
- each idea should be 1-3 sentences
- each idea should state why it would improve the product
- each idea should stay clearly outside the required implementation bar unless promoted later

### Required discipline

Enhancement ideas are valuable, but they must stay subordinate to the audit-driven plan.

The order remains:

1. audit the real product surface
2. identify gaps
3. derive bundles
4. define required implementation work
5. then capture enhancement ideas as a clearly separate section

## How To Derive Bundles

Bundles must be grouped from the audit and cohesion evidence.

Good bundle boundaries usually come from one or more of the following:

- features that are already tightly related in the product workflow
- rows that share the same runtime or admin ownership
- rows that depend on the same foundational backend work
- rows that are only partially complete because of the same missing detail surface
- rows that are strongly connected in the cohesion matrix
- rows that are currently fragmented and need to be collapsed into one operator surface

Do not create arbitrary bundles just to make a plan look neat.

## Mandatory Interpretation Rules

When reading `FEATURE-AUDIT.md`, always respect:

- `Merge / Collapse`
  If a feature should be collapsed, do not blueprint it as a separate long-term product area unless the audit explicitly reverses that decision.
- `Cohesion`
  If cohesion is weak, the bundle should include the work needed to close that weakness.
- `Fix Order`
  Foundation and runtime paths come before dependent polish.
- `Fix Status`
  Do not rewrite completed work as though it were unstarted.
- `Delivery Audit Crosswalk`
  Use it to align docs, Postman, scripts, examples, README, and infrastructure coverage.

## Required Order Inside Each Bundle

Each bundle plan should think in this order:

1. backend and runtime truth
2. managed entity lifecycle or investigative lifecycle
3. detail views
4. UI shell and operator workflow
5. cross-feature cohesion
6. docs/Postman/scripts/examples
7. polish

## Completion Standard

A bundle is not complete because a page exists.

A bundle is complete only when the relevant work is aligned across:

- backend
- runtime behavior where relevant
- UI
- detail and list flows
- docs
- Postman
- scripts
- examples
- cross-feature cohesion

## Special Rule For Major Features

When writing a `{FEATURE}-BUNDLES-BLUEPRINT.md`, keep the major feature family as
the top-level organizing unit.

Do not mix unrelated major features into one blueprint.

Examples:

- `FinOps` gets its own blueprint
- `Organization & Access` gets its own blueprint
- `Gateway & Routing` gets its own blueprint

Cross-feature dependencies must still be documented inside the blueprint through
the cohesion and implementation sections.

## Practical Summary

The correct sequence is:

1. `FEATURE-AUDIT.md`
2. major feature section
3. Feature Gap Matrix
4. Delivery Audit Crosswalk
5. Feature Cohesion Matrix
6. derive bundle groupings
7. write `{FEATURE}-BUNDLES-BLUEPRINT.md`
8. make the blueprint fully structured, implementation-ready, and driven by the audit evidence above

This is the required working rule for future feature-family audits and bundle planning.

## Development, Audit, And Close-Out Workflow

After a blueprint exists, the work does not stop at planning.

The required delivery loop for actually developing and closing a feature or
bundle is:

1. start from the current `FEATURE-AUDIT.md` row state
2. confirm what the feature currently owns
3. confirm what is collapsed, legacy, or compatibility-only
4. confirm what the bundle blueprint says must be implemented
5. build the backend and runtime truth first
6. build or finish the UI and operator workflow second
7. update docs, Postman, scripts, examples, and README where relevant
8. verify cross-feature cohesion
9. update the audit rows honestly
10. only then mark the work complete

This section explains the required detail for that workflow.

## Step 1 - Re-read The Audit Before Changing Code

Before implementing a feature or bundle:

- re-read the exact feature rows in `FEATURE-AUDIT.md`
- re-read the `Notes`
- re-read the `Merge / Collapse` instructions
- re-read the `Fix Order`
- re-read the `Fix Status`
- re-read the `Delivery Audit Crosswalk`
- re-read the relevant cohesion block

Do not start implementation from memory.

Always verify:

- what the current owner surface is
- what adjacent surfaces own
- whether the route is real, collapsed, or compatibility-only
- whether completion should be judged as CRUD, investigation completeness,
  admin completeness, runtime completeness, or evidence completeness

## Step 2 - Define The Exact Completion Bar

Before writing code, state internally what "done" means for that feature class.

Examples:

- managed entity feature:
  backend CRUD + UI CRUD + detail/list flows + support surfaces
- observability feature:
  real backend data + real filters/drilldowns + export/detail completeness +
  support surfaces
- redirect/collapsed feature:
  route ownership clarified + compatibility redirect works + docs/support assets
  reflect the collapse
- architecture feature:
  ownership boundaries are real in code, consumers are migrated, stale paths are
  removed, and support surfaces match the new architecture

Do not apply the wrong completion bar.

## Step 3 - Build Backend And Runtime Truth First

Implementation order must follow the repo standard:

1. backend contracts
2. runtime enforcement or runtime behavior if relevant
3. data model and validation
4. detail/list query shape
5. UI shell and actions

This means:

- do not build decorative UI on incomplete backend contracts
- do not mark governance complete if runtime enforcement is still missing
- do not mark gateway work complete if live traffic still depends on deprecated
  behavior
- do not mark admin CRUD complete if update/delete/detail lifecycle is missing

When the feature implies runtime truth, verify the real runtime path rather than
only admin configuration pages.

## Step 4 - Finish The Full User Workflow

Do not stop at one page.

For a feature with list/detail/create/update/delete expectations, verify all of:

- list page
- detail page
- create flow
- edit flow
- delete or archive flow
- filters/search/scope states where relevant
- empty states
- error states
- permission-aware behavior

For an investigative or observability feature, verify all of:

- summary entry point
- filters/search
- pagination or cursor behavior
- drill-in path
- exports
- related-entity pivots
- evidence or correlation context where relevant

For a collapsed feature, verify all of:

- redirect or compatibility path works
- real owner surface exposes the required controls
- no duplicate ghost UI remains active

## Step 5 - Review Cross-Feature Cohesion Before Calling It Done

Every feature must be checked against adjacent major features before closure.

Examples:

- gateway work must be checked against org scope, observability, governance, and
  FinOps
- org/admin work must be checked against workspaces, access groups, API keys,
  and onboarding
- observability work must be checked against runtime, governance, and economics
- governance work must be checked against runtime enforcement, evidence, and
  org scope
- build surfaces must be checked against gateway, evaluation, observability, and
  optimization

Use the cohesion matrix actively.

Do not treat it as documentation only.

If a feature is technically implemented but still behaves like an isolated
island, it is not ready for close-out.

## Step 6 - Update Delivery Surfaces As Part Of The Feature

After code is done, review the delivery surfaces tied to the
`Delivery Audit Crosswalk`.

That means checking and updating as needed:

- docs
- Postman
- scripts
- examples
- README
- infrastructure or compose files where relevant

If the feature changed routes, ownership, redirects, or terminology, update the
supporting materials in the same pass.

Do not defer these updates as "later cleanup" unless the audit explicitly tracks
them as a separate remaining item.

## Step 7 - Re-audit The Feature After The Changes

After implementation, re-audit the feature row as if you were seeing it fresh.

Check:

- Backend
- UI
- Actions
- Docs
- Postman
- Scripts/Examples
- Complete
- Cohesion
- Merge / Collapse still accurate
- Fix Status
- Notes

Use honest statuses:

- `OK` only if verified
- `PARTIAL` if still incomplete
- `LEGACY` only for intentionally minimized or compatibility-only surfaces
- `NO` or non-complete status if the feature still misses the real completion
  bar

Do not promote a feature to complete just because major code landed.

## Step 8 - Update The Audit Files Explicitly

When work is complete, update:

- the relevant row in `FEATURE-AUDIT.md`
- any impacted matrix notes if the cohesion story materially changed
- the related row or override in `DELIVERY-AUDIT.md` if delivery completeness
  changed
- the relevant blueprint if the implementation materially changed the future
  plan, ownership boundary, or bundle definition

The audit files are not optional notes.

They are part of the product-delivery source of truth.

## Mandatory Completion Marking Rule

When a feature, subfeature, collapsed surface, or bundle-level implementation
pass is actually finished, it must be marked complete in both audit systems.

That means:

- update the relevant row in `FEATURE-AUDIT.md`
- update the corresponding row or audited override in `DELIVERY-AUDIT.md`

Do not treat one audit file as sufficient on its own.

The expected close-out is:

- `FEATURE-AUDIT.md` reflects shipped feature truth, ownership, collapse state,
  cohesion, and fix status
- `DELIVERY-AUDIT.md` reflects delivery completeness across docs, Postman,
  scripts, examples, README, and infrastructure where relevant

If the implementation is complete in code but either audit file still shows the
old state, the work is not fully closed.

## Step 9 - Close The Item Carefully

Only close a feature, row, or bundle when all of the following are true:

- the right owner surface exists
- backend truth is real
- runtime truth is real where required
- UI and actions are complete for the feature class
- collapsed and legacy routes are handled intentionally
- docs/Postman/scripts/examples are aligned
- cohesion with adjacent features is acceptable
- audit rows have been updated to reflect reality

If any of those are still untrue, leave the item open and describe what remains.

## Required Close-Out Language

When updating audit rows or blueprint notes:

- say what is complete now
- say what class of feature it is
- say why the completion bar is satisfied
- say what remains only if real remaining work still exists

Good examples:

- "Complete as a managed entity surface: backend and UI now support create,
  list, detail, update, and delete, and docs/Postman/scripts/examples are
  aligned."
- "Complete as an investigative observability surface: filtering, drill-in,
  export, pagination, and related pivots are all present and verified."
- "Complete as a deliberate collapse: the old route is now compatibility-only,
  the real owner surface contains the controls, and support material reflects
  the new ownership."

Avoid vague close-out language such as:

- "done for now"
- "mostly complete"
- "good enough"
- "should be fine"

## Required Rule For Incomplete Work

If you discover a feature is broader than expected:

- do not silently narrow the scope
- do not declare victory on only the easiest page
- do not ignore the detail route, support assets, or runtime path

Instead:

1. update the audit honestly
2. capture the gap in the blueprint if needed
3. leave the row or bundle open
4. state clearly what remains

## Final Operating Principle

The workflow is:

1. audit the real surface
2. derive the bundle
3. implement the feature end to end
4. re-audit it honestly
5. update the source-of-truth files
6. close it only when backend, UI, support surfaces, and cohesion all hold

This is the required rule for developing, auditing, and closing RunLedger
features one brick at a time without leaving partial, duplicate, or
decorative-only work behind.
