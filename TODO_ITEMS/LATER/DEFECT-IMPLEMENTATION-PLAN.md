# RunLedger — Defect Implementation Plan

**Created:** August 12, 2026
**Source:** Master_TODO.md (97 items across 7 categories)
**Constraint:** Every task is scoped to 1-2 hours, max 4 hours with vibe coding.
**Tracks:** Backend (BE), Frontend (UI), Infra/Config (INF), Docs/Scripts (DOC)

---

## How This Plan Works

- Tasks are grouped into **sprints** (logical waves), ordered by dependency.
- Each task has a **track** (BE/UI/INF/DOC) so you can parallelize backend and frontend work.
- Tasks within a sprint can be done in any order **unless** a dependency arrow says otherwise.
- Time estimates assume one person using Claude Code / vibe coding.
- `→` means "must be done after". No arrow = independent within the sprint.

---

# SPRINT 0 — STOP THE BLEEDING (Day 1)

These are 5-30 minute fixes for runtime crashes and critical security gaps. Do them first, in one sitting.

---

### S0-01 · Fix `_period_key` NameError [BE] — 15 min
**Refs:** DF-01
**What:** Add `from runledger_api.services.budgets import _period_key` to `workers/metering.py` imports.
**Files:** `workers/metering.py:161`
**Test:** Start worker, trigger a budget threshold event, confirm no crash.

### S0-02 · Fix `ProviderSyncRequest` NameError [BE] — 15 min
**Refs:** DF-02
**What:** Move `from pydantic import BaseModel` from inside function body to top-level imports in `routers/hub.py`.
**Files:** `routers/hub.py:147,179`
**Test:** `python -c "from runledger_api.routers.hub import router"` — no ImportError.

### S0-03 · Fix guardrail argument types in plugin runner [BE] — 15 min
**Refs:** DF-03
**What:** Change `evaluate_guardrails(db, workspace_id, None, arg_str)` to `evaluate_guardrails(db, workspace_id, "tool_call", [arg_str])` in `services/plugin_runner.py`.
**Files:** `services/plugin_runner.py:116`
**Test:** Call a tool-governance endpoint; confirm guardrail actually evaluates instead of silently allowing.

### S0-04 · Register 13 missing model files in `__init__.py` [BE] — 15 min
**Refs:** AG-06
**What:** Add imports for `approvals`, `billing`, `budgets`, `agents`, `projects`, `playground`, `vector_stores`, `mcp_registry`, `plugins`, `hub`, `otlp`, `evaluators`, `outcomes` to `models/__init__.py`.
**Files:** `models/__init__.py`
**Test:** `alembic check` — no "target metadata not up to date" warnings for these tables.

### S0-05 · Fix OIDC algorithm confusion [BE] — 15 min
**Refs:** DF-08
**What:** In `services/security.py:72-88`, replace `alg = header.get("alg", "RS256")` with hardcoded `algorithms=["RS256", "RS384", "RS512"]`. Never trust the token's `alg` claim.
**Files:** `services/security.py:72-88`
**Test:** Craft a test token with `alg: HS256` — verify it's rejected.

### S0-06 · Fix CORS to restrict methods/headers [BE] — 15 min
**Refs:** DF-11
**What:** In `main.py:83-89`, replace `allow_methods=["*"]` and `allow_headers=["*"]` with explicit lists: `["GET", "POST", "PUT", "DELETE", "OPTIONS"]` and `["Authorization", "Content-Type", "X-API-Key", "X-Workspace-ID"]`.
**Files:** `main.py:83-89`
**Test:** Send OPTIONS preflight with `Access-Control-Request-Method: PATCH` — confirm rejected.

### S0-07 · Fix rate limit tier for gateway [BE] — 15 min
**Refs:** AG-13
**What:** Change `/chat/completions` from `management` tier (60 RPM) to `ingest` tier (600 RPM) in the rate limit decorator.
**Files:** `routers/gateway.py` (decorator)
**Test:** Confirm the endpoint responds under moderate concurrency instead of 429'ing at 1 RPS.

### S0-08 · Fix migration startup race [INF] — 15 min
**Refs:** AG-16
**What:** In `apps/api/scripts/start.sh`, gate `alembic upgrade head` behind `if [ "$RUN_MIGRATIONS" = "true" ]`. Default to false.
**Files:** `apps/api/scripts/start.sh`
**Test:** Start API without env var — no migration runs. Set `RUN_MIGRATIONS=true` — migrations run.

---

# SPRINT 1 — SECURITY CRITICAL (Days 2-3)

P0 security defects. Each is independent — parallelize freely.

---

### S1-01 · Encrypt ledger signing keys [BE] — 2h
**Refs:** DF-05
**What:** Add Fernet encryption using a `LEDGER_MASTER_KEY` env var. Encrypt `key_value` on write, decrypt on read in `services/ledger.py:52`. Add migration to re-encrypt existing keys.
**Files:** `models/ledger.py:29`, `services/ledger.py:52`, new migration
**Test:** Insert a signing key, verify DB stores ciphertext, verify runtime decrypts correctly.

### S1-02 · Stop emailing plaintext credentials [BE] — 2h
**Refs:** DF-06
**What:** In `services/email.py:124-189`: (1) Remove raw password from email body. (2) Replace with one-time password reset link using a signed token with 24h expiry. (3) Remove API key from email — show only in UI after creation.
**Files:** `services/email.py:124-189`
**Test:** Create user → verify email contains reset link, not password.

### S1-03 · Remove hardcoded default secrets [INF] — 2h
**Refs:** DF-07
**What:** (1) Remove default values for `POSTGRES_PASSWORD`, `SECRET_KEY`, `ADMIN_SECRET` from `docker-compose.yml`. (2) In `core/config.py`, add startup validation that rejects known defaults (`runledger`, `change-me-in-production-32chars`, `runledger-admin`). (3) Update `.env.example` with placeholder comments. (4) Add `requirepass` to Redis config.
**Files:** `docker-compose.yml`, `.env.example`, `core/config.py`, Redis config
**Test:** Start API with default secrets → clear error message. Start with real secrets → success.

### S1-04 · Fix IP ACL default-deny [BE] — 1h
**Refs:** DF-13
**What:** In `services/security.py:148-149,121,106-109`: (1) When ACL is enabled and no rules match, return deny (not allow). (2) When `client_ip` is `None`, deny instead of skip. (3) Validate `X-Forwarded-For` against a `TRUSTED_PROXIES` config list.
**Files:** `services/security.py:106-149`
**Test:** Enable ACL, send request from unlisted IP → blocked. Send with no IP → blocked.

### S1-05 · Add admin auth to write endpoints (5 routers) [BE] — 2h
**Refs:** AG-21
**What:** Add `require_workspace_admin` dependency to all POST/PUT/DELETE endpoints in: `hub.py`, `mcp_registry.py`, `plugins.py`, `projects.py`, `phase16_deferred.py`.
**Files:** 5 router files
**Test:** Call write endpoint with non-admin API key → 403. Admin key → success.

### S1-06 · API key hashing with pepper [BE] — 2h
**Refs:** DF-09
**What:** (1) Add `API_KEY_PEPPER` env var. (2) Replace `hashlib.sha256(key)` with `hmac.new(pepper, key, hashlib.sha256)` in `services/auth.py:22-28`. (3) Add migration to rehash existing keys (requires one-time key rotation or dual-check period).
**Files:** `services/auth.py:22-28`
**Test:** Create API key → verify hash differs from raw SHA-256. Authenticate → success.

---

# SPRINT 2 — GUARDRAIL SANDBOX + GATEWAY PERF (Days 3-5)

These are the remaining P0 defect and the highest-impact gateway performance fixes.

---

### S2-01 · Guardrail sandbox: replace exec() — Part 1: RestrictedPython [BE] — 4h
**Refs:** DF-04
**What:** (1) Install `RestrictedPython`. (2) Replace `exec()` in `services/guardrails.py:100-173` with `compile_restricted` + `safe_globals`. (3) Add `signal.alarm` timeout (or `threading.Timer` on Windows). (4) Change fail mode from `allow` to `deny`.
**Files:** `services/guardrails.py:100-173`, `requirements.txt`
**Test:** Try known bypass vectors (string concat `__import__`, getattr, chr reconstruction) → all blocked. Timeout test → denied after limit.

### S2-02 · Gateway connection pooling [BE] — 2h
**Refs:** AG-09
**What:** Create module-level `_provider_clients: dict[str, httpx.AsyncClient]` in `services/gateway_providers.py`. Each provider base URL gets one pooled client (max 100 connections, 30s keepalive). Add `close_all_clients()` shutdown hook.
**Files:** `services/gateway_providers.py:157,172,254,269,613,633`
**Test:** Send 10 concurrent requests → verify only 1 TLS handshake per provider (check connection count).

### S2-03 · Gateway: move request logging to background [BE] — 3h
**Refs:** AG-10 (partial — logging only, not cost cap aggregation)
**What:** In `services/gateway.py:627-706`, wrap the DB write block (request log, Kafka delivery, cache store) in `asyncio.create_task()`. Keep cost cap check synchronous for now.
**Files:** `services/gateway.py:627-706`
**Test:** Benchmark: measure p95 latency before/after with 50 concurrent requests.

### S2-04 · Gateway: pre-aggregate cost caps in Redis [BE] — 3h
**Refs:** AG-10 (partial — cost cap aggregation)
**What:** Replace the SUM aggregation over `gateway_requests` in `services/gateway_controls.py:88-236` with Redis INCRBY per (route, period) key. Add periodic Celery task to reconcile Redis counters with DB every 60s.
**Files:** `services/gateway_controls.py:88-236`, new Celery task
**Depends on:** S2-03
**Test:** Cost cap still triggers correctly. DB SUM and Redis counter agree within 60s window.

### S2-05 · Fix Redis config for budget durability [INF] — 1h
**Refs:** AG-14
**What:** In `docker-compose.yml` Redis service: set `appendonly yes`, change maxmemory-policy to `volatile-lru`. Update Helm values.yaml if present.
**Files:** `docker-compose.yml`, Helm chart
**Test:** Fill Redis, trigger LRU → only TTL keys evicted, budget counters survive.

---

# SPRINT 3 — CLEANUP DECORATIVE PRIMITIVES (Days 5-7)

Remove fake budget/team controls before building real ones. Backend and UI tasks can be parallelized.

---

### S3-01 · Remove `team_name` from IpAclRule + chargeback [BE] — 2h
**Refs:** CL-01 (partial)
**What:** (1) Remove `team_name` column from `IpAclRule` model — scope by workspace_id instead. (2) Remove "team" from `ChargebackRule.dimension` enum/validation — valid values become workspace, feature_tag, end_user, api_key, model. (3) Remove `team` from `ApiKey.ownership_type` enum. (4) Alembic migration for all three.
**Files:** `models/security.py:106`, `models/billing.py:136`, `models/tenant.py:174-177`
**Test:** Create IP ACL rule without team_name → works. Create chargeback rule with dimension=team → rejected.

### S3-02 · Rename TeamModel.team_name to label [BE] — 1h
**Refs:** CL-01 (partial)
**What:** Rename column `team_name` → `label` on `TeamModel` model. Update router and schema references. Migration with `ALTER COLUMN RENAME`.
**Files:** `models/projects.py:54`, `routers/projects.py`
**Test:** Existing team models still load with renamed column.

### S3-03 · Remove Project.budget_usd and budget_period [BE] — 1h
**Refs:** CL-02
**What:** Drop `budget_usd` and `budget_period` columns from `Project` model. Update `routers/projects.py` to remove those fields from create/update schemas. Migration to drop columns.
**Files:** `models/projects.py:27-28`, `routers/projects.py`
**Depends on:** None
**Test:** Create project → no budget fields accepted. Existing projects load fine.

### S3-04 · Remove AccessGroup.budget_usd [BE] — 30 min
**Refs:** CL-03
**What:** Drop `budget_usd` from `AccessGroup` model. Update router schemas. Migration.
**Files:** `models/access_groups.py:22-23`
**Test:** Create access group → no budget field.

### S3-05 · Remove Agent.budget_envelope [BE] — 30 min
**Refs:** CL-04
**What:** Drop `budget_envelope` from `Agent` model. Update router schemas. Migration.
**Files:** `models/agents.py:39`
**Test:** Register agent → no budget_envelope field.

### S3-06 · UI: Remove budget fields from Projects page [UI] — 1h
**Refs:** CL-02
**What:** Remove budget_usd and budget_period form fields from the Projects create/edit forms. Add a "Manage budgets →" link pointing to `/budgets`.
**Files:** `apps/web/app/(dashboard)/projects/page.tsx:95,419`
**Depends on:** S3-03
**Test:** Open Projects page → no budget fields. Link to Budgets works.

### S3-07 · UI: Remove budget field from Access Groups page [UI] — 30 min
**Refs:** CL-03
**What:** Remove budget_usd form field from access group create/edit. Add link to Budgets page.
**Files:** `apps/web/app/(dashboard)/access-groups/page.tsx`
**Depends on:** S3-04
**Test:** Open Access Groups → no budget field.

### S3-08 · UI: Remove budget field from Agents page [UI] — 30 min
**Refs:** CL-04
**What:** Remove budget_envelope from agent registration form. Add link to Budgets page.
**Files:** `apps/web/app/(dashboard)/agents/page.tsx`
**Depends on:** S3-05
**Test:** Open Agents → no budget_envelope field.

### S3-09 · UI: Replace "Team" with "Workspace" in dimension toggles [UI] — 1h
**Refs:** CL-06
**What:** In Cost Savings, Engineering, Request Flow, and Chargeback pages: replace "Team" dimension toggle/chart label with "Workspace". Remove "Team cost flow" mode from Request Flow (or rename to "Workspace cost flow").
**Files:** `apps/web/app/(dashboard)/cost-savings/page.tsx`, `engineering/page.tsx`, `request-flow/page.tsx`, `chargeback/page.tsx`
**Depends on:** S3-01
**Test:** Open each page → "Team" label gone, replaced with "Workspace".

### S3-10 · UI: Rename "Team Models" to "Approved Models" [UI] — 30 min
**Refs:** CL-07
**What:** Change page title, sidebar label, and all in-page references from "Team Models" to "Approved Models".
**Files:** `apps/web/app/(dashboard)/team-models/page.tsx`, `Sidebar.tsx`
**Depends on:** S3-02
**Test:** Sidebar shows "Approved Models". Page title matches.

---

# SPRINT 4 — CHARGEBACK + BUDGET CRUD (Days 7-9)

Fix the FinOps chain so it actually works end-to-end.

---

### S4-01 · Implement chargeback report endpoint [BE] — 3h
**Refs:** FC-01
**What:** Add `GET /billing/chargeback-report` to `routers/billing.py`. Query actual spend from `provider_calls`/`agent_runs` grouped by dimension. Wire in `apply_chargeback_rules()` from `services/billing.py:582-608`. Return grouped attribution data.
**Files:** `routers/billing.py`, `services/billing.py`
**Test:** Create chargeback rules → call endpoint → get real spend breakdown by dimension.

### S4-02 · Wire chargeback rules into billing period close [BE] — 1h
**Refs:** FC-02
**What:** In `close_billing_period()`, call `apply_chargeback_rules()` to generate attribution breakdown as part of the period close output.
**Files:** `services/billing.py`
**Depends on:** S4-01
**Test:** Close billing period → chargeback attribution included in result.

### S4-03 · Add chargeback export endpoint [BE] — 1h
**Refs:** FC-01 (export part)
**What:** Add `GET /billing/chargeback-report/export` with CSV and JSON format support. Server-side streaming for large datasets.
**Files:** `routers/billing.py`
**Depends on:** S4-01
**Test:** Call export endpoint → get valid CSV with attribution rows.

### S4-04 · Add chargeback rule Update endpoint [BE] — 1h
**Refs:** FC-15
**What:** Add `PUT /billing/chargeback-rules/{id}` to `routers/billing.py`.
**Files:** `routers/billing.py`
**Test:** Create rule → update weight → verify changed.

### S4-05 · Fix chargeback dimension attribution [BE] — 3h
**Refs:** FC-03
**What:** Rewrite `apply_chargeback_rules()` to query actual spend grouped by the rule's dimension from `provider_calls`/`agent_runs`, instead of multiplying total cost by static weights. Remove "team" and "project" as dimension options.
**Files:** `services/billing.py:582-608`, `models/billing.py:136`
**Depends on:** S4-01, S3-01
**Test:** Create rules with feature_tag dimension → get actual per-feature_tag spend, not proportional guessing.

### S4-06 · Add GET/PUT endpoints to budgets router [BE] — 2h
**Refs:** AG-22
**What:** Add `GET /budgets/{id}` and `PUT /budgets/{id}` to `routers/budgets.py`. Include validation that scope_id references a real entity.
**Files:** `routers/budgets.py`
**Test:** Create budget → GET by ID → PUT with new amount → verify updated.

### S4-07 · Fix cost savings category attribution [BE] — 2h
**Refs:** FC-12
**What:** In `workers/metering.py`, populate `savings_category` during cost enrichment based on actual optimization decisions (cache_hit, cheaper_model_routing, local_model) instead of post-hoc model name matching. Remove the heuristic guessing in the Cost Savings page.
**Files:** `workers/metering.py`, `apps/web/app/(dashboard)/cost-savings/page.tsx:143-157`
**Test:** Process a cached request → savings_category = "cache_hit" (not guessed from model name).

---

# SPRINT 5 — GATEWAY HARDENING (Days 9-12)

Circuit breaker, streaming improvements, retry fixes.

---

### S5-01 · Circuit breaker: state machine [BE] — 3h
**Refs:** AG-11
**What:** Create `services/circuit_breaker.py` with in-memory per-route state machine: closed (pass through) → open (after N failures, block for cooldown) → half-open (allow 1 probe, close on success / reopen on failure). Configure failure_threshold, cooldown_seconds, half_open_max_calls.
**Files:** Create `services/circuit_breaker.py`
**Test:** Unit test: 5 failures → opens → cooldown → half-open → 1 success → closes.

### S5-02 · Circuit breaker: integrate into gateway [BE] — 2h
**Refs:** AG-11
**What:** Replace the rudimentary `cooldown_until` check in `services/gateway.py:822-823,972-975` with the circuit breaker. Persist state to DB only on state transitions (not per request). Remove DB writes from hot path.
**Files:** `services/gateway.py:822-823,972-975`
**Depends on:** S5-01
**Test:** Configure route with failing provider → circuit opens → requests fast-fail → provider recovers → circuit closes.

### S5-03 · Streaming: pre-flight health check [BE] — 2h
**Refs:** AG-12 (partial)
**What:** Before committing to a streaming route in `routers/gateway.py:470-582`, perform a non-streaming health probe (lightweight HEAD or small completion) against the selected route. If unhealthy, try next route in fallback chain before streaming begins.
**Files:** `routers/gateway.py:470-582`
**Depends on:** S5-02
**Test:** Set up route with unhealthy primary, healthy secondary → streaming falls back to secondary.

### S5-04 · Streaming: post-stream token reconciliation [BE] — 2h
**Refs:** AG-12 (partial)
**What:** After streaming completes, parse the final SSE data for usage/token counts (OpenAI format: `usage` field in last chunk). Write token count to the request log. Fall back to prompt/completion token estimation if not available.
**Files:** `routers/gateway.py:470-582`
**Test:** Stream a request → verify token count is populated in gateway_requests table (not NULL).

### S5-05 · Honor provider Retry-After headers [BE] — 1h
**Refs:** DF-16
**What:** In `services/gateway.py:976-978`, parse `Retry-After` header from 429 responses. Use `max(calculated_backoff, retry_after_seconds)` for the wait.
**Files:** `services/gateway.py:976-978`
**Test:** Mock 429 with `Retry-After: 30` → verify gateway waits 30s, not 4s cap.

### S5-06 · Guardrail bypass requires platform admin + audit [BE] — 1h
**Refs:** DF-15
**What:** In the endpoint that sets `guardrail_bypass` on workspace model (`models/tenant.py:112`), add check for platform admin role. Generate audit log entry when bypass is toggled.
**Files:** `models/tenant.py:112`, relevant router
**Test:** Workspace admin tries to set bypass → 403. Platform admin → success + audit entry.

---

# SPRINT 6 — SIDEBAR + PAGE CONSOLIDATION (Days 12-15)

UI restructuring. Can be done in parallel with Sprint 5 if you have a frontend person.

---

### S6-01 · Add missing pages to sidebar [UI] — 1h
**Refs:** UI-08, UI-09
**What:** Add `access-groups`, `response-cache`, `search-tools`, `tags`, `tool-policies`, `security`, and `guardrails` to sidebar under appropriate sections per the UI audit recommendations.
**Files:** `apps/web/components/layout/Sidebar.tsx`
**Test:** Every listed page is reachable from the sidebar.

### S6-02 · Expose ecosystem pages to org admins [UI] — 1h
**Refs:** UI-11
**What:** In sidebar config, show `integrations`, `otlp`, `mcp-registry`, `plugins`, `ai-hub` to org admin and org manager roles, not just platform admin.
**Files:** `apps/web/components/layout/Sidebar.tsx`
**Test:** Log in as org admin → see ecosystem pages in sidebar.

### S6-03 · Fix chargeback sidebar permission [UI] — 30 min
**Refs:** UI-10
**What:** Gate chargeback sidebar entry on org-level billing permission (not workspace admin). Show "Access required" state if user navigates directly.
**Files:** `Sidebar.tsx`, `chargeback/page.tsx`
**Depends on:** S6-01
**Test:** Workspace admin → no chargeback in sidebar. Org billing admin → visible.

### S6-04 · Fix integration status cards [UI] — 1h
**Refs:** UI-12
**What:** In integrations page, change status for Email/SMTP, S3/MinIO Backup, LiteLLM, LangGraph, REST webhook from "Planned" to "Available". Add setup anchors.
**Files:** `apps/web/app/(dashboard)/integrations/page.tsx`
**Test:** Open integrations → shipped features show "Available".

### S6-05 · Consolidate billing pages [UI] — 2h
**Refs:** FC-09
**What:** Add "Summary" and "Periods" tabs to `/billing` page. Move billing-summary content into the Summary tab. Set up redirect from `/billing-summary` → `/billing?tab=summary`.
**Files:** `apps/web/app/(dashboard)/billing/page.tsx`, `billing-summary/page.tsx`
**Test:** Navigate to `/billing-summary` → redirected. Both views accessible via tabs.

### S6-06 · Consolidate budget pages [UI] — 2h
**Refs:** FC-10
**What:** Add "Budgets", "Tiers", "Overrides", "Model Budgets" tabs to `/budgets` page. Move content from `budget-tiers`, `budget-overrides`, `model-budgets` pages into tabs. Redirect old URLs.
**Files:** `apps/web/app/(dashboard)/budgets/page.tsx` and 3 sub-pages
**Test:** Navigate to `/budget-tiers` → redirected to `/budgets?tab=tiers`. All content accessible.

### S6-07 · Consolidate experiment pages [UI] — 3h
**Refs:** FC-04
**What:** Make `/evaluation` the canonical home with tabs: Datasets, Experiments, Evaluators, Replay. Redirect `/experiments` → `/evaluation?tab=experiments`, `/replay` → `/evaluation?tab=replay`. Remove redundant sidebar entries.
**Files:** `apps/web/app/(dashboard)/evaluation/page.tsx`, sidebar config
**Depends on:** S6-01
**Test:** All experiment workflows reachable from one page. Old URLs redirect.

### S6-08 · Merge evaluations score submission into Evaluation Studio [UI] — 1h
**Refs:** FC-07
**What:** Add "Quick Score" tab to `/evaluation`. Redirect `/evaluations` → `/evaluation?tab=scores`.
**Files:** `apps/web/app/(dashboard)/evaluations/page.tsx`, `evaluation/page.tsx`
**Depends on:** S6-07
**Test:** Navigate to `/evaluations` → redirected. Score submission works from tab.

### S6-09 · Sidebar collapse — reduce to ~28 items [UI] — 3h
**Refs:** UI-01
**What:** Apply the recommended 7-section structure from the UI audit. Collapse merged pages into parent entries. Remove entries that are now tabs. Final sections: Observe, Build & Improve, Gateway & Routing, Safety & Governance, FinOps, Organization, Platform.
**Files:** `apps/web/components/layout/Sidebar.tsx`
**Depends on:** S6-01 through S6-08
**Test:** Count sidebar items ≤ 30. All pages still reachable. No broken links.

---

# SPRINT 7 — RBAC + AUTH HARDENING (Days 15-17)

---

### S7-01 · Layout-level RBAC guard [UI] — 3h
**Refs:** UI-02
**What:** In `apps/web/app/(dashboard)/layout.tsx`, add a route→permission mapping. On each page load, check `useRole()` against the mapping. Render an "Access Denied" component for unauthorized routes. Cover all ~80 routes.
**Files:** `apps/web/app/(dashboard)/layout.tsx`, create `lib/routePermissions.ts`
**Test:** Navigate directly to `/gateway` as non-admin → "Access Denied". Admin → normal page.

### S7-02 · Refactor direct fetch() to apiFetch [UI] — 1h
**Refs:** UI-05
**What:** Replace `fetch()` calls in `organization/page.tsx` and `workspace/page.tsx` with `apiFetch<T>()`.
**Files:** 2 page files
**Test:** Both pages still load correctly. API errors show proper error handling.

### S7-03 · Delete ~50 dead API functions [UI] — 2h
**Refs:** FC-05
**What:** Grep for each exported function in `api.ts` to find unused ones. Delete dead clusters: data warehouse connector (8), invoicing (7), billing webhooks (4), subscription/checkout (2), legacy experiments (5), admin tenant CRUD (7), and any others confirmed unused.
**Files:** `apps/web/lib/api.ts`
**Test:** `npm run build` — no missing import errors. Grep confirms deleted functions were unused.

---

# SPRINT 8 — FK CONSTRAINTS + BUDGET UNIFICATION (Days 17-21)

The big structural fix. Backend-only.

---

### S8-01 · FK constraints: financial models [BE] — 2h
**Refs:** AG-05 (partial)
**What:** Alembic migration adding FKs for: `BudgetOverride.budget_id → budgets.id`, `BudgetBreach.budget_id → budgets.id`, `ModelBudget.api_key_id → api_keys.id`, `ApiKey.budget_tier_id → budget_tiers.id`, `UsageSnapshot.billing_period_id → billing_periods.id`. Validate data first (query for orphans, delete or log them).
**Files:** New migration, financial model files
**Depends on:** S0-04 (models registered)
**Test:** Migration runs cleanly. Attempt insert with invalid FK → rejected.

### S8-02 · FK constraints: organizational models [BE] — 2h
**Refs:** AG-05 (partial)
**What:** Add FKs for: `Project.workspace_id → workspaces.id`, `ProjectKey.project_id → projects.id`, `ProjectKey.api_key_id → api_keys.id`, `TeamModel.workspace_id → workspaces.id`, `AccessGroupMember.group_id → access_groups.id`, `AccessGroupMember.user_id → users.id`. Orphan cleanup first.
**Files:** New migration, org model files
**Depends on:** S0-04
**Test:** Migration runs. Cascade delete workspace → projects deleted.

### S8-03 · FK constraints: operational models [BE] — 2h
**Refs:** AG-05 (partial)
**What:** Add FKs for: `GuardrailEvent/TestCase/Alert.guardrail_rule_id`, `ProviderCall.workspace_id/span_id`, `ToolCall.workspace_id`, `UsageHourly/Daily.workspace_id`, `WorkflowRun.workflow_id`, `WorkflowStep.run_id`, `AgentMemory.agent_id`. Orphan cleanup first.
**Files:** New migration, operational model files
**Depends on:** S0-04
**Test:** Migration runs. All FKs enforced.

### S8-04 · Budget unification: merge BudgetTier into Budget [BE] — 4h
**Refs:** AG-03 (partial)
**What:** (1) Add `scope_type = "api_key"` support to the main Budget model. (2) Migrate existing BudgetTier rows into Budget table with scope_type="api_key". (3) Update `check_cost_cap` to query Budget table instead of BudgetTier. (4) Keep BudgetTier model temporarily for backward compat reads, mark deprecated.
**Files:** `models/budgets.py`, `models/budget_tiers.py`, `services/gateway_controls.py`, migration
**Depends on:** S8-01
**Test:** Existing budget tier enforcement still works. New budgets created via unified model.

### S8-05 · Budget unification: merge ModelBudget into Budget [BE] — 2h
**Refs:** AG-03 (partial)
**What:** Add `model_id` filter support to Budget. Migrate existing ModelBudget rows as Budget entries with scope_type="api_key" + model_id filter. Deprecate ModelBudget.
**Files:** `models/budgets.py`, `models/model_budgets.py`, migration
**Depends on:** S8-04
**Test:** Model-level budget enforcement works via unified Budget.

### S8-06 · Budget unification: wire unified check into gateway [BE] — 3h
**Refs:** AG-04
**What:** Consolidate `check_cost_cap` and `check_budgets` into one `enforce_budget()` function. Call it from both gateway paths (streaming and non-streaming). Use Redis counters from S2-04.
**Files:** `services/gateway_controls.py`, `services/budgets.py`, `routers/gateway.py:488,629`
**Depends on:** S8-04, S8-05, S2-04
**Test:** Set budget with scope=workspace → gateway enforces it. Set budget with scope=api_key → gateway enforces it. Both paths (streaming/non-streaming) check.

### S8-07 · Validate budget scope_id references [BE] — 2h
**Refs:** AG-07
**What:** In budget create/update endpoints, validate that `scope_id` references a real entity based on `scope_type`: workspace→workspaces table, end_user→users, app→applications, api_key→api_keys.
**Files:** `routers/budgets.py`, `routers/phase16_deferred.py`
**Depends on:** S8-04
**Test:** Create budget with non-existent scope_id → 400 error.

---

# SPRINT 9 — PLUGIN SYSTEM + APPROVALS (Days 21-23)

---

### S9-01 · Implement plugin webhook dispatch [BE] — 3h
**Refs:** AG-19
**What:** In `services/plugin_runner.py`, replace `log.info(...)` body with actual HTTP POST to the plugin's configured URL. Include request context in payload. Record response status and latency in `PluginExecution`. Propagate `block` responses.
**Files:** `services/plugin_runner.py`
**Test:** Configure plugin with webhook URL → trigger hook → verify POST received and response recorded.

### S9-02 · Wire plugin governance into approvals [BE] — 2h
**Refs:** AG-20
**What:** When `govern_and_filter_tool_call` detects a violation, create an `ApprovalRequest` row using the existing `Approval` model. Send notification (use existing notification service if available). Return "pending_approval" status to caller.
**Files:** `services/plugin_runner.py`, `models/approvals.py`
**Depends on:** S9-01
**Test:** Tool governance violation → ApprovalRequest created → visible in /approvals UI.

### S9-03 · Wire tool policy require_approval action [BE] — 2h
**Refs:** FC-14
**What:** In the tool execution path, check tool policies for `action=require_approval`. When found, create ApprovalRequest and block execution until resolved.
**Files:** `services/plugin_runner.py`, `models/approvals.py`
**Depends on:** S9-02
**Test:** Set tool policy with require_approval → tool call blocked → approve → tool executes.

---

# SPRINT 10 — INFRA + WORKER HARDENING (Days 23-25)

---

### S10-01 · Split Celery into fast/slow workers [INF] — 2h
**Refs:** AG-15
**What:** (1) In `core/celery_app.py`, define two queues: `fast` and `slow`. Route cost enrichment, alerting, budget sync to `fast`. Route ML forecast, retention, data warehouse to `slow`. (2) In `docker-compose.yml`, create two worker services: `worker-fast` with `--pool=prefork --concurrency=4 -Q fast` and `worker-slow` with `--pool=prefork --concurrency=2 -Q slow`.
**Files:** `core/celery_app.py`, `docker-compose.yml`
**Test:** Start both workers. Submit fast task → processed immediately even when slow task is running.

### S10-02 · Add worker/beat health checks [INF] — 1h
**Refs:** AG-17
**What:** Add health check commands to docker-compose: worker uses `celery inspect ping`, beat uses timestamp file check (beat writes timestamp to `/tmp/celery-beat-alive` every 30s, health check verifies file age < 90s).
**Files:** `docker-compose.yml`, Helm chart
**Test:** Kill worker process → health check fails within 30s. Running worker → health check passes.

### S10-03 · Add core images to CI [INF] — 2h
**Refs:** AG-18
**What:** Add `runledger-api`, `runledger-worker`, `runledger-beat`, `runledger-web` image builds to `.github/workflows/images.yml`. Build on push to main and on tags.
**Files:** `.github/workflows/images.yml`
**Test:** Push to main → CI builds all 4 images.

### S10-04 · Add test coverage measurement [INF] — 1h
**Refs:** GH-02
**What:** Add `pytest-cov` to dev dependencies. Create `.coveragerc` with source paths and omit patterns. Add `--cov --cov-fail-under=40` to pytest config. Wire into CI.
**Files:** `requirements-dev.txt`, `.coveragerc`, `pytest.ini` or `pyproject.toml`
**Test:** `pytest --cov` → coverage report generated. Below 40% → fail.

---

# SPRINT 11 — SECURITY HARDENING (Days 25-28)

---

### S11-01 · Provider API key encryption: envelope crypto [BE] — 4h
**Refs:** DF-10
**What:** (1) Create `services/crypto.py` with envelope encryption: generate DEK, encrypt DEK with KEK from env/vault, store encrypted DEK + ciphertext. (2) Add `encrypted_config` column to provider-related models. (3) Encrypt on write, decrypt on read in gateway_providers.py. (4) Migration to encrypt existing plaintext keys.
**Files:** Create `services/crypto.py`, `services/gateway_providers.py:118-123,209-219`, migration
**Test:** Store provider key → DB contains ciphertext. Gateway call → decrypts and uses key successfully.

### S11-02 · Tenant isolation middleware [BE] — 4h
**Refs:** DF-12
**What:** Create SQLAlchemy event listener that auto-injects `workspace_id` filter on all SELECT queries for models with a `workspace_id` column. Set workspace context from the authenticated request. Log warnings for queries missing workspace scope.
**Files:** Create `middleware/tenant_isolation.py`, modify session setup
**Test:** Query without explicit workspace_id → middleware adds it. Cross-tenant data access → blocked.

### S11-03 · Audit log hash chain [BE] — 3h
**Refs:** DF-14
**What:** (1) Add `previous_hash` column and `entry_hash` column to audit model. (2) On each insert, compute SHA-256 of (previous_hash + event_data) and store as entry_hash. (3) Change `created_at` from Python `default` to `server_default=func.now()`. (4) Add verification function to check chain integrity.
**Files:** `models/audit.py`, migration
**Test:** Insert 3 audit entries → verify chain. Tamper with middle entry → verification fails.

---

# SPRINT 12 — UI POLISH (Days 28-31)

Independent UI improvements. All parallelizable.

---

### S12-01 · Workspace switcher in header [UI] — 2h
**Refs:** UI-03 (partial)
**What:** Add a workspace selector dropdown to the app header component. Persist selection in localStorage. Pass workspace_id to API calls.
**Files:** App header component, API client
**Test:** Switch workspace → all data pages reflect new workspace.

### S12-02 · Add scope bar to analytics pages [UI] — 2h
**Refs:** UI-03 (partial)
**What:** Add `DashboardScopeBar` to: Analytics, Engineering, Model Usage, Cost Savings, Outcomes, Billing pages. Wire time range and scope filters into existing API calls.
**Files:** 6 page.tsx files
**Depends on:** S12-01
**Test:** Each page has scope bar. Changing time range updates data.

### S12-03 · Add feature_tag and api_key filters [UI] — 3h
**Refs:** UI-14
**What:** Extend `DashboardScopeBar` with feature_tag combobox and api_key selector. Wire into all analytics page API calls. Fetch available feature_tags and api_keys from API.
**Files:** `DashboardScopeBar.tsx`, analytics page files
**Depends on:** S12-02
**Test:** Filter by feature_tag → data scoped. Filter by api_key → data scoped.

### S12-04 · Standardize naming: workspace → organization/team [UI] — 3h
**Refs:** UI-07
**What:** Find-and-replace user-visible labels: "workspace" → "team" (for group within org), "organization" → "organization" (keep). Fix sidebar "Teams / Workspaces" → "Teams". Fix plurality inconsistencies.
**Files:** Multiple .tsx files (UI labels only, not API field names)
**Test:** No user-visible "workspace" labels remain (except in technical settings).

### S12-05 · MCP page consolidation [UI] — 2h
**Refs:** FC-06
**What:** Make `/mcp-registry` the canonical MCP management page. Convert `/mcp` into a "Setup Guide" tab within the registry page. Redirect `/mcp` → `/mcp-registry?tab=setup`.
**Files:** `mcp-registry/page.tsx`, `mcp/page.tsx`
**Test:** Navigate to `/mcp` → redirected. Setup guide accessible as tab.

### S12-06 · Tags page: link to feature_tag system [UI] — 1h
**Refs:** FC-08
**What:** Add explanatory text distinguishing organizational tags from runtime feature_tags. Add "View feature tag usage →" link to analytics filtered by feature_tag.
**Files:** `apps/web/app/(dashboard)/tags/page.tsx`
**Test:** Tags page clearly explains the difference.

---

# SPRINT 13 — GATEWAY ADVANCED + ML (Days 31-34)

---

### S13-01 · Wire trained complexity model into routing [BE] — 2h
**Refs:** AG-23
**What:** In `services/routing.py:643-655`, load the persisted GradientBoostingRegressor from `services/ml/complexity.py`. Use it for complexity scoring in `complexity_based` routing strategy. Fall back to `total_chars // 4` only when no trained model exists.
**Files:** `services/routing.py:643-655`, `services/ml/complexity.py`
**Test:** With trained model → uses ML score. Without → uses heuristic. Routing decisions change.

### S13-02 · Bedrock streaming: use async SDK [BE] — 3h
**Refs:** DF-17
**What:** Replace synchronous `asyncio.to_thread` chunk collection in `services/gateway_providers.py:452-476` with async Bedrock `invoke_model_with_response_stream`. Yield chunks as they arrive for real streaming.
**Files:** `services/gateway_providers.py:452-476`
**Test:** Stream from Bedrock → first token arrives before generation completes. Measure TTFT improvement.

### S13-03 · Simplify Project model [BE] — 2h
**Refs:** CL-05
**What:** Redefine Project as: name, description, workspace_id (with FK), and assigned API keys (via ProjectKey with proper FKs). Remove team dropdown. Project becomes a grouping label, not a financial entity.
**Files:** `models/projects.py`, `routers/projects.py`
**Depends on:** S3-03, S8-02
**Test:** Project CRUD works. ProjectKey has proper FKs. No budget or team fields.

### S13-04 · UI: Simplify Projects page [UI] — 2h
**Refs:** CL-05
**What:** Update Projects page to match simplified model: name, description, assigned API keys. Remove team dropdown. Add "Manage budgets →" link.
**Files:** `apps/web/app/(dashboard)/projects/page.tsx`
**Depends on:** S13-03
**Test:** Projects page shows simplified form. No team/budget fields.

---

# SPRINT 14 — TENANT-LEVEL + GOVERNANCE (Days 34-37)

---

### S14-01 · Add tenant_id to financial models [BE] — 3h
**Refs:** AG-08
**What:** Add nullable `tenant_id` FK to `Budget`, `BillingPeriod`, `AlertRule`. When set, budget/billing/alert operates at org level across all workspaces.
**Files:** `models/budgets.py`, `models/billing.py`, `models/alerts.py`, migration
**Depends on:** S8-04
**Test:** Create org-level budget → applies across workspaces.

### S14-02 · Add org-level aggregation endpoints [BE] — 2h
**Refs:** AG-08
**What:** Add `GET /org/budgets/rollup` (aggregate spend across workspaces) and `GET /org/billing/summary` (org-level billing summary).
**Files:** `routers/billing.py` or new `routers/org.py`
**Depends on:** S14-01
**Test:** Call rollup → get org-wide budget summary.

### S14-03 · Governance pack enforcement [BE] — 2h
**Refs:** FC-16
**What:** Add `enforcement_mode` field to governance pack model (values: `advisory`, `mandatory`). When mandatory, prevent individual rule disable while pack is active.
**Files:** Governance pack model and router
**Test:** Create mandatory pack → try to disable individual rule → rejected.

### S14-04 · Playground: route through gateway [UI+BE] — 3h
**Refs:** FC-11
**What:** Change playground page to send requests through the gateway endpoint instead of direct provider calls. Track playground usage as workspace spend.
**Files:** `apps/web/app/(dashboard)/playground/page.tsx`, possibly `routers/playground.py`
**Test:** Playground request → appears in runs/analytics. Cost tracked.

---

# SPRINT 15 — TESTING FOUNDATION (Days 37-40)

---

### S15-01 · Integration test infrastructure [INF] — 2h
**Refs:** GH-01 (partial)
**What:** Create `docker-compose.test.yml` with Postgres and Redis. Create `tests/integration/conftest.py` with database setup/teardown fixtures. Create `tests/integration/__init__.py`.
**Files:** `docker-compose.test.yml`, `tests/integration/conftest.py`
**Test:** `docker compose -f docker-compose.test.yml up -d && pytest tests/integration/` → infrastructure starts.

### S15-02 · Integration test: ingest → cost enrichment [BE] — 2h
**Refs:** GH-01 (partial)
**What:** Write integration test: submit agent run via API → trigger cost enrichment worker → verify cost calculated and stored in DB.
**Files:** `tests/integration/test_ingest_flow.py`
**Depends on:** S15-01
**Test:** Test passes against real Postgres/Redis.

### S15-03 · Integration test: budget check → breach [BE] — 2h
**Refs:** GH-01 (partial)
**What:** Write integration test: create budget → submit runs until budget exceeded → verify breach recorded and enforcement triggered.
**Files:** `tests/integration/test_budget_flow.py`
**Depends on:** S15-01
**Test:** Test passes. Budget breach correctly detected.

### S15-04 · Integration test: billing close → chargeback [BE] — 2h
**Refs:** GH-01 (partial)
**What:** Write integration test: create billing period → submit runs → close period → generate chargeback report → verify attribution.
**Files:** `tests/integration/test_billing_flow.py`
**Depends on:** S15-01, S4-01
**Test:** Test passes. Chargeback attribution matches actual spend.

### S15-05 · Benchmark pass/fail thresholds [DOC] — 1h
**Refs:** SS-04
**What:** Add configurable thresholds to `scripts/bench/run_benchmark.py`: p99 < 500ms, throughput > 100 RPS. Return exit code 1 on failure.
**Files:** `scripts/bench/run_benchmark.py`
**Test:** Run benchmark → pass/fail reported. CI can gate on it.

---

# SPRINT 16 — EXPORT + ONBOARDING (Days 40-43)

---

### S16-01 · Server-side export: runs [BE] — 2h
**Refs:** UI-13 (partial)
**What:** Add `GET /runs/export?format=csv|json` with streaming response. Accept same filters as runs list. Use `StreamingResponse` with chunked encoding.
**Files:** `routers/runs.py`
**Test:** Export 10k runs → CSV downloads without browser crash.

### S16-02 · Server-side export: analytics + billing [BE] — 2h
**Refs:** UI-13 (partial)
**What:** Add export endpoints for analytics summary and billing summary. Same streaming pattern.
**Files:** `routers/analytics.py`, `routers/billing.py`
**Test:** Export endpoints return valid CSV/JSON.

### S16-03 · Wire frontend exports to server endpoints [UI] — 2h
**Refs:** UI-13
**What:** Replace client-side CSV/JSON generation in Runs, Analytics, Billing Summary, and Chargeback pages with fetch calls to server export endpoints. Show download progress.
**Files:** 4 page.tsx files
**Depends on:** S16-01, S16-02
**Test:** Click export → downloads from server, not generated in browser.

### S16-04 · First-run onboarding wizard [UI] — 4h
**Refs:** UI-06
**What:** Create `FirstRunWizard.tsx` component. Detect empty workspace (no runs, no routes). Show 4-step flow: copy API key → configure first route → send test request → view run result. Dismiss permanently after completion.
**Files:** Create `apps/web/components/onboarding/FirstRunWizard.tsx`, wire into dashboard layout
**Test:** New workspace → wizard appears. Complete all steps → wizard dismissed. Existing workspace → no wizard.

---

# SPRINT 17 — SCRIPTS + DOCS (Days 43-45)

---

### S17-01 · Add assertions to hosted scenario scripts [DOC] — 3h
**Refs:** SS-01 (partial)
**What:** Add HTTP status code assertions and response schema validation to scripts under `scripts/scenarios/hosted/`. Each script should fail loudly on unexpected responses.
**Files:** `scripts/scenarios/hosted/*.py`
**Test:** Run scripts against running API → all assertions pass. Break an endpoint → script fails with clear error.

### S17-02 · Add assertions to ollama scenario scripts [DOC] — 3h
**Refs:** SS-01 (partial)
**What:** Same as S17-01 for `scripts/scenarios/ollama/*.py`.
**Files:** `scripts/scenarios/ollama/*.py`
**Test:** Scripts validate responses.

### S17-03 · Document deployment profiles [DOC] — 2h
**Refs:** GH-08
**What:** Create deployment guide documenting: minimal (5 containers: API, worker, beat, Postgres, Redis), recommended (10: + web, Kafka, MinIO, OTEL collector, optimization-api), full (21: all services). Include docker-compose profile flags.
**Files:** `docs/deployment-profiles.md`, update `docker-compose.yml` with profile labels
**Test:** `docker compose --profile minimal up` → 5 containers. Document matches reality.

### S17-04 · Demo mode: add is_demo flag [BE] — 2h
**Refs:** SS-02
**What:** Add `is_demo: bool = False` column to AgentRun, GatewayRequest, and other tables populated by demo seeder. Update `services/demo_mode.py` to set flag. Add `DELETE /admin/demo-data` cleanup endpoint.
**Files:** `services/demo_mode.py`, model files, migration
**Test:** Run demo seeder → rows have is_demo=True. Cleanup endpoint → demo rows deleted, real data untouched.

---

# SPRINT 18 — NICE TO HAVE (Days 45+)

These are independent improvements. Pick based on priority.

---

### S18-01 · Optimization simulator: live pricing [UI] — 2h
**Refs:** SS-03
**What:** Replace hardcoded pricing in optimization simulator with API calls to provider profiles for current pricing.
**Files:** `apps/web/app/(dashboard)/optimization-simulator/page.tsx`

### S18-02 · Rate limits: real management page [UI] — 3h
**Refs:** UI-04
**What:** Replace static reference table with real management UI: view current limits per key, configure custom limits, see usage vs limit.
**Files:** `apps/web/app/(dashboard)/rate-limits/page.tsx`

### S18-03 · A/B test results tab for gateway [UI] — 3h
**Refs:** GH-10
**What:** Add "Experiment Results" tab to gateway page. Show per-variant metrics (latency, cost, quality), z-test significance, promotion button.
**Files:** `apps/web/app/(dashboard)/gateway/page.tsx`

### S18-04 · Canary auto-rollback [BE] — 2h
**Refs:** GH-11
**What:** Add `error_rate_threshold` to canary routing config. Monitor error rate per window. Auto-revert routing weights when exceeded.
**Files:** `services/routing.py`, `services/gateway.py`

### S18-05 · Vector stores: document upload + query testing [UI] — 3h
**Refs:** GH-13
**What:** Add document upload form and search/query testing interface to vector stores page.
**Files:** `apps/web/app/(dashboard)/vector-stores/page.tsx`

### S18-06 · Alert acknowledgment workflow [BE+UI] — 4h
**Refs:** GH-09
**What:** Add state machine to alerts: fired → acknowledged → resolved. Add ack/resolve buttons to monitoring page. Optional webhook to PagerDuty/OpsGenie on fire.
**Files:** Alert model, monitoring page, webhook service

### S18-07 · PII scrubbing expansion [BE] — 4h
**Refs:** GH-05
**What:** Integrate Microsoft Presidio for NER-based PII detection. Add non-US patterns (passport, IBAN, national ID formats). Add configurable scrubbing profile per workspace.
**Files:** `services/scrubbing.py`, requirements

### S18-08 · Search tools + vector stores consolidation [UI] — 1h
**Refs:** FC-13
**What:** Add cross-links between search-tools and vector-stores pages. Add "Connected Vector Store" display on search tools.
**Files:** Both page.tsx files

### S18-09 · Policy dry run: full pipeline mode [BE+UI] — 4h
**Refs:** SS-06
**What:** Add "Full Pipeline" simulation mode that runs a test request through: guardrails → routing → budget check → rate limit → tool policies. Show per-stage pass/fail.
**Files:** Backend simulation endpoint, `policy-dry-run/page.tsx`

### S18-10 · Forecasting: walk-forward validation [BE] — 2h
**Refs:** GH-06
**What:** Replace in-sample MAPE selection with walk-forward cross-validation (train on first N points, test on next M, slide forward).
**Files:** `services/ml/forecast.py:315`

### S18-11 · Anomaly thresholds: per-workspace config [BE] — 2h
**Refs:** GH-07
**What:** Add workspace-level threshold overrides for Z-score and EWMA. Wire adaptive_alerts suggestions into auto-apply with admin approval.
**Files:** `services/ml/adaptive_alerts.py`, workspace model

---

# DEPENDENCY GRAPH

```
S0-04 ──→ S8-01, S8-02, S8-03

S2-04 ──→ S8-06

S3-01 ──→ S3-09, S4-05
S3-02 ──→ S3-10
S3-03 ──→ S3-06, S13-03
S3-04 ──→ S3-07
S3-05 ──→ S3-08

S4-01 ──→ S4-02, S4-03, S4-05, S15-04

S5-01 ──→ S5-02
S5-02 ──→ S5-03

S6-01 ──→ S6-03, S6-07
S6-07 ──→ S6-08
S6-01..S6-08 ──→ S6-09

S8-01 ──→ S8-04
S8-04 ──→ S8-05, S8-06, S8-07, S14-01

S9-01 ──→ S9-02
S9-02 ──→ S9-03

S12-01 ──→ S12-02
S12-02 ──→ S12-03

S13-03 ──→ S13-04

S14-01 ──→ S14-02

S15-01 ──→ S15-02, S15-03, S15-04

S16-01 ──→ S16-03
S16-02 ──→ S16-03
```

---

# TIMELINE SUMMARY

| Sprint | Days | Track | Tasks | Focus |
|---|---|---|---|---|
| **S0** | 1 | BE/INF | 8 | Runtime crashes + quick security fixes |
| **S1** | 2-3 | BE/INF | 6 | P0 security defects |
| **S2** | 3-5 | BE/INF | 5 | Guardrail sandbox + gateway performance |
| **S3** | 5-7 | BE+UI | 10 | Remove decorative team/project/budget fields |
| **S4** | 7-9 | BE | 7 | Chargeback + budget CRUD |
| **S5** | 9-12 | BE | 6 | Circuit breaker + streaming + retry |
| **S6** | 12-15 | UI | 9 | Sidebar restructure + page consolidation |
| **S7** | 15-17 | UI | 3 | RBAC guard + dead code cleanup |
| **S8** | 17-21 | BE | 7 | FK constraints + budget unification |
| **S9** | 21-23 | BE | 3 | Plugin system + approvals |
| **S10** | 23-25 | INF | 4 | Worker split + CI + coverage |
| **S11** | 25-28 | BE | 3 | Provider key encryption + tenant isolation + audit chain |
| **S12** | 28-31 | UI | 6 | Scope bar + filters + naming |
| **S13** | 31-34 | BE+UI | 4 | ML routing + Bedrock streaming + Project simplification |
| **S14** | 34-37 | BE+UI | 4 | Tenant-level ops + governance + playground |
| **S15** | 37-40 | BE/INF | 5 | Integration tests + benchmark |
| **S16** | 40-43 | BE+UI | 4 | Server-side export + onboarding wizard |
| **S17** | 43-45 | DOC/BE | 4 | Script assertions + deployment docs + demo mode |
| **S18** | 45+ | Mixed | 11 | Nice-to-have improvements |

**Total: 109 tasks across 19 sprints (~45 working days for one engineer, ~25 with backend/frontend split).**

**Parallelization guide:**
- Backend person: S0 → S1 → S2 → S3-BE → S4 → S5 → S8 → S9 → S11 → S13-BE → S14 → S15
- Frontend person: S3-UI → S6 → S7 → S12 → S13-UI → S16-UI
- Either: S10 (infra), S17 (docs/scripts), S18 (nice-to-have)
