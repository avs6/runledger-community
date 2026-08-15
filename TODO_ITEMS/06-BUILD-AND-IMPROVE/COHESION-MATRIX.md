# Build & Improve — Cohesion Matrix

Last updated: PENDING AUDIT

This file tracks how Build & Improve features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

This section applies the same matrix structure to `Build & Improve` against the rest of the shipped feature surface.

Current row major feature under audit: `Build & Improve`

### 11.7a Build & Improve x Organization & Access / Gateway & Routing

| Row Major Feature | Row Subfeature | Workspaces | Access groups | API keys | AI hub | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|------------|---------------|----------|--------|-------------------|---------------|------------|----------------|-------------|---------|
| Build & Improve | Playground | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Playground should feel much more like a live gateway-aware experimentation surface over time. |
| Build & Improve | Prompts list | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Prompts already fit the workflow-improvement model, but their gateway/runtime links could be more obvious. |
| Build & Improve | Workflow detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Workflow Detail is one of the strongest candidates for tying together scope, execution, and improvement. |
| Build & Improve | Evaluation studio | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Evaluation Studio already acts as an umbrella, but it still needs a clearer cross-feature ownership story. |
| Build & Improve | Experiments | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Experiments are operationally useful, but the relationship to runtime configuration could still be tighter. |
| Build & Improve | Replay lab | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Replay is useful, but still not as cohesive a first-class feature as the rest of the build suite should become. |
| Build & Improve | Optimization opportunities | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Optimization Opportunities is naturally close to gateway behavior and should remain so. |
| Build & Improve | Optimization simulator | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Optimization Simulator is already a strong bridge between runtime and improvement loops. |
| Build & Improve | Model scorecards | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Model Scorecards already have strong natural cohesion with AI Hub and provider/model surfaces. |

### 11.7b Build & Improve x FinOps / Observe / Self

| Row Major Feature | Row Subfeature | Budgets | Billing periods | Chargeback | Analytics overview | Runs list | Run detail | Request flow | Request explorer | Model usage | Cost and savings | Playground | Workflows list | Evaluation studio | Optimization opportunities | Optimization simulator | Model scorecards | Finding |
|-------------------|----------------|---------|-----------------|------------|--------------------|-----------|------------|--------------|------------------|-------------|------------------|------------|----------------|-------------------|----------------------------|------------------------|------------------|---------|
| Build & Improve | Playground | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Playground should become a stronger live lab that consumes cost, routing, and runtime insights directly. |
| Build & Improve | Prompt detail and versions | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Prompt versioning is strong on its own, but can still gain richer loop-closure with observability and FinOps. |
| Build & Improve | Workflow detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Workflow Detail is one of the clearest "one brick at a time" cohesion surfaces in the whole suite. |
| Build & Improve | Evaluation studio | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Evaluation Studio is strategically important, but still not as consolidated as it should eventually be. |
| Build & Improve | Experiments | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Experiments should become easier to tie to economics and runtime changes. |
| Build & Improve | Replay lab | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Replay is useful but still feels more adjunct than deeply integrated. |
| Build & Improve | Optimization opportunities | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Optimization Opportunities is one of the strongest Build & Improve bridges to FinOps and Observe. |
| Build & Improve | Optimization simulator | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Optimization Simulator is already positioned well as a cross-feature decision tool. |
| Build & Improve | Model scorecards | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Model Scorecards already has one of the clearest internal and cross-feature identities in this family. |
