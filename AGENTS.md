# RunLedger Agent Guide

This file is the canonical repo-level instruction set for any AI development agent working in this repository, including Codex, Claude, Cursor-style agents, Antigravity, and similar systems.

If another tool-specific instruction file exists, treat this file as the product and delivery source of truth for repo work.

## Product Direction

RunLedger is centered on workflows.

Do not introduce new product concepts around teams, projects, or team models.

When touching existing code:

- prefer `workflow`, `feature_tag`, `api_key`, `workspace`, and gateway/runtime concepts
- treat teams, projects, and team models as legacy or cleanup surfaces unless a task explicitly requires removal or migration work
- avoid adding new schema, UI, docs, filters, or analytics dimensions that deepen those legacy concepts

## Core Mental Model

Every feature should strengthen this workflow:

1. Define or identify a workflow.
2. Send traffic through the gateway, SDK, MCP, OTLP, or ingest path.
3. Apply runtime controls and governance.
4. Record runs, model calls, tool calls, outcomes, and cost.
5. Review the workflow in dashboards, governance surfaces, and FinOps surfaces.
6. Improve the workflow through routing, prompts, budgets, evaluations, and policy changes.

New work should make this workflow clearer, more enforceable, and more complete.

## Feature Delivery Standard

When building or changing a feature, do not stop at one layer.

The expected order is:

1. Update the backend first.
2. Update the UI second.
3. Provide complete CRUD where CRUD is appropriate.
4. Review the docs and update them for accuracy and cohesion.
5. Review the Postman collection/assets and update or generate the relevant API coverage.
6. Review the scripts directory and add or update end-to-end simulation coverage.
7. Add or update examples.
8. Ensure the feature is fully finished, not partially implemented.

"Done" does not mean a model, route, or page exists in isolation. "Done" means the backend, UI, docs, Postman assets, scripts, and examples are aligned.

## Backend-First Rule

Backend changes come before UI changes.

For feature work, the agent should:

- implement or update the data model, service logic, router behavior, validation, and enforcement path first
- make sure the feature works in the real runtime path, not only in admin/config surfaces
- verify that the API shape is clean and consistent before building the frontend on top

Avoid UI-only features that sit on incomplete, missing, or decorative backend behavior.

## CRUD Rule

If a feature represents a managed entity, the default expectation is full CRUD across backend and UI.

That usually means:

- backend create, list, get, update, delete or archive endpoints
- UI list/detail/create/edit/delete flows
- validation, empty states, error states, and role-aware access behavior

If CRUD is intentionally not appropriate, the agent should document why in code comments, docs, or the task summary.

## Cohesion Rule

Before finalizing a feature, review whether it is cohesive with the rest of RunLedger.

Check:

- Does it fit the workflow-centered product model?
- Does it align with gateway enforcement, governance, observability, and FinOps where relevant?
- Does it create a duplicate concept or parallel control path?
- Is it enforced in the runtime path if the feature implies enforcement?
- Does it reuse the product's real primitives instead of inventing a new one?

Reject or refactor changes that introduce decorative configuration, disconnected budgets, duplicate policy systems, or UI surfaces with no real enforcement path.

## Legacy Cleanup Rule

Do not expand teams, projects, or team models.

If a task touches those areas, prefer one of these outcomes:

- remove them
- simplify them
- migrate behavior toward workflow-centered primitives
- update naming and docs so they are clearly legacy or transitional

Do not create new dependencies on those concepts.

## Docs Review Rule

After code changes, review docs for any impacted feature area.

This includes:

- README references
- product docs under `docs/`
- architecture or operational docs when behavior changes
- setup instructions when agent/operator workflows change

Docs should describe what actually exists now, not what was planned earlier.

## Postman Rule

After backend API changes:

- review the `postman/` directory
- add or update requests, folders, examples, and generated API assets as needed
- remove stale or unnecessary Postman artifacts tied to deleted or obsolete endpoints

Postman assets should reflect the current API, not abandoned feature branches.

## Scripts Rule

After feature work:

- review `scripts/`
- add or update end-to-end simulation or verification coverage for the feature
- prefer realistic workflow-oriented simulations over isolated seed-only behavior
- avoid leaving demo-only scripts with no assertions when verification is practical

The goal is that a feature can be replayed and demonstrated end-to-end.

## Examples Rule

After feature work:

- add or update examples under `examples/` when the feature affects public usage
- keep examples practical, minimal, and aligned with the current API and workflow model

Examples are part of the completion bar, not optional polish.

## Finish Completely

Do not leave features half-built.

A feature is incomplete if any of these are true:

- backend exists but UI does not
- UI exists but runtime enforcement does not
- routes exist but Postman is stale
- docs still describe old behavior
- scripts do not cover the change
- examples are missing for externally usable functionality
- cleanup of replaced behavior was skipped

Prefer shipping fewer finished features over more half-finished ones.

## Branch And Git Workflow

For implementation work in this repo, the agent should:

1. create a separate branch before making changes
2. keep changes scoped to the task
3. stage only the relevant files
4. leave a clean, reviewable diff with clear intent

Use a branch name that reflects the task.

Do not stage unrelated user changes.

Do not revert unrelated work already in progress in the repository.

## Preferred Decision Heuristics

When choosing between alternatives, prefer the option that:

- strengthens workflow-centric product behavior
- improves runtime enforcement over decorative configuration
- reduces duplicate concepts and parallel systems
- removes legacy surface area
- makes the backend and UI easier to understand together
- improves replayability through docs, Postman, scripts, and examples

## Instruction Priority

If there is tension between speed and completeness, choose completeness.

If there is tension between adding a new abstraction and reusing workflow-centered primitives, reuse the existing primitives.

If there is tension between preserving a legacy teams/projects concept and simplifying toward workflows, simplify toward workflows.
