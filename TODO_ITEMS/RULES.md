# RunLedger Audit, Blueprint, and Implementation Rules

Last updated: 2026-08-14

## Directory Structure

```
TODO_ITEMS/
├── RULES.md                         ← this file
├── FEATURE-STATUS.md                ← dashboard: bundle status + WU index
├── INVENTORY.md                     ← docs/examples/scripts/infra catalog
│
├── 01-ORG-AND-ACCESS/
│   ├── BLUEPRINT.md                 ← bundle blueprint for this feature family
│   ├── GAP-MATRIX.md                ← feature rows: status per surface
│   ├── COHESION-MATRIX.md           ← this feature vs all other features
│   ├── DELIVERY-STATUS.md           ← delivery surface completeness
│   └── WORK-UNITS/
│       ├── WU-001-<slug>.md         ← work units owned by this feature
│       └── ...
│
├── 02-GATEWAY-AND-ROUTING/          ← same structure per folder
├── 03-OBSERVE/
├── 04-SAFETY-AND-GOVERNANCE/
├── 05-FINOPS/
├── 06-BUILD-AND-IMPROVE/
├── 07-PLATFORM-AND-UTILITY/
├── 08-PLANNED-ARCHITECTURE/
└── LATER/
```

## File Responsibilities

| File | One Job | Owned By |
|------|---------|----------|
| `{folder}/BLUEPRINT.md` | Bundle plan: vision, scope, phases, tech spec, acceptance | Feature family |
| `{folder}/GAP-MATRIX.md` | Feature row status: Backend, UI, Actions, Docs, Postman, Scripts, Complete, Cohesion | Feature family |
| `{folder}/COHESION-MATRIX.md` | This feature vs every other feature: STRONG / PARTIAL / GAP / N/A per cell | Feature family |
| `{folder}/DELIVERY-STATUS.md` | Delivery surface: Backend, UI, Docs, README, Examples, Postman, Manual Lab, Auto Script, Infra | Feature family |
| `FEATURE-STATUS.md` | Dashboard rollup: bundle status, GAP/PARTIAL counts, active WU index | Cross-cutting |
| `{folder}/WORK-UNITS/WU-NNN-<slug>.md` | One implementable unit of work with explicit cohesion targets | Feature family |
| `INVENTORY.md` | Reference catalog of docs, examples, scripts, services | Cross-cutting |

---

## The 10 Rules

### Rule 1: Start From the Audit, Not From Memory

Before any implementation, read the target feature's folder:
1. `GAP-MATRIX.md` — current feature row status
2. `COHESION-MATRIX.md` — cross-feature relationships
3. `DELIVERY-STATUS.md` — delivery surface completeness
4. `BLUEPRINT.md` — bundle plan and scope

Do not start from old planning notes, previous conversations, or assumptions about what was already done. The folder is the source of truth.

### Rule 2: Re-Audit Before Every Implementation Pass

Every feature request triggers a fresh audit, even when:
- the feature was worked on earlier
- a prior pass claimed completion
- a blueprint already exists

`Fix Status = RE-AUDIT REQUIRED` is the default posture until a fresh audit in the current request proves otherwise.

### Rule 3: Define the Completion Bar for the Feature Class

Before writing code, state what "done" means for this type of feature:

| Feature Class | Completion Bar |
|---------------|----------------|
| Managed entity | Backend CRUD + UI CRUD + detail/list + support surfaces |
| Observability / investigative | Real backend data + filters/drilldowns + export + detail |
| Redirect / collapsed | Route ownership clarified + redirect works + docs reflect collapse |
| Architecture | Ownership boundaries real in code + consumers migrated + stale paths removed |

Do not apply a CRUD completion bar to an observability surface, or vice versa.

### Rule 4: Build Backend First, Then UI, Then Support

Implementation order within any work unit:
1. Backend contracts and data model
2. Runtime enforcement or behavior (if applicable)
3. UI shell and actions
4. Docs, Postman, scripts, examples

Do not build decorative UI on incomplete backend contracts. Do not mark governance complete if runtime enforcement is missing.

### Rule 5: Cross-Feature Pairing — Close Both Sides

If a cohesion cell is `PARTIAL` or `GAP`, that relationship is shared work by both feature families.

When work is picked up under Feature A that involves a weak cell with Feature B:
- Implement both the A side and the B side in the same change set
- Update `A/COHESION-MATRIX.md` (A's view of B)
- Update `B/COHESION-MATRIX.md` (B's view of A)

A cohesion cell left half-fixed on only one side is not closed.

### Rule 6: Work Units Are the Operational Queue

Every implementation task must have a corresponding `{folder}/WORK-UNITS/WU-NNN-<slug>.md` file inside the owning major feature's folder.

Each work unit must specify:
- Target feature and bundle
- Cohesion cells to close (with target state)
- Paired features that must also change
- Files to update when done
- Acceptance criteria

Do not start implementation without a work unit. Do not create a work unit without first reading the relevant GAP-MATRIX and COHESION-MATRIX.

### Rule 7: Update All Audit Files When Done

When a work unit is completed, update:
1. Target feature's `GAP-MATRIX.md` — feature row status
2. Target feature's `COHESION-MATRIX.md` — cells that changed
3. Paired feature's `COHESION-MATRIX.md` — their view of the changed cells
4. Target feature's `DELIVERY-STATUS.md` — if delivery surfaces changed
5. `FEATURE-STATUS.md` — dashboard counts and WU status
6. The work unit file — mark status as DONE

If either audit file still shows old state after code is complete, the work is not closed.

### Rule 8: Blueprint Structure Requirements

Every `{folder}/BLUEPRINT.md` must contain:

**Blueprint sections:** Title, last updated, purpose, major-feature vision, feature-to-bundle mapping, bundle overview, and per-bundle sections with: product goal, scope (exact GAP-MATRIX rows), current state, route ownership, operator workflow, gap inventory, architecture notes, cross-feature requirements, implementation phases, polish opportunities, and 10–20 product enhancement ideas.

**Technical spec sections (per bundle):** Technical goals, current anchor points, target architecture, data model, schema, API contracts, UI requirements, cross-feature integration, delivery-surface requirements, implementation phases, acceptance criteria, and product enhancement suggestions.

Enhancement ideas must stay clearly separated from required remediation work.

### Rule 9: Honest Status Language

Use precise close-out language:
- "Complete as a managed entity surface: backend and UI now support create, list, detail, update, and delete."
- "Complete as an investigative surface: filtering, drill-in, export, and related pivots are verified."
- "Complete as a deliberate collapse: route redirects, real owner has the controls, docs reflect the change."

Do not use: "done for now", "mostly complete", "good enough", "should be fine".

When work is incomplete, leave the item open and state what remains.

### Rule 10: The Goal Is to Close the Matrices

The end state for any audited feature family is:
- No unresolved `GAP` cells in its COHESION-MATRIX
- No unresolved `PARTIAL` cells in its COHESION-MATRIX
- Every cell resolves to `STRONG` (relationship is real and cohesive) or `N/A` (no meaningful dependency)

If a feature row looks complete in GAP-MATRIX but its COHESION-MATRIX still carries unresolved cells, the feature family is not finished.

---

## Work Unit Template

File: `{folder}/WORK-UNITS/WU-NNN-<slug>.md`

```markdown
# WU-NNN: <Short descriptive name>

- **Status**: NOT_STARTED | IN_PROGRESS | DONE | VERIFIED
- **Bundle**: <Feature family> - <Bundle name>
- **Target**: <folder>/<feature> (`/route`)
- **Created**: <date>
- **Completed**: <date or blank>

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| FinOps: Budget detail | Org: Organization profile | 05×01 | GAP | STRONG |
| FinOps: Budget detail | Org: Access groups | 05×01 | GAP | STRONG |
| ... | ... | ... | ... | ... |

## Paired Features (files to update)

- `05-FINOPS/GAP-MATRIX.md` — Budget detail row
- `05-FINOPS/COHESION-MATRIX.md` — Budget detail cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Budget detail
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Budget detail

## Scope

- **Backend**: <what changes>
- **UI**: <what changes>
- **Docs**: <what changes>
- **Postman**: <what changes>
- **Scripts/Examples**: <what changes>

## Acceptance Criteria

1. <concrete criterion>
2. <concrete criterion>
3. All listed cohesion cells updated to target state
4. All paired feature files updated
5. FEATURE-STATUS.md dashboard updated
```

---

## Status Legend

### GAP-MATRIX and DELIVERY-STATUS

| Status | Meaning |
|--------|---------|
| `OK` | Verified working |
| `PARTIAL` | Present but incomplete, buggy, or unclear |
| `MISSING` | Absent, broken, or disconnected |
| `LEGACY` | Compatibility-only surface; do not expand |
| `PENDING` | Not yet audited |
| `N/A` | Not applicable |

### COHESION-MATRIX

| Status | Meaning |
|--------|---------|
| `STRONG` | Relationship is real and cohesive |
| `PARTIAL` | Some integration exists but incomplete |
| `GAP` | Relationship should exist but is missing or too weak |
| `N/A` | No meaningful direct dependency |

### Work Unit Status

| Status | Meaning |
|--------|---------|
| `NOT_STARTED` | Defined but no implementation begun |
| `IN_PROGRESS` | Active implementation |
| `DONE` | Code complete, audit files updated |
| `VERIFIED` | Re-audited and confirmed after completion |

---

## RE-AUDIT Trigger

**Trigger**: When the user says `RE-AUDIT <Major-Feature> <Minor-Feature>`, execute the full audit workflow below.

**Format**: `RE-AUDIT 01-ORG-AND-ACCESS Organization profile`

The major feature is the folder name (e.g., `01-ORG-AND-ACCESS`, `05-FINOPS`). The minor feature is the sub-feature name as it appears in GAP-MATRIX rows (e.g., `Budgets`, `Provider profiles`, `Playground`).

### RE-AUDIT Workflow

#### Step 1: Load Context

Read these files for the target major feature folder:
1. `{folder}/GAP-MATRIX.md` — find the row for the minor feature
2. `{folder}/COHESION-MATRIX.md` — find all cells involving the minor feature
3. `{folder}/DELIVERY-STATUS.md` — find the delivery row for the minor feature
4. `{folder}/BLUEPRINT.md` — understand bundle ownership and scope

#### Step 2: Audit the Codebase

For the target minor feature, audit the real codebase against each surface:

| Surface | What to check |
|---------|---------------|
| **Backend** | API router exists, endpoints return correct data, CRUD operations work, auth is present |
| **UI** | Page renders at the route, data loads, actions work, navigation is correct |
| **Actions** | Create/update/delete/list operations work end to end (or equivalent for the feature class) |
| **Docs** | `docs/` coverage exists — setup, usage, architecture references |
| **Postman** | Request exists in `postman/RunLedger.postman_collection.json` |
| **Scripts/Examples** | `scripts/` or `examples/` coverage exercises the feature |
| **Complete** | Overall feature completeness per Rule 3 (feature class determines the bar) |
| **Cohesion** | Cross-feature relationships are real in code, not just claimed |

Search the codebase using the feature's route, model names, router files, and UI components. Do not rely on prior conversation context or assumptions.

#### Step 3: Determine Statuses

Assign a status to each surface based on what the code actually shows:
- `OK` — verified working
- `PARTIAL` — present but incomplete, buggy, or unclear
- `MISSING` — absent, broken, or disconnected
- `LEGACY` — compatibility-only surface; do not expand
- `N/A` — not applicable for this feature class

For cohesion cells, audit the relationship between the minor feature and each target feature:
- `STRONG` — relationship is real and directionally cohesive in the code
- `PARTIAL` — some integration exists but incomplete or not operator-friendly
- `GAP` — relationship should exist but is missing or too weak
- `N/A` — no meaningful direct dependency

#### Step 4: Update GAP-MATRIX

Update the minor feature's row in `{folder}/GAP-MATRIX.md` with the audited statuses. Replace `PENDING` values with the determined status. Update the Fix Status column to reflect current state.

#### Step 5: Update COHESION-MATRIX

For every sub-matrix in `{folder}/COHESION-MATRIX.md`:
1. Find the row for the target minor feature
2. Update each cell with the audited cohesion status
3. Update the Finding column with a one-sentence summary of the current relationship

Then update the **paired feature's** COHESION-MATRIX (Rule 5): if the target is `05-FINOPS: Budgets` and a cell involves `01-ORG-AND-ACCESS: Workspaces`, also update `01-ORG-AND-ACCESS/COHESION-MATRIX.md` to reflect the same relationship from the other side.

#### Step 6: Update DELIVERY-STATUS

Update the minor feature's row in `{folder}/DELIVERY-STATUS.md` with audited delivery surface statuses: Backend, UI, Docs, README, Examples, Postman, Manual Lab, Auto Script, Infra, Supporting Infra.

#### Step 7: Report

After all updates, output a **compact one-line summary only** — no verbose breakdown, no per-surface listing, no per-sub-matrix counts:

```
RE-AUDIT COMPLETE: {Major Feature} → {Minor Feature} | GAP-MATRIX: {Fix Status} | COHESION: {n} cells set | DELIVERY: {confirmed or updated}
```

Do not narrate the audit process, do not list individual surface findings, and do not explain cohesion determinations. The files are the record — the report is just a confirmation line.

### RE-AUDIT Scope Rules

- **One minor feature per RE-AUDIT**. Do not batch multiple sub-features in a single pass.
- **Audit the code, not the docs**. If docs say a feature works but the code disagrees, trust the code.
- **Do not change N/A cells**. If a cohesion cell is `N/A`, it stays `N/A` — the audit only changes `PENDING` cells or corrects previously-set statuses.
- **Do not implement fixes during audit**. The RE-AUDIT workflow only observes and records. If the audit reveals gaps, they stay as `GAP` or `MISSING` until a work unit addresses them.
- **Keep output terse**. Do not narrate codebase searches, do not list per-file findings inline, do not explain each status determination. Work silently, update files, print the one-line summary.
- **Update the `Last updated` line** in each file touched, using the current date.

---

## Required Flow Summary

```
1. Read the feature folder (GAP-MATRIX, COHESION-MATRIX, DELIVERY-STATUS, BLUEPRINT)
2. Identify GAP and PARTIAL cells in scope
3. Create or pick up a Work Unit (WU-NNN)
4. Implement: backend → runtime → UI → support surfaces
5. Update both sides of every cohesion relationship
6. Update all audit files honestly
7. Update FEATURE-STATUS.md dashboard
8. Mark WU as DONE
9. Re-audit to verify → mark as VERIFIED
```
