# Observe â€” Cohesion Matrix

Last updated: 2026-08-22

This file tracks how Observe features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

Current row major feature under audit: `Observe`

### 11.5 Observe Cohesion Matrix

This section applies the same matrix structure to `Observe` against the rest of the shipped feature surface.

Current row major feature under audit: `Observe`

### 11.5a Observe x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| Observe | Analytics overview | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Analytics overview consumes economics context well, but it is still not anchored cleanly to the FinOps control plane. |
| Observe | Runs list | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Runs should become easier to explain through budget, quota, allocation, and ledger evidence context. |
| Observe | Run detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Run detail has the raw data to support FinOps explanations, including ledger-facing spend evidence, but the product bridges are still thin. |
| Observe | Request flow | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Request Flow is a natural place to visualize financial, quota, and ledger impacts, but that linkage is still immature. |
| Observe | Request explorer | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Request Explorer should be one of the strongest surfaces for cost attribution, budget debugging, and ledger drillback. |
| Observe | Model usage | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Model Usage already shares a strong natural relationship with provider cost, but budget, billing, and ledger bridges can deepen. |
| Observe | Analytics economics | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Observe is already strongest where it overlaps with economics and billing, which is a good base for deeper FinOps cohesion. |
| Observe | Cost and savings | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Cost and Savings is already a natural FinOps companion and should keep tightening to the budget control plane. |
| Observe | Outcomes and ROI | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Outcomes and ROI should become a clearer top-layer consumer of spend, chargeback, and ledger data. |
| Observe | Monitoring | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Monitoring should increasingly show the operational consequences of spend controls and thresholds. |

### 11.5b Observe x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| Observe | Analytics overview | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `N/A` | `N/A` | MCP Registry and AI hub pages link directly to Analytics. MCP tool call activity and model catalog usage flow into analytics overview aggregates. |
| Observe | Runs list | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | MCP Registry and AI hub pages link directly to Runs. MCP tool calls and model catalog traffic generate runs. GET /analytics/ai-hub-runtime-posture returns run_count_30d. Users is PARTIAL because user activity generates runs but the Users page does not expose user-scoped run filtering directly. |
| Observe | Run detail | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `N/A` | `N/A` | MCP tool calls and model catalog traffic generate runs with drill-through to detail. MCP Registry and AI hub pages link to Runs for investigation. |
| Observe | Request flow | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `N/A` | `N/A` | MCP Registry and AI hub pages link directly to Request Flow. MCP tool calls and model catalog traffic flow into request analysis. |
| Observe | Request explorer | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `N/A` | `N/A` | MCP Registry and AI hub pages link directly to Request Explorer. MCP tool calls and model catalog traffic are investigable in request explorer. |
| Observe | Model usage | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `N/A` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `N/A` | Model usage now accepts api_key_id filter for per-key model breakdown. Workspace page links to model usage. API key footprint returns models used. Users page now cross-links to Model Usage for user-scoped model investigation. |
| Observe | Analytics users | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Workspace page links to Analytics Users. Workspace observe posture includes active user count. |
| Observe | Telemetry | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | Telemetry is already correctly placed in Observe, with scope inheritance still improving. |
| Observe | Monitoring | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Workspace page links to Monitoring. API key footprint modal links to monitoring scoped by key. |
| Observe | Model scorecards | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | Scorecards already align well with AI Hub and workspace model ownership. |

### 11.5c Observe x Gateway & Routing / Safety & Governance / Self

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Tool registry | Tool policies | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Analytics overview | Runs list | Request flow | Request explorer | Monitoring | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------------|---------------|-----------|--------------|----------|-------------|-----------|-----------------|------|--------------------|-----------|--------------|------------------|------------|---------|
| Observe | Analytics overview | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | GET /analytics/provider-profile-observe-posture returns provider-scoped 30-day traffic, cost, and latency. Provider Profiles page links to Analytics Overview. Analytics overview now has a direct provider-profile investigation bridge. |
| Observe | Runs list | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails observe posture returns evaluation breakdown (blocks, modifications, allows) and latency impact. Guardrails page links to Runs. Guardrail enforcement outcomes now surface in run investigation alongside cache and throttle context. |
| Observe | Run detail | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails observe posture returns enforcement outcomes and latency impact. Guardrail block/modify decisions now surface in run detail alongside cache and throttle context. |
| Observe | Request flow | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails observe posture returns enforcement outcomes. Guardrails page links to Request Flow. Guardrail block/modify decisions now surface alongside cache and throttle context in request flow analysis. |
| Observe | Request explorer | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails observe posture returns enforcement outcomes. Guardrails page links to Request Explorer. Guardrail outcomes now surface as a first-class filter dimension in request exploration. |
| Observe | Model usage | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Gateway observe posture returns cache hit rate and distinct model count. Model usage now consumes cache posture as a first-class dimension through the gateway observe bridge. Rate limits remain PARTIAL because throttle evidence is still consumed indirectly. |
| Observe | Monitoring | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails observe posture returns firing rates, block/modify rates, and latency impact. Guardrails page links to Monitoring. Guardrail enforcement rates now surface as first-class monitoring signals alongside cache and throttle health. |
| Observe | Telemetry | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Telemetry is now correctly treated as observability rather than integration setup. |
| Observe | Analytics economics | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Gateway observe posture returns cost, savings, cache hit rate, and throttle metrics. Analytics economics now consumes gateway, cache, and throttle posture as first-class dimensions. Gateway Observe Posture card links to Economics. |
| Observe | Cost and savings | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Gateway observe posture returns total cost and savings. Gateway Observe Posture card links to Cost & Savings. Cache savings and throttle-avoided spend now surface as first-class dimensions in cost attribution. |
