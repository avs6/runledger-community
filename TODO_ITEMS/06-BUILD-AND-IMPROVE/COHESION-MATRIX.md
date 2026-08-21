# Build & Improve â€” Cohesion Matrix

Last updated: 2026-08-20

This file tracks how Build & Improve features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

This section applies the same matrix structure to `Build & Improve` against the rest of the shipped feature surface.

Current row major feature under audit: `Build & Improve`

### 11.7a Build & Improve x Organization & Access / Gateway & Routing

| Row Major Feature | Row Subfeature | Workspaces | Access groups | API keys | AI hub | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|------------|---------------|----------|--------|-------------------|---------------|------------|----------------|-------------|---------|
| Build & Improve | Playground | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Playground sessions now filter by access_group_id through created_by membership. Access group detail links to playground with identity scope. |
| Build & Improve | Prompts list | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Prompts list is a real workspace-scoped registry surface, and prompt selection ultimately feeds gateway execution by name, but the list itself still does not expose direct model, provider, or AI hub associations. |
| Build & Improve | Prompt detail and versions | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Prompt detail is a strong registry and release surface with versioning, promotion, metrics, and Git sync, but its gateway/model relationship is still indirect through `model_hint` and fetch-by-name runtime use rather than direct provider or control-plane posture. |
| Build & Improve | Agents list | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Agents list now filters by access_group_id and api_key_id through workflow run identity. Access group detail links to agents with identity scope. |
| Build & Improve | Agent detail | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Agent detail reachable from access group identity links. Agent runs list supports access_group_id and api_key_id filtering. |
| Build & Improve | Agent memory | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | Agent memory is a real governed storage and evidence surface, but it sits beside agent execution rather than directly exposing gateway or runtime routing controls. |
| Build & Improve | Workflows list | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Workflows list now filters by access_group_id and api_key_id. Identity detail pages link to workflows with scope. |
| Build & Improve | Workflow detail | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Workflow detail reachable from identity links. Workflow runs carry api_key_id and access_group_id for attribution. |
| Build & Improve | Workflow run detail | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Workflow runs now carry api_key_id and access_group_id. Run lists filter by identity. |
| Build & Improve | Datasets | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Datasets are real workspace-scoped evaluation assets, but they sit more naturally under the evaluation suite than as a standalone build surface and do not have direct gateway or runtime-control relationships. |
| Build & Improve | Evaluation studio | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Scores now filter by access_group_id (through end_user_id) and api_key_id (through AgentRun). Identity detail pages link to evaluations. |
| Build & Improve | Experiments | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Experiments now filter by access_group_id (through created_by) and api_key_id. Identity detail pages link to experiments. |
| Build & Improve | Replay lab | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | Replay experiments now accept access_group_id and api_key_id filters. Identity detail pages link to replay. |
| Build & Improve | Replay experiment detail | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | Replay experiment detail reachable from identity links. Parent experiment list supports identity filters. |
| Build & Improve | Optimization opportunities | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | Flywheel recommendations now accept access_group_id and api_key_id filters. Identity detail pages link to optimization. |
| Build & Improve | Optimization simulator | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | Optimization simulator inherits identity filters from opportunities surface. Identity detail pages link to optimization. |
| Build & Improve | Model scorecards | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Model scorecards now accept access_group_id and api_key_id filters. Identity detail pages link to scorecards. |
| Build & Improve | Vector stores list | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Vector Stores list is a real workspace-scoped catalog for retrieval assets, but it stays mostly isolated from gateway, routing, and observability loops and still lacks stronger in-product management cohesion. |
| Build & Improve | Vector store detail | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Vector store detail is a useful retrieval evidence surface for stats and query history, but it remains only loosely connected to the broader workflow and governance systems and does not expose the full backend action set in product. |
| Build & Improve | Runbooks | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Runbooks sits close to runtime evidence, incident review, and optimization follow-up, but it still acts as a downstream operator artifact rather than a more unified control-and-remediation surface. |

### 11.7b Build & Improve x FinOps / Observe / Self

| Row Major Feature | Row Subfeature | Budgets | Billing periods | Chargeback | Analytics overview | Runs list | Run detail | Request flow | Request explorer | Model usage | Cost and savings | Playground | Workflows list | Evaluation studio | Optimization opportunities | Optimization simulator | Model scorecards | Finding |
|-------------------|----------------|---------|-----------------|------------|--------------------|-----------|------------|--------------|------------------|-------------|------------------|------------|----------------|-------------------|----------------------------|------------------------|------------------|---------|
| Build & Improve | Playground | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Playground should become a stronger live lab that consumes cost, routing, and runtime insights directly. |
| Build & Improve | Prompt detail and versions | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Prompt versioning is strong on its own, but can still gain richer loop-closure with observability and FinOps. |
| Build & Improve | Workflow detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Workflow Detail is one of the clearest "one brick at a time" cohesion surfaces in the whole suite. |
| Build & Improve | Evaluation studio | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Evaluation Studio is strategically important, but still not as consolidated as it should eventually be. |
| Build & Improve | Experiments | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Experiments should become easier to tie to economics and runtime changes. |
| Build & Improve | Replay lab | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Replay is useful but still feels more adjunct than deeply integrated. |
| Build & Improve | Optimization opportunities | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Optimization Opportunities is one of the strongest Build & Improve bridges to FinOps and Observe. |
| Build & Improve | Optimization simulator | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Optimization Simulator is already positioned well as a cross-feature decision tool. |
| Build & Improve | Model scorecards | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Model Scorecards already has one of the clearest internal and cross-feature identities in this family. |
