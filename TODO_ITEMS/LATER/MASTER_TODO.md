# RunLedger — Master TODO

**Compiled:** August 12, 2026
**Sources:** TODO.md (architecture gaps audit), IMPLEMENTATION-PLAN.md (10-phase plan), FEATURE-LIST.md (720 features across 77 pages), UI-Audit.md (navigation audit), FEATURE-COVERAGE-README.md (script normalization & coverage)

**Organization:** Items are ordered by category priority, then by severity within each category.

---

## How to Use This Document

Each item has:
- **ID** — stable reference (e.g., `AG-01`)
- **Severity** — P0 (ship blocker) → P4 (nice to have)
- **Effort** — estimated time for one experienced full-stack engineer
- **Files** — primary files to modify
- **Depends on** — prerequisite items by ID

---

# CROSS-CUTTING OBSERVATIONS

These are architectural observations that cut across multiple TODO items. They explain *why* several items exist and how they relate to each other at the system level.

**Added:** August 12, 2026

---

### Canonical runtime truth hierarchy

Not all product primitives are equally real. Based on the current code, this is the actual status:

| Primitive | Status | Notes |
|---|---|---|
| **Guardrails** | Real and enforceable | Wired into gateway pre/post/during-call checks |
| **Route caps / RPM** | Real and enforceable | Gateway hot path via `check_cost_cap` |
| **Scope-based Budgets** | Real in policy service | Not fully unified into gateway hot path |
| **Projects** | Mostly grouping/metadata | Budget fields are decorative, no enforcement |
| **Team Models** | Partly runtime-adjacent | Conceptually legacy, string-backed `team_name` |
| **Access Group / Project / Team-Model budgets** | Fragmented | Not one system — each stores its own budget field disconnected from the Budget table |

This hierarchy should guide prioritization: items that fix or unify *real* primitives (guardrails, route caps, scope-based budgets) are higher leverage than items that add features to *decorative* primitives (project budgets, team-model budgets). The cleanup items (CL-01 through CL-07) exist to *remove* the decorative primitives, not complete them.

### Budget enforcement is split across two different systems

"Budgets" are not one coherent runtime control today. The gateway hot path calls `check_cost_cap`, not the main `check_budgets` service:
- `routers/gateway.py:488` — cost cap check on non-streaming path
- `routers/gateway.py:629` — cost cap check on streaming path
- `services/gateway_controls.py:88` — cost cap implementation

The scope-based budget engine exists, but is used in policy evaluation instead:
- `services/budgets.py:187` — the real budget check logic
- `services/policies.py:269` — budget enforcement via policy engine, not gateway

**Net:** Route caps and "budget" caps are different enforcement paths. This is why AG-03 (unify 5 budget systems) and AG-04 (wire budgets into gateway hot path) are both needed — fixing one without the other leaves the split intact.

### Guardrails are cohesive in the gateway, not in the broader governance engine

Pre-, post-, and during-call guardrail checks are genuinely wired into gateway traffic:
- `routers/gateway.py:510` — pre-call guardrail evaluation
- `routers/gateway.py:652` — post-call guardrail evaluation
- `routers/gateway.py:664` — during-call guardrail check

But tool/plugin governance currently calls guardrails with the wrong argument shape:
- `services/plugin_runner.py:116` — passes `None` as mode (expects `str`), plain string as texts (expects `list[str]`)

So "guardrails" are cohesive in the gateway, not in the broader governance engine. This is why DF-03 (fix argument types) and AG-20 (wire plugin governance into approvals) are both needed — the gateway story works, but everything adjacent to it is broken or disconnected.

### Projects and Team Models are decorative organizational overlays

Projects and Team Models are not first-class financial or runtime entities. They store budget fields directly in the model:
- `models/projects.py:27` — `budget_usd` column
- `models/projects.py:59` — `TeamModel` with per-model budget

The CRUD/API preserves those fields:
- `routers/projects.py:88` — project creation with budget
- `routers/projects.py:208` — team-model creation

The UI presents them as real controls:
- `apps/web/app/(dashboard)/projects/page.tsx:95,419` — budget fields in project forms
- `apps/web/app/(dashboard)/team-models/page.tsx:49,178` — team model management

But they do not unify with the main Budget table. This is the motivation for CL-01 through CL-07 — these aren't arbitrary cleanups, they're removing controls that *look* functional but *aren't*.

### Team semantics are string-based and leak into routing

`TeamModel` is keyed by free-text `team_name`:
- `models/projects.py:54` — `team_name = sa.Column(sa.String(100))`

Gateway route selection can even fall back to a TeamModel lookup by alias or team_name:
- `services/gateway.py:406` — TeamModel lookup by alias
- `services/gateway.py:422` — TeamModel lookup by team_name

That makes "team" feel real in demos, but it is not a stable product primitive. A typo in team_name silently breaks the lookup. This is why CL-01 (remove free-text team_name) and CL-06 (remove team references from UI) matter — the current state is worse than having no team concept at all, because operators will trust a control that doesn't actually work reliably.

### The UI fracture is FinOps/org vs gateway/governance, not sidebar bloat

The UI story is mostly cohesive at the top level, and the current sidebar is actually the best mental model anchor. The main operator flow is visible in:
- `apps/web/components/layout/Sidebar.tsx:203` — Observe section
- `apps/web/components/layout/Sidebar.tsx:210` — Build & Improve section
- `apps/web/components/layout/Sidebar.tsx:236` — Gateway section
- `apps/web/components/layout/Sidebar.tsx:251` — Governance section

The fracture is not "too many random features" — it is that **FinOps and org-control surfaces don't always land on the same runtime objects as gateway/governance**. Budget pages reference scope types that the gateway doesn't check. Chargeback pages reference dimensions ("team") that don't exist as real entities. Project pages show budget fields that no enforcement path reads. The sidebar reorganization (UI-01) will help, but the deeper fix is making FinOps and gateway agree on what the runtime primitives are (AG-03, AG-04, CL-01 through CL-07).

---

# A. ARCHITECTURE GAPS

These are structural problems in the data model, schema, and system design that prevent the product from delivering on its core value proposition. Fix these first — everything else builds on top.

---

### AG-01 — [REMOVED — see Section G: Teams & Projects Cleanup]
*Originally proposed creating a `teams` table. Decision: Teams and Projects add speculative complexity. The existing primitives (Workspace, API Key, feature_tag) cover the real use cases. See section G for cleanup of the decorative remnants.*

### AG-02 — [REMOVED — see Section G: Teams & Projects Cleanup]
*Originally proposed wiring Projects into AgentRun/billing. Decision: Same as AG-01. If an enterprise customer explicitly demands team-level attribution within a workspace, add it then. See section G for cleanup.*

### AG-03 — Five parallel budget systems that don't communicate [P1]
**Problem:** Five independent budget mechanisms with different enforcement, scoping, and breach tracking:
| System | Scope | Enforcement | Breach Tracking |
|---|---|---|---|
| `Budget` (scope-based) | workspace/user/feature/app | Async Celery (lagging) | Yes |
| `BudgetTier` (API-key) | workspace | Real-time gateway | No |
| `ModelBudget` (per-model) | api_key_id | None | No |
| `Project.budget_usd` | project | None | No |
| `AccessGroup.budget_usd` | access group | None | No |
Plus `Agent.budget_envelope` — a raw number with no FK and no enforcement.
**Fix:** Unify into one budget system. Use `workspace`, `end_user`, `feature_tag`, `app`, and `api_key` as the scope types (not team/project). Remove decorative budget fields from Project, AccessGroup, and Agent (see CL-01 through CL-05). Wire all enforcement through one code path.
**Files:** `models/budgets.py`, `models/budget_tiers.py`, `models/model_budgets.py`, `models/projects.py:27-28`, `models/access_groups.py:22-23`, `models/agents.py:39`, `services/gateway_controls.py`, `services/budgets.py`
**Effort:** 4-5 days
**Depends on:** None

### AG-04 — Workspace budgets not enforced in gateway hot path [P2]
**Problem:** Gateway calls `check_cost_cap` (route/project/tier limits) but never calls `check_budgets` from `services/budgets.py`. The main Budget model with workspace/user/feature scope is only checked by the policies service and Celery metering worker — not for every gateway request. Budget counters update asynchronously (60s lag), creating an over-budget window.
**Fix:** Integrate `check_budgets` into the gateway hot path or consolidate all budget checks into `check_cost_cap`.
**Files:** `routers/gateway.py:488,629`, `services/gateway_controls.py`, `services/budgets.py`
**Effort:** 2-3 days
**Depends on:** AG-03

### AG-05 — 35+ missing foreign key constraints [P1]
**Problem:** At least 35 columns holding UUIDs referencing other tables have no FK constraint. The database cannot enforce referential integrity. Orphan rows are invisible. Cascade deletes don't work.
**Critical missing FKs (financial):** BudgetOverride.budget_id, BudgetBreach.budget_id, ModelBudget.api_key_id, ApiKey.budget_tier_id, UsageSnapshot.billing_period_id
**Critical missing FKs (organizational):** Project.workspace_id, ProjectKey.project_id/api_key_id, TeamModel.workspace_id, AccessGroupMember.group_id/user_id
**Critical missing FKs (operational):** GuardrailEvent/TestCase/Alert.guardrail_rule_id, ProviderCall.workspace_id/span_id, ToolCall.workspace_id, UsageHourly/Daily.workspace_id, WorkflowRun.workflow_id, WorkflowStep.run_id, AgentMemory.agent_id
**Fix:** Single Alembic migration. Validate existing data first (delete orphans or backfill). Add all FKs.
**Files:** All model files listed above
**Effort:** 1 day + data cleanup
**Depends on:** AG-06 (models registered in __init__.py)

### AG-06 — 13 model files not registered in `__init__.py` [P1]
**Problem:** `approvals.py`, `billing.py`, `budgets.py`, `agents.py`, `projects.py`, `playground.py`, `vector_stores.py`, `mcp_registry.py`, `plugins.py`, `hub.py`, `otlp.py`, `evaluators.py`, `outcomes.py` define SQLAlchemy models but are not imported in `models/__init__.py`. Alembic autogenerate cannot see these tables.
**Fix:** Add imports to `models/__init__.py`.
**Files:** `models/__init__.py`
**Effort:** 15 minutes
**Depends on:** None

### AG-07 — Budget/policy `scope_id` accepts arbitrary strings [P2]
**Problem:** Any string/UUID is accepted without validating it references a real workspace, user, or app. You can create a budget for a non-existent scope.
**Fix:** Validate `scope_id` against the appropriate table based on `scope_type` (workspace→workspaces, end_user→users, app→applications, api_key→api_keys) before creating/updating.
**Files:** `models/budgets.py:20-24`, `routers/budgets.py:135-137`, `routers/phase16_deferred.py`
**Effort:** 1 day
**Depends on:** AG-03

### AG-08 — No tenant-level scoping for financial models [P2]
**Problem:** Despite `org_billing_admin` and `org_auditor` roles, no financial or governance model operates at the tenant level. Everything is workspace-scoped. You cannot set org-level budgets, run org-level billing, apply org-level guardrails, or view org-level chargeback.
**Fix:** Add `tenant_id` (nullable FK) to `Budget`, `BillingPeriod`, `AlertRule`. Add aggregation endpoints: `GET /org/budgets/rollup`, `GET /org/billing/summary`.
**Files:** `models/budgets.py`, `models/billing.py`, `models/alerts.py`
**Effort:** 2-3 days
**Depends on:** AG-03

### AG-09 — No connection pooling in gateway — new TLS handshake per request [P1]
**Problem:** Every HTTP call creates a new `httpx.AsyncClient`. At 1000 RPS = 1000 TLS handshakes/second.
**Fix:** Create module-level `_provider_clients: dict[str, httpx.AsyncClient]` registry with connection pooling. Reuse across requests. Add shutdown hook.
**Files:** `services/gateway_providers.py:157,172,254,269,613,633`
**Effort:** 1 day
**Depends on:** None

### AG-10 — Synchronous DB writes in gateway hot path [P1]
**Problem:** A single gateway request triggers 10-15 DB ops (request logging, Kafka delivery, cache store, cost cap aggregations). Cost cap check runs SUM aggregations over `gateway_requests` — gets slower as table grows.
**Fix:** Move request logging to `asyncio.create_task` or task queue. Pre-aggregate cost caps in Redis with periodic DB reconciliation.
**Files:** `services/gateway.py:627-706`, `services/gateway_controls.py:88-236`
**Effort:** 2-3 days
**Depends on:** None

### AG-11 — No circuit breaker — cooldown is insufficient [P2]
**Problem:** Gateway has rudimentary cooldown (set `cooldown_until` on failure, skip route until then) but no half-open state, no failure-count threshold, cooldown writes to DB in hot path, no health probes, `consecutive_health_failures` counter is tracked but never used.
**Fix:** Implement in-memory circuit breaker per route with closed/open/half-open states. Persist state to DB only on transitions.
**Files:** Create `services/circuit_breaker.py`, integrate into `services/gateway.py:822-823,972-975`
**Effort:** 2 days
**Depends on:** None

### AG-12 — Streaming has no fallback and no token counting [P2]
**Problem:** Non-streaming has full fallback chain. Streaming picks one route — if it fails mid-stream, client gets broken SSE. Streaming token counts logged as `None` — billing and analytics blind to streaming usage.
**Fix:** Pre-flight health check before streaming commit. Post-stream token reconciliation via SSE parsing.
**Files:** `routers/gateway.py:470-582`
**Effort:** 2 days
**Depends on:** AG-11

### AG-13 — Chat/completions on wrong rate limit tier [P1]
**Problem:** `/chat/completions` is on `management` tier (60 RPM). Gateway cannot handle more than 1 request/second per key.
**Fix:** Move to `ingest` tier (600 RPM) or create dedicated `gateway` tier.
**Files:** `routers/gateway.py` (rate limit decorator)
**Effort:** 30 minutes
**Depends on:** None

### AG-14 — Financial data in volatile Redis with LRU eviction [P1]
**Problem:** Budget spend counters stored in Redis with `allkeys-lru` eviction and `appendonly: no`. Under memory pressure, budget counters can be evicted. Daily sync is recovery, but eviction between syncs = stale enforcement.
**Fix:** Set `appendonly: yes`, change to `volatile-lru` (only evict TTL keys). Or move budget counters to PostgreSQL with atomic increment.
**Files:** Redis config, `docker-compose.yml`
**Effort:** Half day (Redis config) or 2 days (PostgreSQL migration)
**Depends on:** None

### AG-15 — Single-threaded Celery worker for 25+ tasks [P1]
**Problem:** `--pool=solo` with no concurrency. If ML forecast retraining takes 20 minutes, cost enrichment (60s interval) is delayed by 20 minutes.
**Fix:** Split into two worker profiles: `fast` (cost enrichment, alerting, budget sync) and `slow` (ML, forecasting, retention). Use `--pool=prefork --concurrency=4` for fast.
**Files:** `core/celery_app.py`, `docker-compose.yml`, Helm chart
**Effort:** 1-2 days
**Depends on:** None

### AG-16 — Migrations run on every API startup [P2]
**Problem:** `start.sh` runs `alembic upgrade head` before uvicorn. Multi-replica = race condition.
**Fix:** Gate behind `RUN_MIGRATIONS` env var (default false). Only migration Job runs migrations.
**Files:** `apps/api/scripts/start.sh`
**Effort:** 30 minutes
**Depends on:** None

### AG-17 — No worker/beat health monitoring [P2]
**Problem:** Docker Compose and Helm have health checks for API but none for Celery worker or beat. If worker hangs, nothing detects it.
**Fix:** Add Celery worker liveness check (`inspect ping`) and beat heartbeat (timestamp file + staleness check).
**Files:** `docker-compose.yml`, Helm chart
**Effort:** 1 day
**Depends on:** None

### AG-18 — Core Docker images not built in CI [P2]
**Problem:** CI builds optimization-layer images but NOT core images (`runledger-api`, `runledger-worker`, `runledger-beat`, `runledger-web`). Manual `make build-images` only.
**Fix:** Add core image builds to `.github/workflows/images.yml`.
**Files:** `.github/workflows/images.yml`
**Effort:** Half day
**Depends on:** None

### AG-19 — Plugin execution is a no-op [P1]
**Problem:** `execute_plugin_hooks` queries DB for active plugins, records `PluginExecution` entries with latency tracking, but execution body is just `log.info(...)`. No webhook call, no script execution.
**Fix:** Implement webhook dispatch (HTTP POST to plugin's configured URL). Record response in `PluginExecution`. Propagate blocks.
**Files:** `services/plugin_runner.py`
**Effort:** 1-2 days
**Depends on:** None

### AG-20 — Approval workflow has no persistence [P2]
**Problem:** `govern_and_filter_tool_call` creates an approval ID string but no `ApprovalRequest` table insert, no notification, no mechanism to resolve. Approval exists in UI but plugin governance doesn't use it.
**Fix:** Wire plugin governance violations into existing `Approval` model and router.
**Files:** `services/plugin_runner.py`
**Effort:** 1 day
**Depends on:** AG-19

### AG-21 — Write operations on critical resources require only a valid API key [P0]
**Problem:** 5 routers allow any API key holder to perform admin operations:
- `hub.py` — add/update/remove models, sync providers
- `mcp_registry.py` — register servers, grant permissions, call tools
- `plugins.py` — install/update/uninstall plugins
- `projects.py` — create/update/delete projects and team-models
- `phase16_deferred.py` — manage tags, search-tools, tool-policies, access-groups, response-cache
**Fix:** Add `require_workspace_admin` dependency to all write endpoints.
**Files:** `routers/hub.py`, `routers/mcp_registry.py`, `routers/plugins.py`, `routers/projects.py`, `routers/phase16_deferred.py`
**Effort:** 1 day
**Depends on:** None

### AG-22 — Missing CRUD operations on budgets router [P2]
**Problem:** No GET single budget and no UPDATE budget endpoint. Users cannot view or modify a specific budget after creation.
**Fix:** Add `GET /budgets/{id}` and `PUT /budgets/{id}`.
**Files:** `routers/budgets.py`
**Effort:** 1 day
**Depends on:** None

### AG-23 — Complexity-based routing ignores the trained model [P2]
**Problem:** The `complexity_based` routing strategy uses `total_chars // 4` (crude heuristic). Meanwhile, `services/ml/complexity.py` trains a real GradientBoostingRegressor and persists it — but it goes completely unused in routing.
**Fix:** Wire the trained complexity model into the routing strategy. Fall back to character heuristic only when no trained model is available.
**Files:** `services/routing.py:643-655`, `services/ml/complexity.py`
**Effort:** 1 day
**Depends on:** None

---

# B. FEATURE COHESION

These are problems where features exist but are disconnected, duplicated, or don't work together as a coherent product. The product demos well but falls apart under real operator workflows.

---

### FC-01 — Chargeback report endpoint does not exist [P0]
**Problem:** UI calls `GET /billing/chargeback-report`. API client defines `getChargebackReport`. **No such route exists in any router file.** Chargeback page always returns 404.
**Fix:** Implement `GET /billing/chargeback-report` in `routers/billing.py`. Query actual spend grouped by dimension (workspace, feature_tag, end_user, api_key, model) from `provider_calls`/`agent_runs`. Apply chargeback rules via `apply_chargeback_rules()`. Also add `/billing/chargeback-report/export`.
**Files:** `routers/billing.py` (create endpoint), `services/billing.py:582-608`
**Effort:** 1-2 days
**Depends on:** None

### FC-02 — `apply_chargeback_rules` is dead code [P1]
**Problem:** Function exists in `services/billing.py:582-608` and works correctly, but no router endpoint calls it. Only imported in tests.
**Fix:** Wire into chargeback-report endpoint (FC-01) and `close_billing_period`.
**Files:** `services/billing.py:582-608`
**Effort:** Half day
**Depends on:** FC-01

### FC-03 — Chargeback has no real dimension-based attribution [P2]
**Problem:** `ChargebackRule.dimension` is free-text. Allocation multiplies `net_cost * weight` per rule without grouping actual spend by dimension. Billing breakdown groups by `application_id`/`end_user_id` but doesn't use chargeback rules.
**Fix:** Chargeback allocation must query actual spend grouped by the rule's dimension (workspace, feature_tag, end_user, api_key, model) from `provider_calls`/`agent_runs`, not multiply total cost by static weights. Remove "team" and "project" as dimension options — use workspace and feature_tag instead.
**Files:** `models/billing.py:136`, `services/billing.py:582-608`
**Effort:** 2 days
**Depends on:** FC-01

### FC-04 — Three redundant entry points for experiments [P2]
**Problem:** `/experiments`, `/evaluation` (Evaluation Studio), and `/replay` (Replay Lab) all offer experiment creation using the exact same API functions. Three sidebar items for one workflow.
**Fix:** Make `/evaluation` the canonical home. Add tabs: Datasets, Experiments, Evaluators, Replay. Redirect `/experiments` → `/evaluation?tab=experiments`, `/replay` → `/evaluation?tab=replay`. Remove redundant sidebar entries.
**Files:** `apps/web/app/(dashboard)/evaluation/page.tsx`, sidebar config
**Effort:** 1-2 days
**Depends on:** None

### FC-05 — ~50 dead API functions in api.ts [P2]
**Problem:** `api.ts` exports 406 functions; ~50 never imported. Dead clusters: data warehouse connector (8), invoicing (7), billing webhooks (4), subscription/checkout (2), legacy experiments (5), admin tenant CRUD (7). These represent abandoned feature branches.
**Fix:** Delete dead functions. They mislead due diligence and suggest capabilities that don't exist.
**Files:** `apps/web/lib/api.ts`
**Effort:** 1 day
**Depends on:** None

### FC-06 — MCP Registry vs MCP Servers — two management surfaces [P3]
**Problem:** `/mcp-registry` (full CRUD with tabs for servers/tools/calls/permissions) and `/mcp` (static config generator) overlap. Unclear which is canonical.
**Fix:** Consolidate into one page or clearly differentiate (registry = management, mcp = setup guide).
**Files:** `apps/web/app/(dashboard)/mcp-registry/page.tsx`, `apps/web/app/(dashboard)/mcp/page.tsx`
**Effort:** 1 day
**Depends on:** None

### FC-07 — Evaluations vs Evaluation Studio — overlapping pages [P3]
**Problem:** `/evaluations` (score submission/viewing) and `/evaluation` (full CRUD for datasets, experiments, evaluators) have near-identical names and overlapping functionality.
**Fix:** Consolidate: `/evaluations` becomes "Quick Score" tab within `/evaluation`, or merge score submission into the Evaluation Studio.
**Files:** `apps/web/app/(dashboard)/evaluations/page.tsx`, `apps/web/app/(dashboard)/evaluation/page.tsx`
**Effort:** 1 day
**Depends on:** None

### FC-08 — Tags are standalone — not linked to feature_tag system [P3]
**Problem:** `/tags` manages standalone tag entities that are not linked to the `feature_tag` system used in runs. Two separate tagging mechanisms.
**Fix:** Unify with `feature_tag` or clearly differentiate (organizational tags vs runtime feature tags).
**Files:** `apps/web/app/(dashboard)/tags/page.tsx`
**Effort:** Half day
**Depends on:** None

### FC-09 — Billing is split across two pages [P3]
**Problem:** `/billing` and `/billing-summary` are separate pages that both call `getBillingSummary`.
**Fix:** Merge billing-summary into `/billing` as a "Summary" tab alongside "Periods".
**Files:** `apps/web/app/(dashboard)/billing/page.tsx`, `apps/web/app/(dashboard)/billing-summary/page.tsx`
**Effort:** Half day
**Depends on:** None

### FC-10 — Budget pages over-split in sidebar [P3]
**Problem:** Four sidebar entries for one conceptual area: budgets, budget-tiers, budget-overrides, model-budgets.
**Fix:** Make tiers, overrides, and model budgets tabs/views within the budgets page.
**Files:** `apps/web/app/(dashboard)/budgets/page.tsx` and sub-pages
**Effort:** 1 day
**Depends on:** None

### FC-11 — Playground bypasses gateway — no cost tracking [P3]
**Problem:** Playground makes direct provider calls, bypassing routing policies. Playground usage not tracked as workspace spend.
**Fix:** Route playground requests through the gateway. Track costs as workspace spend.
**Files:** `apps/web/app/(dashboard)/playground/page.tsx`
**Effort:** 1-2 days
**Depends on:** None

### FC-12 — Cost savings categories are heuristic guesses [P3]
**Problem:** When `savings_category` is null, code guesses based on cached tokens or model name containing "llama"/"local"/"ollama".
**Fix:** Populate `savings_category` during cost enrichment based on actual optimization decisions (cache hit, cheaper model routing, local model), not post-hoc name matching.
**Files:** `workers/metering.py`, `apps/web/app/(dashboard)/cost-savings/page.tsx:143-157`
**Effort:** 1 day
**Depends on:** None

### FC-13 — Search Tools and Vector Stores are separate pages [P3]
**Problem:** `/search-tools` and `/vector-stores` manage related retrieval infrastructure but are split across two unconnected pages.
**Fix:** Merge or cross-link.
**Files:** Both page.tsx files
**Effort:** Half day
**Depends on:** None

### FC-14 — Tool Policies `require_approval` action not enforced [P2]
**Problem:** Tool policy can set `action=require_approval` but the approval workflow is not implemented — the value is stored but never checked at runtime.
**Fix:** Wire tool policy approval actions into the Approval model. Block tool execution pending approval.
**Files:** `services/plugin_runner.py`, `models/approvals.py`
**Effort:** 1-2 days
**Depends on:** AG-20

### FC-15 — Chargeback rule missing Update endpoint [P3]
**Problem:** Create, Read, Delete exist but no Update. Users must delete and recreate rules.
**Fix:** Add `PUT /billing/chargeback-rules/{id}`.
**Files:** `routers/billing.py`
**Effort:** Half day
**Depends on:** None

### FC-16 — Governance packs don't enforce — rules can be individually disabled [P3]
**Problem:** Governance packs are templates that create rules, but each rule can be individually disabled, undermining the pack concept.
**Fix:** Add pack-level enforcement (all rules mandatory when pack is active).
**Files:** Governance pack pages and backend
**Effort:** 1 day
**Depends on:** None

---

# C. UI GAPS

These are problems in the user interface — missing pages, broken navigation, inconsistent behavior, and information architecture issues.

---

### UI-01 — 62 sidebar items — extreme information overload [P2]
**Problem:** 7 sections with 62 nav items. Most SaaS products have 15-25. A new user sees 24 ungated items with zero progressive disclosure.
**Fix:** Collapse related items into parent pages with tabs. Target ~28 sidebar items. Recommended groupings per UI-Audit.md:
- Observe: 6 items (merge Request Flow/Explorer, Model Usage/Scorecards into parents)
- Build & Improve: 6 items (merge Datasets/Experiments/Replay into Evaluation tabs)
- Gateway: 4 items
- Safety: 6 items (merge Tool Registry+Search+Policies, merge Approvals+Audit+Dry Run+Governance)
- FinOps: 4 items (budget sub-pages as tabs, billing-summary merged)
- Organization: 6 items
- Platform: 3 items
**Files:** `apps/web/components/layout/Sidebar.tsx`
**Effort:** 2-3 days
**Depends on:** FC-04, FC-09, FC-10

### UI-02 — RBAC is sidebar-only — pages unprotected by URL [P2]
**Problem:** `useRole` is imported in only 22 of ~70+ page files. Sidebar correctly gates sections, but navigating directly to `/chargeback`, `/gateway`, or `/security` via URL loads the page regardless of role.
**Fix:** Add a layout-level RBAC guard in `apps/web/app/(dashboard)/layout.tsx` that checks `useRole` against a route→permission mapping. Show "Access Denied" page.
**Files:** `apps/web/app/(dashboard)/layout.tsx`
**Effort:** 1 day
**Depends on:** None

### UI-03 — Scope bar coverage is inconsistent [P3]
**Problem:** Only 6 pages use `DashboardScopeBar`. The remaining 76 pages rely on implicit API key scoping. No way to switch workspace context without changing API key.
**Fix:** Add scope bar to all analytics/data pages. Add workspace switcher to the app header.
**Files:** Multiple page.tsx files
**Effort:** 2-3 days
**Depends on:** None

### UI-04 — Rate Limits page is a static reference table [P3]
**Problem:** Shows hardcoded tier definitions with no API calls. No way to configure or view actual rate limit state.
**Fix:** Make it a real management page (configure per-key limits, view usage vs limits) or move content to docs.
**Files:** `apps/web/app/(dashboard)/rate-limits/page.tsx`
**Effort:** 1-2 days
**Depends on:** None

### UI-05 — Two pages bypass the api.ts layer [P3]
**Problem:** `organization/page.tsx` and `workspace/page.tsx` use direct `fetch()` calls instead of typed `apiFetch<T>`.
**Fix:** Refactor to use `apiFetch`.
**Files:** `apps/web/app/(dashboard)/organization/page.tsx`, `apps/web/app/(dashboard)/workspace/page.tsx`
**Effort:** 1 day
**Depends on:** None

### UI-06 — No onboarding for non-admin users [P3]
**Problem:** Getting Started page is buried as 12th item in Organization section, gated behind `canAccessApiKeys`. It's a demo seeder, not a user guide.
**Fix:** Detect empty workspace (no runs, no routes). Show a 4-step wizard: copy API key → configure route → send first request → view run.
**Files:** Create `apps/web/components/onboarding/FirstRunWizard.tsx`
**Effort:** 2 days
**Depends on:** None

### UI-07 — Naming inconsistencies across the frontend [P3]
**Problem:** Four terms for organizational hierarchy: "workspace" (461 occurrences across 49 files), "organization" (94 across 24), "team" (57 across 13), "tenant" (0 in .tsx, leaks via API types). Sidebar reads "Teams / Workspaces" — presenting them as interchangeable.
**Fix:** Standardize: Frontend uses "Organization" (top-level) and "Team" (group within org). API responses use `organization` and `team`. Remove "workspace" from user-visible labels.
**Files:** Multiple .tsx files across frontend
**Effort:** 1-2 days
**Depends on:** None

### UI-08 — Several shipped pages missing from sidebar [P3]
**Problem:** Routes exist but are not in the sidebar navigation: `access-groups`, `response-cache`, `search-tools`, `tags`, `tool-policies`, `security`.
**Fix:** Add to sidebar under appropriate sections (per UI-Audit.md recommendations).
**Files:** `apps/web/components/layout/Sidebar.tsx`
**Effort:** Half day
**Depends on:** None

### UI-09 — Guardrails not surfaced as first-class product area [P3]
**Problem:** Guardrails exist in backend and runtime path but have no major sidebar entry. Product undersells an implemented capability.
**Fix:** Add Guardrails as a prominent sidebar entry under Safety & Governance.
**Files:** Sidebar config
**Effort:** 30 minutes
**Depends on:** None

### UI-10 — Chargeback sidebar visibility inconsistent with backend permissions [P3]
**Problem:** Sidebar shows Chargeback to workspace admins, but billing API requires org-level permissions. Users see error toasts.
**Fix:** Only surface Chargeback where org-level permissions exist. Show proper access-denied state.
**Files:** Sidebar config, chargeback page
**Effort:** Half day
**Depends on:** UI-02

### UI-11 — Org-facing ecosystem pages hidden behind platform-only navigation [P3]
**Problem:** `integrations`, `otlp`, `mcp-registry`, `plugins`, `ai-hub` exist but only platform admins can reach them via sidebar.
**Fix:** Expose org-usable ecosystem pages to org admins through the main sidebar.
**Files:** Sidebar config
**Effort:** Half day
**Depends on:** None

### UI-12 — Integration health cards show "Planned" for shipped features [P3]
**Problem:** Several integration cards show `Planned` status even though the product ships real UI/API for them (Email/SMTP, S3 Backup, LiteLLM guidance, LangGraph guidance, REST webhook).
**Fix:** Mark shipped integrations as `Available`. Reserve `Planned` for truly unimplemented work.
**Files:** `apps/web/app/(dashboard)/integrations/page.tsx`
**Effort:** Half day
**Depends on:** None

### UI-13 — Client-side CSV/JSON exports will fail on large datasets [P3]
**Problem:** Runs, Analytics, Billing Summary, and Chargeback all use client-side export (build entire dataset in browser memory, generate file). Will crash on large datasets.
**Fix:** Add server-side streaming export endpoints. Download via server-generated file.
**Files:** Multiple page.tsx files, add export endpoints to corresponding routers
**Effort:** 2-3 days
**Depends on:** None

### UI-14 — No feature_tag or api_key dimensions across analytics pages [P3]
**Problem:** Dashboard, Runs, Sessions, Analytics, Outcomes, Engineering, Cost Savings, Billing Summary — limited filtering. Workspace scope exists but no breakdown by feature_tag (workflow/agent identity) or api_key (ownership).
**Fix:** Add feature_tag and api_key filters to DashboardScopeBar and all analytics pages. These are the real attribution dimensions — feature_tag identifies what workflow/agent generated the cost, api_key identifies who owns it.
**Files:** Multiple page.tsx files, DashboardScopeBar component
**Effort:** 2-3 days
**Depends on:** None

---

# D. DEFECTS

These are bugs that will crash, silently fail, or produce incorrect results in production.

---

### DF-01 — `_period_key` NameError in metering worker [P0]
**Problem:** `workers/metering.py:161` calls `_period_key()` which is never imported. Budget threshold Kafka events silently crash when any budget hits 80%.
**Fix:** Add `from runledger_api.services.budgets import _period_key` to imports.
**Files:** `workers/metering.py:161`
**Effort:** 5 minutes
**Depends on:** None

### DF-02 — `ProviderSyncRequest(BaseModel)` NameError in hub.py [P0]
**Problem:** `ProviderSyncRequest` at module scope (line 147) inherits `BaseModel`, which is only imported inside a function body (line 179). Module import crash — entire hub router fails to load.
**Fix:** Move `from pydantic import BaseModel` to top-level imports.
**Files:** `routers/hub.py:147,179`
**Effort:** 5 minutes
**Depends on:** None

### DF-03 — `govern_and_filter_tool_call` passes wrong argument types [P0]
**Problem:** Passes `None` as mode (expects `str`) and plain string as texts (expects `list[str]`). Broad `except` swallows the error, defaulting to "allow" — guardrail evaluation silently fails for all tool governance.
**Fix:** `evaluate_guardrails(db, workspace_id, "tool_call", [arg_str])`
**Files:** `services/plugin_runner.py`
**Effort:** 5 minutes
**Depends on:** None

### DF-04 — Guardrail sandbox `exec()` is trivially bypassable [P0]
**Problem:** Custom guardrail logic runs via `exec()` with a regex blocklist. Proven bypass vectors: string concatenation (`"__imp" + "ort__"`), getattr via builtins, `re` module traversal, `chr()` reconstruction, no timeout enforcement (`timeout_ms` unused), fails open on error (returns `allow`).
**Fix:** Run custom guardrail logic in isolated subprocess with `seccomp` or `RestrictedPython`. Add `signal.alarm` timeout. Change fail mode to `deny`.
**Files:** `services/guardrails.py:100-173`
**Effort:** 2-3 days
**Depends on:** None

### DF-05 — Ledger signing keys stored in plaintext in database [P0]
**Problem:** `models/ledger.py:29` stores `key_value` as `sa.Text`. Anyone with DB read access can forge ledger snapshots.
**Fix:** Encrypt with Fernet/master key from env/vault. Decrypt at use time only.
**Files:** `models/ledger.py:29`, `services/ledger.py:52`
**Effort:** 1 day
**Depends on:** None

### DF-06 — Plaintext passwords and API keys sent via email [P0]
**Problem:** `services/email.py:124-189` embeds raw password and API key in both plaintext and HTML email body. Email archives become credential dumps.
**Fix:** Never transmit passwords via email. Use one-time reset link. Show API keys only in UI after creation.
**Files:** `services/email.py:124-189`
**Effort:** 1 day
**Depends on:** None

### DF-07 — Hardcoded default secrets everywhere [P0]
**Problem:** `POSTGRES_PASSWORD=runledger`, `SECRET_KEY=change-me-in-production-32chars`, `ADMIN_SECRET=runledger-admin`, Letta `letta` (hardcoded, no env override), MinIO `runledger/runledgerminio`, default admin `admin@runledger.local / runledger`, Redis with no auth.
**Fix:** Remove default values. Require env vars. Add startup validation rejecting known defaults. Configure Redis `requirepass`.
**Files:** `docker-compose.yml`, `.env.example`, `scripts/start.sh`, `core/config.py`
**Effort:** 1 day
**Depends on:** None

### DF-08 — OIDC algorithm confusion vulnerability [P1]
**Problem:** Token verification accepts whatever algorithm the token header claims: `alg = header.get("alg", "RS256")`. Attacker can set `alg: HS256` and sign with public key material.
**Fix:** Hardcode `algorithms=["RS256", "RS384", "RS512"]`. Never trust the token's `alg`.
**Files:** `services/security.py:72-88`
**Effort:** 30 minutes
**Depends on:** None

### DF-09 — API key hashing without salt [P1]
**Problem:** SHA-256 with no salt. While keys have high entropy, identical keys produce identical hashes.
**Fix:** Use HMAC-SHA256 with server-side pepper.
**Files:** `services/auth.py:22-28`
**Effort:** Half day
**Depends on:** None

### DF-10 — No encryption for provider API keys [P1]
**Problem:** Zero encryption layer anywhere. All provider keys as plaintext env vars. `GatewayPassThroughEndpoint.auth_config` likely stores credentials inline. In multi-tenant: all tenants share process env.
**Fix:** Implement envelope encryption. Use KMS/Vault for provider key management.
**Files:** `services/gateway_providers.py:118-123,209-219,415-428`
**Effort:** 2-3 days
**Depends on:** None

### DF-11 — CORS allows credentials with wildcard methods/headers [P2]
**Problem:** `allow_credentials=True` with `allow_methods=["*"]` and `allow_headers=["*"]`. XSS on an allowed origin enables arbitrary authenticated requests.
**Fix:** Restrict to specific methods (`GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`) and specific headers.
**Files:** `main.py:83-89`
**Effort:** 30 minutes
**Depends on:** None

### DF-12 — No tenant isolation middleware [P2]
**Problem:** Isolation relies on developers manually adding `workspace_id` filters to every query. No RLS, no middleware guard. Single omitted filter = cross-tenant data leak.
**Fix:** Implement PostgreSQL RLS or SQLAlchemy query modifier auto-injecting `workspace_id` filters.
**Files:** Create middleware, modify session setup
**Effort:** 2 days
**Depends on:** None

### DF-13 — IP ACL default-allow with no rules [P2]
**Problem:** When no rules match, function returns without blocking (default-allow). If `client_ip` is `None`, check skipped entirely. `X-Forwarded-For` trusted without validation.
**Fix:** Default-deny when ACL is enabled. Validate `X-Forwarded-For` against trusted proxies. Never skip when IP is None.
**Files:** `services/security.py:148-149,121,106-109`
**Effort:** Half day
**Depends on:** None

### DF-14 — Audit logs are not tamper-proof [P2]
**Problem:** Regular PostgreSQL rows with no hash chain, no WORM storage. `created_at` uses Python `default` (not `server_default`) — timestamps spoofable.
**Fix:** Add `previous_hash` column with hash chain. Use `server_default=func.now()`. Consider append-only table or external log sink.
**Files:** `models/audit.py`
**Effort:** 1-2 days
**Depends on:** None

### DF-15 — Guardrail bypass flag on workspace model [P3]
**Problem:** `models/tenant.py:112` — `guardrail_bypass: bool` allows workspace admin to disable all guardrails with no platform approval and no audit event.
**Fix:** Require platform admin approval. Generate audit event.
**Files:** `models/tenant.py:112`
**Effort:** Half day
**Depends on:** None

### DF-16 — Retry does not honor provider Retry-After header [P3]
**Problem:** Gateway retries with exponential backoff capped at 4s. Provider 429s often have `Retry-After` of 30-60s, which is ignored.
**Fix:** Parse `Retry-After` header. Use `max(backoff, retry_after)`.
**Files:** `services/gateway.py:976-978`
**Effort:** Half day
**Depends on:** None

### DF-17 — Bedrock streaming is fake-streamed [P3]
**Problem:** Bedrock adapter collects ALL chunks synchronously via `asyncio.to_thread`, then yields. Time-to-first-token = total generation time.
**Fix:** Use async Bedrock SDK or `invoke_model_with_response_stream`.
**Files:** `services/gateway_providers.py:452-476`
**Effort:** 1-2 days
**Depends on:** None

---

# E. GOOD TO HAVE

Features that would differentiate the product but don't block adoption. These should be prioritized after categories A-D are addressed.

---

### GH-01 — No integration tests — everything is mocked [P1]
**Problem:** 47 test files exist, all database/Redis interactions mocked. No test exercises a real DB query or Redis operation. FK violations, query performance, migration correctness are invisible.
**Fix:** Add `docker-compose.test.yml` with Postgres+Redis. Create `tests/integration/` for critical paths: ingest → cost enrichment → budget check → billing close → chargeback.
**Effort:** 3-4 days
**Depends on:** None

### GH-02 — No test coverage measurement [P2]
**Problem:** No `pytest-cov`, no `.coveragerc`, no coverage gate in CI. Coverage silently degrades.
**Fix:** Add `pytest-cov` with `--cov-fail-under=40`. Ratchet up over time.
**Effort:** 1 day
**Depends on:** None

### GH-03 — No frontend tests [P3]
**Problem:** 82-page frontend with zero tests — no component tests, no E2E (Playwright/Cypress), no visual regression.
**Fix:** Add Playwright E2E for 5 critical paths: login, create budget, configure gateway route, view runs, generate chargeback report.
**Effort:** 2-3 days
**Depends on:** None

### GH-04 — No load or performance testing [P2]
**Problem:** Basic benchmark exists but no pass/fail thresholds. No Locust, k6, or Artillery config. For a gateway product, this is a notable gap.
**Fix:** Add k6 or Locust load test with baseline thresholds. Run in CI on schedule.
**Effort:** 2-3 days
**Depends on:** None

### GH-05 — PII scrubbing covers only 4 US-centric patterns [P3]
**Problem:** Detects only email, SSN, credit card, phone. Misses names, addresses, DOB, passport, drivers license, IP, geolocation, biometric, non-US formats. Insufficient for GDPR.
**Fix:** Integrate Microsoft Presidio or expand patterns significantly.
**Files:** `services/scrubbing.py`
**Effort:** 2-3 days
**Depends on:** None

### GH-06 — Forecasting uses in-sample model selection [P3]
**Problem:** Runs 4 methods, picks lowest in-sample MAPE. No out-of-sample validation. ARIMA grid search prone to overfitting on short series.
**Fix:** Use walk-forward validation or train/test split.
**Files:** `services/ml/forecast.py:315`
**Effort:** 1 day
**Depends on:** None

### GH-07 — Anomaly detection thresholds are static [P3]
**Problem:** Z-score (3.0) and EWMA (2.5 sigma) thresholds are global constants. Adaptive alerts module generates threshold suggestions but doesn't auto-apply. Different workspaces = different false positive rates.
**Fix:** Auto-tune per workspace or allow workspace-level threshold configuration.
**Files:** `services/ml/adaptive_alerts.py`
**Effort:** 1-2 days
**Depends on:** None

### GH-08 — 21-container full stack is operationally prohibitive [P3]
**Problem:** Full deployment requires 21+ containers. Optimization-layer services are genuinely optional (fail-open) but documentation doesn't make this clear.
**Fix:** Document minimal (5 containers), recommended (10), and full (21) deployment profiles with trade-offs.
**Files:** `docker-compose.yml`, documentation
**Effort:** 1 day
**Depends on:** None

### GH-09 — No alert acknowledgment/escalation workflow [P3]
**Problem:** Monitoring page shows alert firings but no way to acknowledge, escalate, or integrate with PagerDuty/OpsGenie.
**Fix:** Add alert acknowledgment state machine. Integrate with external incident tools via webhooks.
**Files:** Monitoring page, alert backend
**Effort:** 2-3 days
**Depends on:** None

### GH-10 — No A/B test result analysis UI for gateway [P3]
**Problem:** Gateway supports A/B test routing strategy but no UI to view experiment results, significance, or make promotion decisions.
**Fix:** Add A/B test results tab to gateway page with z-test significance display.
**Files:** `apps/web/app/(dashboard)/gateway/page.tsx`
**Effort:** 1-2 days
**Depends on:** None

### GH-11 — No canary auto-rollback [P3]
**Problem:** Canary routing strategy has no automatic rollback on elevated error rates.
**Fix:** Add configurable error rate threshold. Auto-revert to previous routing weights when exceeded.
**Files:** `services/routing.py`, `services/gateway.py`
**Effort:** 1-2 days
**Depends on:** None

### GH-12 — Evaluator/policy config is raw JSON [P3]
**Problem:** Evaluator config, gateway policy conditions, and tool policy conditions are all raw JSON textareas. Error-prone for operators.
**Fix:** Build config builder UI with validated fields for each type.
**Files:** Multiple page.tsx files
**Effort:** 3-5 days
**Depends on:** None

### GH-13 — No document upload or query testing for vector stores [P3]
**Problem:** Vector stores page allows CRUD but no document upload and no search/query testing interface.
**Fix:** Add document upload UI and test query interface with similarity results.
**Files:** `apps/web/app/(dashboard)/vector-stores/page.tsx`
**Effort:** 2 days
**Depends on:** None

### GH-14 — No SSO/SAML/MFA configuration [P4]
**Problem:** Organization and security pages have no SSO, SAML, or MFA configuration. User creation is password-based only.
**Fix:** Add SSO/SAML config UI. Add email invitation flow. Add MFA setup.
**Files:** Organization page, security page, auth services
**Effort:** 5+ days
**Depends on:** None

### GH-15 — No SIEM log forwarding [P4]
**Problem:** Audit logs stay in PostgreSQL. No forwarding to Splunk, Datadog, or other SIEM tools.
**Fix:** Add SIEM forwarding configuration (target URL, format, auth).
**Files:** Audit service, settings page
**Effort:** 2-3 days
**Depends on:** DF-14

### GH-16 — Org creation and deletion need refinement [P4]
**Problem:** Org creation requires admin password (no invitation). Plan changes have no billing implications. Org deletion is permanent with no soft-delete.
**Fix:** Add email invitation. Wire plan changes to billing. Implement soft-delete with 30-day recovery window.
**Files:** `apps/web/app/(dashboard)/organizations/page.tsx`, org backend
**Effort:** 3-4 days
**Depends on:** None

---

# F. SIMULATORS & SCRIPTS

Demo tooling, scenario scripts, benchmarks, and testing utilities.

---

### SS-01 — Scenario scripts have zero assertions [P2]
**Problem:** Scripts under `scripts/scenarios/hosted/` and `scripts/scenarios/ollama/` are purely data generators. All fire-and-forget API calls with no assertions on return values, no status code checks, no validation.
**Fix:** Either add assertions (making them integration tests) or explicitly label as demo-only tooling.
**Files:** `scripts/scenarios/hosted/*.py`, `scripts/scenarios/ollama/*.py`
**Effort:** 2-3 days
**Depends on:** None

### SS-02 — Demo mode creates data in production tables [P3]
**Problem:** Onboarding demo seeder creates sample data that persists in production tables with no distinction flag.
**Fix:** Add `is_demo` boolean flag to demo-created rows. Add cleanup that targets only demo data.
**Files:** `services/demo_mode.py`, relevant model files
**Effort:** 1-2 days
**Depends on:** None

### SS-03 — Optimization simulator uses static cost tables [P3]
**Problem:** Simulator uses hardcoded pricing, not live data from provider profiles.
**Fix:** Pull live pricing from provider profiles. Make simulation results reflect actual current costs.
**Files:** `apps/web/app/(dashboard)/optimization-simulator/page.tsx`
**Effort:** 1 day
**Depends on:** None

### SS-04 — Benchmark script has no pass/fail thresholds [P3]
**Problem:** `scripts/bench/run_benchmark.py` measures p50/p95/p99 and throughput but has no baseline assertions.
**Fix:** Add configurable pass/fail thresholds. Return non-zero exit code on failure. Run in CI.
**Files:** `scripts/bench/run_benchmark.py`
**Effort:** Half day
**Depends on:** None

### SS-05 — Replay Lab doesn't capture tool call side effects [P3]
**Problem:** Replaying a run re-executes LLM calls but doesn't mock/capture tool call side effects. Replay may produce different results if tools have changed.
**Fix:** Record tool call inputs/outputs during original run. Mock tool calls during replay.
**Files:** Replay lab backend
**Effort:** 2-3 days
**Depends on:** None

### SS-06 — Policy dry run tests individual policies, not full pipeline [P3]
**Problem:** Tests guardrails, routing, budget, and rate limits individually but not the complete request lifecycle.
**Fix:** Add full pipeline simulation mode showing the complete request path through all stages.
**Files:** `apps/web/app/(dashboard)/policy-dry-run/page.tsx`, backend simulation endpoint
**Effort:** 2-3 days
**Depends on:** None

---

# G. TEAMS & PROJECTS CLEANUP

The codebase introduced Teams and Projects as organizational primitives but never wired them into the systems that matter (budgets, billing, chargeback, analytics). Rather than completing that integration (which adds speculative complexity), clean up the decorative remnants. The existing primitives — Workspace (boundary), API Key (ownership), feature_tag (workflow identity) — cover the real use cases.

---

### CL-01 — Remove `team_name` free-text strings from models [P2]
**Problem:** `TeamModel.team_name`, `IpAclRule.team_name`, `ChargebackRule` "team" dimension, and `ApiKey.owner_reference` when `ownership_type=team` all store free-text team strings that reference nothing. These create the illusion of team support without delivering it.
**Fix:** Remove `team_name` from `IpAclRule` (scope IP rules to workspace instead). Remove "team" as a chargeback dimension option (use workspace and feature_tag). Keep `TeamModel.team_name` temporarily as a display label but rename to `label` and document it's cosmetic. Remove `team` from `ApiKey.ownership_type` enum — keys are owned by users, service accounts, or the org.
**Files:** `models/security.py:106`, `models/billing.py:136`, `models/tenant.py:174-177`, `models/projects.py:54`
**Effort:** 1-2 days
**Depends on:** None

### CL-02 — Remove decorative `Project.budget_usd` and `Project.budget_period` [P2]
**Problem:** Project has `budget_usd` and `budget_period` columns that are completely disconnected from the budget system. No enforcement, no breach tracking, no integration with billing. Operators set a budget and assume it works.
**Fix:** Remove `budget_usd` and `budget_period` from the `Project` model. If a project needs a budget, the operator creates a real `Budget` row scoped to `feature_tag` or `api_key` (the keys assigned to that project). Update the Projects UI form to remove the budget fields and link to the Budgets page instead.
**Files:** `models/projects.py:27-28`, `routers/projects.py`, `apps/web/app/(dashboard)/projects/page.tsx`
**Effort:** 1 day
**Depends on:** None

### CL-03 — Remove decorative `AccessGroup.budget_usd` [P2]
**Problem:** Same as CL-02 but for Access Groups. Budget value stored with no enforcement.
**Fix:** Remove `budget_usd` from `AccessGroup` model. Update the Access Groups UI to remove the budget field and link to Budgets page.
**Files:** `models/access_groups.py:22-23`, `apps/web/app/(dashboard)/access-groups/page.tsx`
**Effort:** Half day
**Depends on:** None

### CL-04 — Remove decorative `Agent.budget_envelope` [P2]
**Problem:** Raw number field with no FK to budgets and no enforcement. Agent "budgets" are fiction.
**Fix:** Remove `budget_envelope` from the `Agent` model. Update Agent registration form to remove the field. If agents need spend limits, create a real `Budget` scoped to the `feature_tag` the agent uses.
**Files:** `models/agents.py:39`, `apps/web/app/(dashboard)/agents/page.tsx`
**Effort:** Half day
**Depends on:** None

### CL-05 — Simplify Project to a lightweight grouping entity [P3]
**Problem:** Project tries to be an organizational primitive but is disconnected from everything. `ProjectKey` join table has no FK constraints. Project appears in dashboards but provides no real filtering or attribution.
**Fix:** Redefine Project as a simple metadata/grouping label: name, description, workspace_id (with FK), and assigned API keys (with proper FKs on ProjectKey). Remove budget fields (CL-02). Remove team dropdown (use workspace as the boundary). Project becomes a way to organize API keys and label work — not a financial or governance entity.
**Files:** `models/projects.py`, `routers/projects.py`, `apps/web/app/(dashboard)/projects/page.tsx`
**Effort:** 1-2 days
**Depends on:** CL-02

### CL-06 — Remove "team" references from UI labels and filters [P3]
**Problem:** Cost Savings has "Team" dimension toggle. Engineering has "Cost by Team" chart. Request Flow has "Team cost flow" mode. Chargeback has "team" dimension. All reference free-text team strings that mean nothing consistent.
**Fix:** Replace "Team" with "Workspace" in dimension toggles and chart labels. Remove "Team cost flow" mode from Request Flow (or rename to "Workspace cost flow"). Update chargeback dimension list to remove "team".
**Files:** `apps/web/app/(dashboard)/cost-savings/page.tsx`, `apps/web/app/(dashboard)/engineering/page.tsx`, `apps/web/app/(dashboard)/request-flow/page.tsx`, `apps/web/app/(dashboard)/chargeback/page.tsx`
**Effort:** 1 day
**Depends on:** CL-01

### CL-07 — Rename "Team Models" to "Model Allowlist" or "Approved Models" [P3]
**Problem:** The "Team Models" page manages which models a workspace can use, with per-model budgets and GDPR opt-out. The name implies team-level scoping that doesn't exist. It's really a workspace-level model approval list.
**Fix:** Rename to "Approved Models" or "Model Allowlist". Update sidebar label, page title, and API route references. Keep the `team_name` field as a cosmetic `label` (CL-01).
**Files:** `apps/web/app/(dashboard)/team-models/page.tsx`, sidebar config, `routers/projects.py`
**Effort:** Half day
**Depends on:** CL-01

---

# H. IMPLEMENTATION PLAN

This section captures the phased implementation plan from IMPLEMENTATION-PLAN.md. Each phase references items from sections A-G above.

---

## Phase 0 — Hotfixes (Day 1-2)

Runtime bugs that will crash or silently fail in production. Zero dependencies. Ship immediately.

- **DF-01** — Fix `_period_key` NameError in metering worker (5 min)
- **DF-02** — Fix `ProviderSyncRequest` NameError in hub.py (5 min)
- **DF-03** — Fix `govern_and_filter_tool_call` argument types (5 min)
- **AG-06** — Register 13 missing model files in `__init__.py` (15 min)

## Phase 1 — Foundation: Budget Unification & FK Constraints (Week 1-2)

- **AG-03** — Unify 5 budget systems into one (4-5 days)
- **AG-05** — Add 35+ missing FK constraints via Alembic migration (1 day + data cleanup)
- **CL-01 through CL-04** — Remove decorative team/project/budget fields (2-3 days)
- **AG-07** — Validate budget/policy scope_ids (1 day)

## Phase 2 — Fix the FinOps Chain End-to-End (Week 2-3)

- **FC-01** — Implement missing `/billing/chargeback-report` endpoint (1-2 days)
- **FC-02** — Wire `apply_chargeback_rules` into period close (half day)
- **FC-03** — Add dimension-based chargeback attribution from real spend data (2 days)
- **FC-15** — Add chargeback rule update endpoint (half day)
- **FC-12** — Fix cost savings category attribution (1 day)
- **AG-22** — Add missing budget CRUD endpoints (1 day)

## Phase 3 — Gateway Production Hardening (Week 3-4)

- **AG-09** — Add connection pooling to provider clients (1 day)
- **AG-10** — Move gateway request logging to background tasks (2-3 days)
- **AG-13** — Fix rate limit tier for chat completions (30 min)
- **AG-11** — Implement circuit breaker with half-open state (2 days)
- **AG-12** — Add streaming fallback and token reconciliation (2 days)
- **DF-16** — Honor provider Retry-After headers (half day)

## Phase 4 — Product Cohesion and UI Cleanup (Week 4-5)

- **UI-01** — Collapse sidebar from 62 to ~28 items (2-3 days)
- **FC-04** — Consolidate experiment entry points (1-2 days)
- **FC-09** — Consolidate billing pages (half day)
- **FC-10** — Consolidate budget pages (1 day)
- **UI-02** — Add layout-level RBAC guard (1 day)
- **FC-05** — Remove dead API functions (1 day)
- **UI-07** — Standardize naming (1-2 days)
- **UI-06** — Create first-run onboarding (2 days)
- **CL-05 through CL-07** — Simplify Project, clean up team UI references (2-3 days)
- **UI-08** — Add missing pages to sidebar (half day)
- **UI-09** — Add Guardrails to sidebar (30 min)

## Phase 5 — Infrastructure and Ops Hardening (Week 5-6)

- **AG-14** — Fix Redis configuration for budget data durability (half day – 2 days)
- **AG-15** — Fix Celery worker concurrency (1-2 days)
- **AG-16** — Fix migration race condition (30 min)
- **AG-17** — Add worker/beat health monitoring (1 day)
- **AG-18** — Add core images to CI (half day)
- **GH-02** — Add test coverage measurement (1 day)
- **AG-08** — Add tenant-level scoping to financial models (2-3 days)

## Phase 6 — Plugin System Completion (Week 6)

- **AG-19** — Implement real plugin webhook dispatch (1-2 days)
- **AG-20** — Wire plugin governance into approvals system (1 day)
- **FC-14** — Wire tool policy approval actions into Approval model (1-2 days)

## Phase 7 — Authorization Fixes (Week 6-7)

- **AG-21** — Add admin requirements to write endpoints (1 day)

## Phase 8 — Testing (Week 7-8)

- **GH-01** — Add integration tests (3-4 days)
- **GH-03** — Add E2E tests for critical frontend paths (2-3 days)

## Phase 9 — Security Hardening (Week 8-10)

- **DF-04** — Replace guardrail `exec()` sandbox (2-3 days)
- **DF-07** — Remove all hardcoded default secrets (1 day)
- **DF-06** — Stop emailing plaintext credentials (1 day)
- **DF-05** — Encrypt ledger signing keys (1 day)
- **DF-08** — Fix OIDC algorithm confusion (30 min)
- **DF-12** — Add tenant isolation middleware (2 days)
- **DF-14** — Make audit logs tamper-resistant (1-2 days)
- **DF-11** — Restrict CORS methods/headers (30 min)
- **DF-13** — Fix IP ACL to default-deny (half day)
- **DF-09** — Add salt/pepper to API key hashing (half day)
- **DF-10** — Encrypt provider API keys at rest (2-3 days)
- **GH-05** — Expand PII scrubbing (2-3 days)

---

# I. UI AUDIT — NAVIGATION & INFORMATION ARCHITECTURE

This section captures the complete sidebar audit and recommended information architecture from UI-Audit.md. These findings inform UI-01 through UI-14 above.

---

## Current Sidebar Audit

### Audit Findings

1. **Several shipped pages are missing from the sidebar:** `access-groups`, `response-cache`, `search-tools`, `tags`, `tool-policies`, `security`. Users cannot discover these features through the product UI.

2. **Guardrails are implemented but not surfaced as a first-class product area:** Backend router `/guardrails`, gateway enforcement in the runtime path, scenario coverage in `scripts/scenarios/ollama/05_guardrails.py`, lab coverage in `scripts/scenarios/labs/part9_guardrails.md` — but no dedicated dashboard route or major sidebar entry.

3. **Budget surfaces are over-split:** `budgets`, `budget-tiers`, `budget-overrides`, and `model-budgets` are all part of one conceptual product area. The Finance section feels more complex than necessary.

4. **Billing is split awkwardly:** `/billing` and `/billing-summary` should be one product area.

5. **Org structure items are grouped incorrectly:** `projects` and `team-models` sit inside `Ecosystem` but behave more like organization topology and ownership controls.

6. **Rate limits are grouped as Finance but behave like runtime controls:** `rate-limits` should be under Gateway and Routing.

7. **Naming is inconsistent:** `evaluation` and `evaluations` both appear. `organization`, `organizations`, and `workspace` use different plurality. Product alternates between `workspace` and `team` semantics.

8. **Current sidebar reflects implementation order more than operator workflow:** Current sections (Workspace, Improve, Control Plane, Finance, Ecosystem, Governance, Organization, Platform) don't consistently match how operators think.

### Org-Facing Ecosystem Pages Hidden Behind Platform Navigation (Finding 9)

The following pages existed but only platform admins could reach them naturally from the sidebar: `integrations`, `otlp`, `mcp-registry`, `plugins`, `ai-hub`. Org admins and org managers could have valid backend access but not discover the feature.

### Integrations Inventory Stale (Finding 10)

Several cards in the Integrations experience still appeared as `Planned` even though the product already ships real UI or API paths: Email/SMTP, S3/MinIO Backup, LiteLLM/Open WebUI/OpenHands guidance, LangGraph integration guidance, Generic REST webhook ingest.

### Chargeback Navigation/Permissions Inconsistent (Finding 11)

The sidebar exposed `Chargeback` to workspace admins, but the billing API requires org-level permissions. Users could reach the page and immediately get a load failure toast.

### OTLP Quick-Start Stale Link (Finding 12)

The OTLP page referenced an outdated repository link rather than current in-product setup surfaces.

## Recommended Sidebar Shape

### 1. Observe
- `dashboard`
- `runs`
- `sessions`
- `request-flow`
- `request-explorer`
- `analytics`
- `engineering`
- `monitoring`
- `model-usage`
- `model-scorecards`

### 2. Build And Improve
- `agents`
- `workflows`
- `playground`
- `prompts`
- `evaluations`
- `datasets`
- `experiments`
- `replay`
- `optimization-opportunities`
- `optimization-simulator`
- `runbooks`

### 3. Gateway And Routing
- `gateway`
- `provider-profiles`
- `response-cache`
- `rate-limits`
- Future: pass-through endpoint UI, deployment health, advanced routing views

### 4. Safety And Governance
- Guardrails
- `tool-registry`
- `search-tools`
- `tool-policies`
- `mcp`
- `data-capture`
- `security`
- `approvals`
- `audit`
- `policy-dry-run`
- `governance-pack`
- `alert-rules`
- `tags`

### 5. FinOps
- `cost-savings`
- `budgets` (with tiers, overrides, model budgets as tabs)
- `billing` (with billing-summary as tab)
- `chargeback`
- `outcomes`

### 6. Organization
- `organization/dashboard`
- `organization`
- `users`
- `workspace`
- `projects`
- `team-models`
- `access-groups`
- `api-keys`

### 7. Platform
- `global-dashboard`
- `organizations`
- `integrations`
- `otlp`
- `mcp-registry`
- `plugins`
- `ai-hub`
- `onboarding`
- `settings`

## Suggested Product Rules

- New dashboard pages should not be added without deciding their sidebar location at the same time.
- If a feature is a sub-configuration of an existing concept, prefer a tab or section before adding a new top-level nav item.
- Backend-only capabilities should be tracked explicitly until they have a first-class UI surface or are intentionally API-only.
- Organization structure, permissions, and ownership should stay grouped together.
- Runtime routing, caching, throttling, and provider behavior should stay grouped together.
- Finance pages should focus on spend, billing, attribution, and ROI, not runtime enforcement controls.

---

# J. FEATURE COVERAGE & SCRIPT NORMALIZATION

This section captures the feature coverage model and script normalization targets from FEATURE-COVERAGE-README.md. See also SCRIPT-NORMALIZATION-PLAN.local.md for the detailed script migration plan.

---

## Coverage Model

Each feature should map to this contract:

| Field | Meaning |
|---|---|
| `UI Surface` | Where the capability is used or verified in the dashboard |
| `Manual Lab` | The UI/operator walkthrough document |
| `Automated Script` | Seed/simulate/verify script that creates state or activity |
| `Infra` | Required support service or external dependency |
| `Current State` | `Present`, `Partial`, or `Missing` from the scripts/labs normalization perspective |

## Required Script Folder Reorganization

The current script folder should be normalized around one entrypoint:

```text
scripts/
  run_demo.py
  cleanup.py
  FEATURE-COVERAGE-README.md
  pricing/
  seed/
  simulate/
  infra/
  integrations/
  scenarios/
    manifests/
    automated/
    labs/
  lib/
```

### Entry Point Contract

`run_demo.py` should become the only script most operators need.

Example commands:

```bash
uv run python scripts/run_demo.py doctor
uv run python scripts/run_demo.py infra up --profile full-demo
uv run python scripts/run_demo.py seed core
uv run python scripts/run_demo.py seed pricing --provider ollama
uv run python scripts/run_demo.py seed feature smtp
uv run python scripts/run_demo.py seed feature backup
uv run python scripts/run_demo.py seed feature kafka
uv run python scripts/run_demo.py simulate full
uv run python scripts/run_demo.py simulate org homelab
uv run python scripts/run_demo.py simulate org localaiagentstack
uv run python scripts/run_demo.py simulate feature gateway
uv run python scripts/run_demo.py simulate feature budgets
uv run python scripts/run_demo.py simulate feature approvals
uv run python scripts/run_demo.py verify feature data-capture
uv run python scripts/run_demo.py reset --hard
```

## Canonical Demo Topology

The normalized default demo should use:

- Platform admin: `admin@runledger.local`
- Password for every account: `runledger`

Organizations:

1. `HomeLab`
   - admin: `admin@homelab.com`
   - users: `user1@homelab.com`, `user2@homelab.com`
   - workspace: `AgentTest`

2. `LocalAIAgentStack`
   - admin: `admin@localstack.com`
   - users: `user1@localstack.com`, `user2@localstack.com`
   - workspaces: `LiteLLM Gateway`, `OpenWebUI`, `Codex`, `Langgraph`, `HermesAgent`, `Claude Desktop`, `OpenAICodes`, `PythonAgents`

Rules:
- org admin belongs to every workspace in that org
- one workspace API key per workspace
- random but reproducible user assignment
- Ollama is the default provider and pricing source for local demos

## Immediate Migration Targets

These current files should be normalized first:

- `apps/api/scripts/seed_demo.py` → `scripts/seed/seed_quick.py`
- `scripts/full_simulate.py` → `scripts/simulate/full_simulate.py`
- `apps/api/scripts/demo_mode.py` → merged into `scripts/run_demo.py` or `scripts/seed/demo_mode.py`
- `scripts/pricing.yaml` → `scripts/pricing/pricing.yaml`

Compatibility shims can remain temporarily, but new work should stop targeting the old layout.

## Definition Of Done

The script folder normalization is complete when:

- every major product feature has a matching lab and automation surface
- no new demo logic is added under `apps/api/scripts/` except container runtime helpers
- `run_demo.py` can seed, simulate, verify, and reset the entire local demo
- `full_simulate` and quick seed share one common script library
- LocalAIAgentStack and HomeLab scenarios are first-class, repeatable, and documented

## Feature Inventory

### Platform Core

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Platform bootstrap | `onboarding`, `organization`, `workspace` | `labs/platform-bootstrap.md` | `seed/core.py` | core compose | Missing |
| Organizations and tenants | `organizations`, `organization` | `labs/orgs-and-workspaces.md` | `seed/core.py` | core compose | Missing |
| Workspaces | `workspace`, `organization` | `labs/orgs-and-workspaces.md` | `seed/core.py` | core compose | Missing |
| Users and memberships | `users`, `organization` | `labs/users-and-rbac.md` | `seed/core.py` | core compose | Missing |
| API keys | `api-keys`, `settings` | `labs/api-keys.md` | `seed/core.py` | core compose | Missing |
| RBAC and role-aware access | many pages via role gating | `labs/users-and-rbac.md` | `seed/core.py`, `verify/rbac.py` | core compose | Partial |
| Platform settings | `settings` | `labs/settings-core.md` | `seed/catalog.py` | core compose | Missing |
| Onboarding and product tour | `onboarding` | `labs/onboarding.md` | `seed/core.py`, `simulate/platform_story.py` | core compose | Missing |

### Instrumentation And Ingest

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Python SDK | `runs`, `analytics`, `sessions` | existing labs | `integrations/python_sdk_runner.py` | core compose | Partial |
| TypeScript SDK | `runs`, `analytics` | `labs/typescript-sdk.md` | `integrations/typescript_sdk_runner.py` | core compose | Missing |
| OTLP ingest | `otlp`, `runs`, `request-flow` | existing `part2_observe.md` | `simulate/feature_otlp.py` | OTEL collector | Partial |
| OpenInference ingest | `otlp`, `request-flow` | `labs/openinference.md` | `simulate/feature_openinference.py` | OTEL collector | Missing |
| Webhook ingest | `runs`, `analytics` | `labs/webhook-ingest.md` | `simulate/feature_webhook.py` | core compose | Missing |
| MCP ingest and control plane | `mcp`, `mcp-registry`, `tool-registry` | `labs/mcp.md` | `simulate/feature_mcp.py`, `integrations/mcp_clients.py` | core compose | Partial |
| Session and end-user attribution | `sessions`, `analytics/users` | `labs/attribution.md` | `simulate/feature_sessions.py` | core compose | Missing |
| Trace/run correlation | `request-flow`, `runs` | `labs/request-flow.md` | `simulate/feature_traces.py` | core compose | Partial |

### Observability

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Runs | `runs` | existing labs | `simulate/full.py` | core compose | Partial |
| Sessions | `sessions` | `labs/sessions.md` | `simulate/feature_sessions.py` | core compose | Missing |
| Request flow | `request-flow` | existing `part2_observe.md` | `simulate/feature_request_flow.py` | core compose | Partial |
| Request explorer | `request-explorer` | `labs/request-explorer.md` | `simulate/feature_request_flow.py` | core compose | Missing |
| Analytics | `analytics`, `engineering` | `labs/analytics.md` | `simulate/full.py` | core compose | Partial |
| Monitoring | `monitoring` | `labs/monitoring.md` | `simulate/feature_monitoring.py` | core compose | Missing |
| Model usage | `model-usage` | `labs/model-usage.md` | `simulate/feature_model_usage.py` | core compose | Missing |
| Model scorecards | `model-scorecards` | `labs/model-scorecards.md` | `simulate/feature_scorecards.py` | core compose | Missing |
| Replay lab | `replay` | `labs/replay.md` | `simulate/feature_replay.py` | core compose | Missing |
| Runbooks | `runbooks` | `labs/runbooks.md` | `simulate/feature_runbooks.py` | core compose | Missing |
| Optimization simulator | `optimization-simulator` | `labs/optimization-simulator.md` | `simulate/feature_optimization_story.py` | core compose | Missing |
| Cost and savings views | `cost-savings`, `optimization-opportunities` | `labs/cost-savings.md` | `simulate/feature_cost_savings.py` | core compose | Missing |

### Gateway And Runtime Controls

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Gateway routes | `gateway` | existing gateway lab | `seed/gateway.py`, `simulate/feature_gateway.py` | core compose | Partial |
| Provider profiles | `provider-profiles` | `labs/provider-profiles.md` | `seed/provider_profiles.py` | core compose | Missing |
| Routing policies | `gateway` | `labs/gateway-routing.md` | `seed/gateway.py`, `simulate/feature_gateway.py` | core compose | Partial |
| Routing groups | `gateway` | `labs/gateway-routing.md` | `seed/gateway.py`, `simulate/feature_gateway.py` | core compose | Partial |
| Fallback chains | `gateway` | `labs/gateway-fallbacks.md` | `seed/gateway.py`, `simulate/feature_gateway_failover.py` | core compose | Missing |
| Deployment health | `gateway`, `monitoring` | `labs/deployment-health.md` | `simulate/feature_gateway_failover.py` | core compose | Missing |
| Pass-through endpoints | `gateway` | `labs/pass-through.md` | `seed/gateway.py`, `simulate/feature_pass_through.py` | core compose | Missing |
| Runtime controls | `gateway`, `rate-limits` | `labs/runtime-controls.md` | `seed/gateway.py`, `simulate/feature_runtime_controls.py` | core compose | Missing |
| Rate limits | `rate-limits`, `gateway` | `labs/runtime-controls.md` | `simulate/feature_runtime_controls.py` | core compose | Missing |
| Benchmarking | `gateway` | `labs/benchmarking.md` | `bench/run_benchmark.py`, `simulate/feature_benchmarks.py` | core compose | Partial |

### Optimization

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Exact cache | `gateway`, `response-cache` | `labs/cache.md` | `simulate/feature_cache.py` | core compose | Missing |
| Semantic cache | `response-cache`, `gateway` | `labs/cache.md` | `simulate/feature_semantic_cache.py` | embedding, semantic-cache, qdrant | Missing |
| Context compiler | `gateway` | `labs/context-compiler.md` | `simulate/feature_context_compiler.py` | context-compiler svc | Missing |
| Prompt compression | `gateway`, `optimization-opportunities` | `labs/prompt-compression.md` | `simulate/feature_prompt_compression.py` | compression svc | Missing |
| Intelligent routing | `gateway` | `labs/gateway-routing.md` | `simulate/feature_routing_optimization.py` | router svc | Missing |
| Tool filtering | `tool-registry`, `mcp`, `gateway` | `labs/tool-filtering.md` | `simulate/feature_tool_filtering.py` | core compose | Missing |
| Optimization flywheel | `gateway`, `optimization-opportunities` | `labs/flywheel.md` | `simulate/feature_flywheel.py` | flywheel svc | Missing |

### FinOps

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Metering | `analytics`, `billing-summary` | `labs/metering.md` | `simulate/full.py` | core compose | Partial |
| Pricing and provider pricing import | `provider-profiles`, `billing` | `labs/pricing.md` | `seed/local_models.py`, `pricing/ollama_pricing.py` | core compose, Ollama | Missing |
| Cost attribution | `analytics`, `chargeback` | `labs/attribution.md` | `simulate/feature_finops.py` | core compose | Missing |
| Budgets | `budgets` | existing labs | `seed/budgets.py`, `simulate/feature_budgets.py` | core compose | Partial |
| Budget tiers | `budget-tiers` | `labs/budget-tiers.md` | `seed/budgets.py` | core compose | Missing |
| Budget overrides | `budget-overrides` | `labs/budget-overrides.md` | `seed/budgets.py` | core compose | Missing |
| Model budgets | `model-budgets` | `labs/model-budgets.md` | `seed/budgets.py` | core compose | Missing |
| Chargeback | `chargeback` | `labs/chargeback.md` | `simulate/feature_chargeback.py` | core compose | Missing |
| Billing summary and periods | `billing`, `billing-summary` | `labs/billing.md` | `simulate/feature_billing.py` | core compose | Missing |
| Ledger | `ledger` | `labs/ledger.md` | `simulate/feature_ledger.py` | core compose | Missing |
| Outcomes and ROI | `outcomes`, `cost-savings` | existing labs | `simulate/feature_outcomes.py` | core compose | Partial |

### Governance

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Prompt registry and versions | `prompts` | `labs/prompts.md` | `seed/prompts.py`, `simulate/feature_prompts.py` | core compose | Missing |
| Evaluations | `evaluations`, `evaluation` | `labs/evaluations.md` | `simulate/feature_evaluations.py` | core compose | Missing |
| Datasets and experiments | `datasets`, `experiments` | `labs/experiments.md` | `simulate/feature_experiments.py` | core compose | Missing |
| Guardrails and content safety | backend `/guardrails`, gateway enforcement | existing labs | existing scripts, `simulate/full.py` | core compose | Partial |
| Approvals | `approvals` | `labs/approvals.md` | `seed/approvals.py`, `simulate/feature_approvals.py` | core compose | Missing |
| Alerts | `alert-rules`, `monitoring` | `labs/alerts.md` | `seed/alerts.py`, `simulate/feature_alerts.py` | core compose | Missing |
| Retention | `settings`, `data-capture` | `labs/retention.md` | `seed/retention.py` | core compose | Missing |
| Policy dry-run | `policy-dry-run` | `labs/policy-dry-run.md` | `simulate/feature_policy_dry_run.py` | core compose | Missing |
| Governance pack and audit | `governance-pack`, `audit` | `labs/governance-pack.md` | `simulate/feature_governance_pack.py` | core compose | Missing |
| Data capture studio | `data-capture` | `labs/data-capture.md` | `seed/data_capture.py`, `simulate/feature_data_capture.py` | core compose | Missing |
| Tag management | `tags` | `labs/tags.md` | `seed/tags.py` | core compose | Missing |
| Search tools | `search-tools` | `labs/search-tools.md` | `seed/search_tools.py` | core compose | Missing |
| Tool registry | `tool-registry` | `labs/tool-registry.md` | `seed/tool_registry.py` | core compose | Missing |
| Tool policies | `tool-policies` | `labs/tool-policies.md` | `seed/tool_policies.py`, `simulate/feature_tool_filtering.py` | core compose | Missing |
| Access groups | `access-groups` | `labs/access-groups.md` | `seed/access_groups.py` | core compose | Missing |
| Security settings | `security` | `labs/security-settings.md` | `seed/security.py` | core compose | Missing |

### Agentic And Admin Surfaces

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Agents | `agents` | `labs/agents.md` | `simulate/feature_agents.py` | core compose | Missing |
| Workflows | `workflows` | `labs/workflows.md` | `simulate/feature_workflows.py` | core compose | Missing |
| Vector stores | `vector-stores` | `labs/vector-stores.md` | `simulate/feature_vector_stores.py` | qdrant | Missing |
| API playground | `playground` | `labs/playground.md` | `seed/playground.py` | core compose | Missing |
| MCP registry | `mcp-registry` | `labs/mcp-registry.md` | `seed/mcp.py` | core compose | Missing |
| Plugins | `plugins` | `labs/plugins.md` | `seed/plugins.py` | core compose | Missing |
| Projects | `projects` | `labs/projects.md` | `seed/projects.py` | core compose | Missing |
| AI hub | `ai-hub` | `labs/ai-hub.md` | `simulate/feature_ai_hub.py` | core compose | Missing |

### Operations And Integrations

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| SMTP settings and email delivery | `settings` | `labs/smtp-and-email.md` | `seed/email.py`, `simulate/feature_email.py` | SMTP server | Missing |
| Email delivery history and reports | `settings` | `labs/smtp-and-email.md` | `simulate/feature_email.py` | SMTP server | Missing |
| Backup target config | `settings` | `labs/backup-and-restore.md` | `seed/backup.py` | MinIO or S3 | Missing |
| Backup runs and snapshots | `settings` | `labs/backup-and-restore.md` | `simulate/feature_backup.py` | MinIO or S3 | Missing |
| Restore drill | `settings` | `labs/backup-and-restore.md` | `simulate/feature_restore_drill.py` | MinIO or S3 | Missing |
| Kafka export configs | `integrations` | `labs/kafka-streaming.md` | `seed/kafka.py` | Redpanda or Kafka | Missing |
| Kafka delivery history, retry, DLQ | `integrations` | `labs/kafka-streaming.md` | `simulate/feature_kafka.py` | Redpanda or Kafka | Missing |
| Redpanda live streaming demo | `integrations`, `monitoring` | `labs/kafka-streaming.md` | `streaming/kafka_consumer.py`, `simulate/feature_kafka.py` | Redpanda | Partial |
| OTEL collector | `otlp` | `labs/otlp-collector.md` | `infra/otel.py` | OTEL collector | Missing |
| Queue visibility | `settings` | `labs/operator-queues.md` | `simulate/feature_ops_queues.py` | Redis, Celery | Missing |
| Feature flags | `settings` | `labs/feature-flags.md` | `seed/operator_settings.py` | core compose | Missing |
| Storage posture and infra policy | `settings` | `labs/operator-storage.md` | `infra/checks.py` | MinIO/S3 optional | Missing |
| Local TLS and demo proxy | `settings`, external browser | `labs/local-tls.md` | `infra/tls.py` | Caddy | Missing |
| Deployment profiles | local deployment docs | `labs/deployment-profiles.md` | `infra/profiles.py` | compose profiles | Missing |

### Local Models And External Local Stacks

| Feature | UI Surface | Manual Lab | Automated Script | Infra | Current State |
|---|---|---|---|---|---|
| Ollama model discovery | `provider-profiles`, `model-usage` | `labs/local-models.md` | `pricing/ollama_pricing.py` | Ollama | Missing |
| Local model pricing import | `provider-profiles`, `billing` | `labs/local-models.md` | `seed/local_models.py` | Ollama | Missing |
| HomeLab `AgentTest` traffic | full product surfaces | `labs/homelab.md` | `simulate/traffic/homelab_agenttest.py` | local Python agent | Missing |
| LocalAIAgentStack bootstrap | `organizations`, `workspace`, `integrations` | `labs/localaiagentstack.md` | `integrations/localaiagentstack/bootstrap.py` | LocalAIAgentStack | Missing |
| LocalAIAgentStack Python agents | `runs`, `analytics`, `gateway` | `labs/localaiagentstack.md` | `integrations/localaiagentstack/python_agent_runner.py` | LocalAIAgentStack | Missing |
| Codex workspace traffic | `runs`, `mcp`, `gateway` | `labs/codex.md` | `integrations/localaiagentstack/codex_runner.py` | Codex/local stack | Missing |
| OpenWebUI workspace traffic | `runs`, `otlp`, `analytics` | `labs/openwebui.md` | `integrations/localaiagentstack/openwebui_runner.py` | OpenWebUI/local stack | Missing |
| Hermes/OpenHands/Desktop agent traffic | `runs`, `mcp`, `approvals`, `tool-registry` | `labs/desktop-agents.md` | `integrations/localaiagentstack/desktop_agent_runner.py` | local stack | Missing |

---

# K. FEATURE LIST — COMPLETE PAGE CATALOG

This section captures the detailed feature catalog from FEATURE-LIST.md — every button, form, action, filter, export, tab, modal, toggle, chart, and data display across all 77+ pages.

---

## Section 1: Observe (15 pages)

### Dashboard (`/dashboard`)
- **Data:** 4 KPI cards (Total Spend with delta %, Agent Runs, Avg Cost/Run, Total Tokens); Spend Over Time area chart; Spend by Model donut chart; Spend by Feature bar chart; Recent Runs list (8 runs)
- **Filters:** DashboardScopeBar (time range 24h/7d/30d/90d, Project selector, Access Group selector)
- **Actions:** "Org Dashboard" link (org admins), "View all" → `/runs`, clickable run rows
- **Gaps:** No team/project drill-down; no real-time refresh

### Runs (`/runs`)
- **Data:** 4 KPI cards; Model Activity mini bar chart; RunsTable (dense); Result count
- **Filters:** Expandable RunFilters: Status toggles, Model combobox, Run ID search, Feature tag, End user ID, Cost range, Time presets (5m–30d), Custom datetime range
- **Actions:** "Request Explorer" link, "Export CSV" split button, PDF export, "Load more" pagination
- **Gaps:** No project_id or team filter; CSV export is client-side

### Run Detail (`/runs/[run_id]`)
- **Data:** RunSummaryBar; Error banner; DAG graph; PayloadViewer; Provider Calls table; Spans table; Tool Calls table
- **Actions:** RunScorePanel "Submit Score" with dropdown/value/confidence
- **Gaps:** No project/team attribution visible; no "replay this run" action

### Sessions (`/sessions`)
- **Data:** Sessions table (Session ID, User, Turns, Cost, Duration, Avg Score, Started)
- **Filters:** Time range, End user ID, Min turns, Cost range, Search
- **Gaps:** No project/team filter; no export

### Session Detail (`/sessions/[session_id]`)
- **Data:** Session header; Cumulative Cost Over Turns line chart; Runs timeline list
- **Gaps:** No session-level scoring

### Request Flow (`/request-flow`)
- **Data:** 4 KPI cards; Sankey/flow SVG diagram; Top Prompts/Users/Agents lists; Optimization Hints
- **Filters:** 5 flow modes, Metric thickness, Scope, Density, Top N, Collapse small, Zoom
- **Gaps:** "Team cost flow" mode references free-text strings

### Request Explorer (`/request-explorer`)
- **Data:** 4 KPI cards; Recent Requests list; Selected request detail (8 fact cards, Request Lifecycle, Prompt/Response, Model Calls, Tools, Outcome, Spans)
- **Filters:** Search, Status, Intent, Model
- **Gaps:** No project/team filter

### Analytics (`/analytics`)
- **Data:** KPI strip; Spend Over Time area chart; Spend by Model pie chart; Spend by Feature bar chart; Spend by End User table; Model Breakdown table
- **Filters:** Time period (11 presets)
- **Actions:** Refresh, Export (CSV + JSON)
- **Gaps:** No team/project breakdown; no period comparison

### Economics (`/analytics/economics`)
- **Data:** Top Workflows by Cost table; Version Compare delta cards; Cost Regressions table; Annotations list
- **Actions:** Compare button
- **Gaps:** Version compare is manual text entry

### Users Analytics (`/analytics/users`)
- **Data:** Cohort distribution strip; Users by Spend table with anomaly warnings
- **Filters:** Segmentation tabs (All/Heavy/Anomalous/New)
- **Gaps:** Anomaly thresholds hardcoded

### Engineering (`/engineering`)
- **Data:** 8 KPI cards; Request Lifecycle Pipeline; Quality Funnel; Agent Dependency Graph; Cost by Feature/Team/Model bars; Tool Usage bars
- **Filters:** DashboardScopeBar
- **Gaps:** "Cost by Team" uses free-text; dependency graph is static

### Model Usage (`/model-usage`)
- **Data:** 4 KPI cards; Resource Usage Timeline stacked area; Routing Distribution pie; Cost/Latency/Quality bars; Model Usage Table; Routing Decision Detail table
- **Filters:** Scope selector, DashboardScopeBar
- **Gaps:** Quality scores sparse; routing decisions not auditable

### Monitoring (`/monitoring`)
- **Data:** 3 KPI cards; Security Events tab; Alert Firings tab; Gateway Log tab
- **Filters:** Per-tab: time range, type/status/model dropdowns, search
- **Gaps:** No alert acknowledgment; no severity classification

### Evaluations (`/evaluations`)
- **Data:** Score Summary cards (7-day avg); Recent Scores table
- **Actions:** "Submit Score" form (Run ID, Name, Value, Label, Source, Confidence)
- **Gaps:** Manual only; overlaps with Evaluation page

### Outcomes (`/outcomes`)
- **Data:** Summary KPI cards per outcome type; Success Rate Trend chart; Workflow ROI table; Quality vs Success correlation
- **Filters:** Window days (7/14/30/90)
- **Gaps:** ROI assumes value_usd populated; no team/project breakdown

## Section 2: Build & Improve (18 pages)

### Agents (`/agents`) + Agent Detail
- **Data:** Agent cards grid; Agent detail with tools, runs, metrics, memory
- **Actions:** Register, Edit, Archive, memory management
- **Gaps:** budget_envelope decorative; no team/project assignment

### Workflows (`/workflows`) + Detail
- **Data:** Workflow cards; step editor; run history
- **Actions:** Create, Edit, Archive, "Run Now"
- **Gaps:** Steps are JSON blobs; no visual editor

### Playground (`/playground`)
- **Data:** Chat history; response metadata; token usage
- **Actions:** Send, Clear, Copy, "Save as prompt", parameter adjustments
- **Gaps:** Bypasses gateway; no cost tracking

### Prompts (`/prompts`) + Detail
- **Data:** Prompts table; version history; git sync
- **Actions:** Create, Delete, "New Version", "Promote to production"
- **Gaps:** Git sync one-way; no A/B testing

### Evaluation Studio (`/evaluation`)
- **Data:** 4 tabs: Experiments, Datasets, Prompts, Evaluators (each with tables)
- **Actions:** Full CRUD for each entity type; Run experiments/evaluators
- **Gaps:** Experiments run synchronously; config is raw JSON

### Datasets (`/datasets`), Experiments (`/experiments`), Replay Lab (`/replay-lab`)
- See FC-04 for consolidation plan

### Optimization Opportunities (`/optimization`)
- **Data:** Opportunity cards with savings estimates
- **Actions:** Apply, Dismiss
- **Gaps:** Rule-based; "Apply" action vague

### Optimization Simulator (`/optimization-simulator`)
- **Data:** Simulation results, cost comparison
- **Actions:** Run Simulation, Apply to Gateway
- **Gaps:** Static cost tables; no audit trail for applied changes

### Model Scorecards (`/model-scorecards`)
- **Data:** Per-model scorecards (quality, cost efficiency, latency, reliability)
- **Gaps:** Small sample sizes; no confidence intervals

### Runbooks (`/runbooks`)
- **Data:** Runbook list with steps
- **Actions:** Create, Execute, Edit, Delete
- **Gaps:** Steps are text-only; no workflow integration

### Vector Stores (`/vector-stores`)
- **Data:** Store list with collection info
- **Actions:** Create, Delete, Sync
- **Gaps:** No document upload; no query testing

## Section 3: Gateway & Safety (17 pages)

### Model Gateway (`/gateway`)
- **Data:** Routing Groups, Routes, Policies, Pass-through, Flywheel, Benchmarks (6 tabs)
- **Actions:** Full CRUD for each entity; "Test Route", "Run Benchmark"
- **Gaps:** Only 3 of 9 routing strategies have ML backing; no A/B result analysis; canary has no auto-rollback

### Provider Profiles (`/provider-profiles`)
- **Data:** Provider cards with health/latency/cost
- **Actions:** Add, Edit, Delete, "Test Connection"
- **Gaps:** API keys should be in secrets manager; no key rotation

### Guardrails (`/guardrails`)
- **Data:** Rules table; Safety profiles
- **Actions:** Create, Edit, Delete, Toggle, "Test Rule"
- **Gaps:** exec() sandbox bypass (DF-04); no versioning

### Response Cache, Rate Limits, Tool Registry, Search Tools, Tool Policies, MCP Servers, Data Capture, Security, Approvals, Audit Log, Policy Dry Run, Governance Pack, Alert Rules, Tags
- See individual items in sections B-D for specific gaps

## Section 4: FinOps, Org & Platform (27 pages)

### Cost Savings (`/cost-savings`)
- **Data:** KPI cards; CostBreakdownBars; ROI Table; SavingsAttributionCards; CostHeatmap; Budget Overlay
- **Filters:** DashboardScopeBar with dimension toggle (Team/Project/Application/User/Agent/Model/Tool/Time)
- **Gaps:** "Team" dimension uses free-text (CL-06); savings estimated not measured

### Budgets, Budget Tiers, Budget Overrides, Model Budgets
- See AG-03 and FC-10 for consolidation plan

### Billing, Billing Summary, Billing Period Detail
- See FC-09 for consolidation plan

### Chargeback (`/chargeback`)
- **Data:** Rules table; Reports with breakdown
- **Actions:** Add/Delete rules; Export CSV/JSON
- **Gaps:** FC-01 (endpoint missing), FC-03 (no real attribution)

### Organization, Org Dashboard, Users, Workspaces, Projects, Team Models, Access Groups, API Keys
- See CL-01 through CL-07 for cleanup plan

### OTLP, MCP Registry, Plugins, AI Hub, Integrations, Settings
- See individual items in sections B-D for specific gaps

### Global Dashboard, Organizations (Platform Admin)
- See individual items for gaps

---

# SUMMARY

| Category | Count | P0 | P1 | P2 | P3 | P4 |
|---|---|---|---|---|---|---|
| **A. Architecture Gaps** | 21 | 1 | 8 | 10 | 0 | 0 |
| **B. Feature Cohesion** | 16 | 1 | 1 | 5 | 9 | 0 |
| **C. UI Gaps** | 14 | 0 | 0 | 2 | 12 | 0 |
| **D. Defects** | 17 | 7 | 2 | 4 | 4 | 0 |
| **E. Good to Have** | 16 | 0 | 1 | 2 | 9 | 4 |
| **F. Simulators & Scripts** | 6 | 0 | 0 | 1 | 5 | 0 |
| **G. Teams & Projects Cleanup** | 7 | 0 | 0 | 4 | 3 | 0 |
| **TOTAL** | **97** | **9** | **12** | **28** | **42** | **4** |

---

# RECOMMENDED EXECUTION ORDER

**Week 1-2: Stop the bleeding**
- All P0 Defects: DF-01 through DF-07 (runtime crashes, security critical)
- AG-06 (register models in __init__.py — 15 min, unblocks everything)
- AG-21 (admin auth on write endpoints — 1 day)
- FC-01, FC-02 (chargeback endpoint — currently returns 404)

**Week 2-3: Structural integrity**
- AG-03 (budget unification — collapse 5 systems into 1)
- AG-05 (FK constraints — 35+ missing)
- CL-01 through CL-04 (remove decorative team/project/budget fields)
- AG-09, AG-10, AG-13 (gateway performance)

**Week 3-5: Enterprise readiness**
- AG-04 (budget enforcement in gateway)
- AG-11, AG-12 (circuit breaker, streaming)
- AG-14, AG-15 (Redis durability, Celery concurrency)
- DF-08 through DF-14 (security P1/P2 fixes)
- FC-03, FC-04, FC-05 (chargeback attribution, consolidate experiments, remove dead code)

**Week 5-7: Product cohesion**
- UI-01 (sidebar collapse)
- UI-02 (RBAC guard)
- CL-05 through CL-07 (simplify Project, clean up team UI references)
- FC-09, FC-10 (billing/budget page consolidation)
- AG-19, AG-20 (plugin system)
- AG-08 (tenant-level scoping)

**Week 7-9: Quality and testing**
- GH-01 (integration tests)
- GH-02 (coverage measurement)
- GH-03 (frontend E2E)
- GH-04 (load testing)
- SS-01 (scenario assertions)

**Week 9-10: Polish and differentiation**
- Remaining UI gaps (UI-03 through UI-14)
- Remaining good-to-have items
- Simulator and script improvements

**Total estimate: ~10 weeks for one experienced full-stack engineer, ~5 weeks with two (frontend/backend split).**

---

*Cross-reference: SCRIPT-NORMALIZATION-PLAN.local.md for detailed script migration steps. SECURITY-EE-TODO.md for enterprise security hardening backlog.*
