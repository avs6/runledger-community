# RunLedger Work Unit Implementation Rules

Last updated: 2026-08-16

This file is the implementation companion to [`TODO_ITEMS/RULES.md`](C:/Users/Abi/Desktop/github/runledger-community/TODO_ITEMS/RULES.md).

Use it when a work unit already exists and the next job is to **implement it completely** rather than re-audit the feature.

---

## Purpose

A work unit is not a suggestion or a loose theme.

A work unit is an **implementation contract** that must:

1. close specific cohesion cells
2. improve the real product, not just the audit files
3. leave backend, UI, docs, Postman, scripts, and examples aligned
4. update both sides of every changed relationship

If the code changes but the matrices still describe the old reality, the work unit is not done.

---

## Core Implementation Order

For every work unit, execute in this order:

1. Read the work unit file.
2. Read the owning folder's `GAP-MATRIX.md`.
3. Read the owning folder's `COHESION-MATRIX.md`.
4. Read the paired folder's `COHESION-MATRIX.md`.
5. Read the owning folder's `DELIVERY-STATUS.md`.
6. Read the owning folder's `BLUEPRINT.md` if the scope or bundle intent is unclear.
7. Implement backend first.
8. Implement runtime behavior or enforcement next if applicable.
9. Implement UI flows and navigation.
10. Update docs.
11. Update Postman.
12. Update scripts and examples.
13. Re-check the real feature behavior.
14. Update all audit/status files.

Do not skip the paired matrix. Do not update matrices before the code is real.

---

## Work Unit Execution Rules

### Rule 1: The Work Unit Owns the Scope

The work unit file is the immediate execution contract.

It defines:

- target feature
- bundle
- cohesion cells to close
- paired features
- acceptance criteria

Do not expand into unrelated cleanup unless:

- it is required to make the work unit real
- or the existing code directly blocks the target behavior

Keep the change set tight, but complete.

### Rule 2: Close the Real Product Path

A cohesion cell only moves to `STRONG` when the real operator flow works.

Examples:

- a page links to the related surface with the correct scope pre-applied
- backend contracts accept and validate the new scope
- the target page actually consumes that scope
- exports and detail views preserve the same context
- runtime behavior honors the configured entity rather than just storing metadata

Do not mark a relationship `STRONG` because:

- a field exists in a schema
- a row stores the value but nothing uses it
- a page mentions the concept without real drill-through
- docs claim support that the product does not actually provide

### Rule 3: Backend First Means Real Runtime First

When the work unit changes behavior, implement:

- validation
- ownership checks
- routing behavior
- query filtering
- attribution logic
- policy enforcement
- runtime contracts

before UI polish.

If the UI can select a scope but the backend ignores it, the work unit is incomplete.

### Rule 4: Drill-Through Matters

For cross-feature cohesion work, try to close the operator loop, not just the data model.

That usually means:

- source page links to target page
- target page loads with the right query params or route context
- filters persist into detail views
- detail views preserve context into exports or downstream flows

Weak cross-navigation is usually `PARTIAL`, not `STRONG`.

### Rule 5: Support Surfaces Are Part of Implementation

After backend and UI changes, review and update:

- `docs/`
- `postman/RunLedger.postman_collection.json`
- `scripts/`
- `examples/`

If the feature changed and these surfaces still describe old behavior, the work unit is not complete.

### Rule 6: Work Units Must Update Both Sides of Cohesion

If a work unit closes:

- `01-ORG-AND-ACCESS -> 05-FINOPS`

then update:

- `TODO_ITEMS/01-ORG-AND-ACCESS/COHESION-MATRIX.md`
- `TODO_ITEMS/05-FINOPS/COHESION-MATRIX.md`

The language does not need to be identical, but the state must agree.

### Rule 7: Completion Is Earned, Not Assumed

A work unit can move to `COMPLETED` only when:

- code is implemented
- support surfaces are updated
- audit/status files are updated
- acceptance criteria are materially satisfied
- verification has been attempted

If something is still missing, leave the work unit open and state what remains.

---

## Completion Bar by Work Unit Type

### Managed Entity Work Unit

Expected completion:

- backend CRUD or intentional limited lifecycle
- list and detail behavior
- create/edit/delete flows where appropriate
- validation and ownership checks
- docs/Postman/script/example updates

### Investigative or Observe Work Unit

Expected completion:

- real filters
- drill-through and context preservation
- detail surfaces
- export or handoff where relevant
- audit matrices updated to reflect new operator path

### FinOps or Governance Cohesion Work Unit

Expected completion:

- scope or attribution is real in backend queries
- related pages link correctly
- detail and export flows preserve the same scope
- docs/Postman/scripts/examples reflect the new scope model

### Redirect or Collapse Work Unit

Expected completion:

- redirect works
- real owner surface is clear
- docs reflect collapse
- no stale audit language claims the retired page is still the owner

---

## Status Rules

Use these work unit statuses:

| Status | Meaning |
|--------|---------|
| `NOT_STARTED` | Defined but untouched |
| `IN_PROGRESS` | Active implementation underway |
| `COMPLETED` | Code and audit files updated, acceptance materially satisfied |
| `VERIFIED` | Re-audited after implementation and confirmed accurate |

Use `COMPLETED` when the implementation pass is done.
Use `VERIFIED` only after a later re-audit confirms the feature still matches the file.

---

## Matrix Update Rules

After implementation, update these files in this order:

1. work unit file
2. owning `GAP-MATRIX.md`
3. owning `COHESION-MATRIX.md`
4. paired `COHESION-MATRIX.md`
5. owning `DELIVERY-STATUS.md`
6. `TODO_ITEMS/FEATURE-STATUS.md`

When updating matrix language:

- prefer precise statements about shipped behavior
- name the actual route or runtime path
- say what is still partial if not fully closed
- avoid vague claims like "better integrated now"

Good phrasing:

- "Billing period detail now preserves `access_group_id` into reconciliation, breakdown, and export flows."
- "Chargeback now supports the `access_group` dimension with budget variance where the budget scope aligns."

Weak phrasing:

- "Financial cohesion improved."
- "This should now be stronger."

---

## Verification Rules

Before closing a work unit, verify what you can.

Preferred checks:

- typecheck
- lint if lightweight and reliable
- JSON parse for changed machine-readable files
- targeted smoke script or example if practical
- route/query contract review where automated verification is unavailable

If a check cannot run:

- say so in the final summary
- do not pretend the work was fully verified

---

## Implementation Heuristics

When choosing between two solutions, prefer the one that:

- strengthens workflow-centered product behavior
- uses real RunLedger primitives like `workspace`, `workflow`, `feature_tag`, `api_key`, and gateway/runtime concepts
- avoids reviving `teams`, `projects`, or `team models`
- closes the full operator loop instead of only adding storage
- improves both runtime truth and audit truth

---

## Minimum Final Checklist

Before calling a work unit complete, confirm:

- backend changed where required
- UI changed where required
- docs updated
- Postman updated
- scripts and/or examples updated where appropriate
- owning matrix files updated
- paired matrix files updated
- feature-status dashboard updated
- work unit status updated
- at least one verification step run

If any item above is still missing, the work unit remains open.

---

## Suggested Work Unit Template Notes

When editing an existing work unit, keep these fields current:

- `Status`
- `Completed`
- cohesion table current state
- completion notes if useful

Recommended completion note format:

- what shipped
- what paired surfaces changed
- what remains partial, if anything

That keeps future re-audits grounded in real implementation history instead of guesswork.
