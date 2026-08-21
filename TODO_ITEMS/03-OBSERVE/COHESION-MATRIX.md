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
| Observe | Analytics overview | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Analytics overview now accepts api_key_id filter for key-scoped cost attribution. API key footprint modal links to analytics overview. Workspace observe posture endpoint provides workspace-level analytics summary. |
| Observe | Runs list | `STRONG` | `N/A` | `STRONG` | `GAP` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Runs list now accepts api_key_id filter. API key footprint modal links to key-scoped runs. Workspace page links to runs. Onboarding now STRONG: has_first_run readiness check links to /runs, and the Observe & Monitor section includes a dedicated Runs navigation card. |
| Observe | Run detail | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Run detail inherits API key context from runs. Workspace page links to run investigation. |
| Observe | Request flow | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Request flow now accepts api_key_id filter. Workspace page links to request flow. |
| Observe | Request explorer | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Request explorer inherits api_key_id filter. Workspace page links to request investigation. |
| Observe | Model usage | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `N/A` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `N/A` | Model usage now accepts api_key_id filter for per-key model breakdown. Workspace page links to model usage. API key footprint returns models used. Users page now cross-links to Model Usage for user-scoped model investigation. |
| Observe | Analytics users | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Workspace page links to Analytics Users. Workspace observe posture includes active user count. |
| Observe | Telemetry | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | Telemetry is already correctly placed in Observe, with scope inheritance still improving. |
| Observe | Monitoring | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | Workspace page links to Monitoring. API key footprint modal links to monitoring scoped by key. |
| Observe | Model scorecards | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | Scorecards already align well with AI Hub and workspace model ownership. |

### 11.5c Observe x Gateway & Routing / Safety & Governance / Self

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Tool registry | Tool policies | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Analytics overview | Runs list | Request flow | Request explorer | Monitoring | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------------|---------------|-----------|--------------|----------|-------------|-----------|-----------------|------|--------------------|-----------|--------------|------------------|------------|---------|
| Observe | Analytics overview | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Analytics overview reflects general request health, but Guardrails and rate-limit posture still show up more as summarized runtime signals than as first-class overview control loops. |
| Observe | Runs list | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Runs list can expose guardrail-related outcomes indirectly, but Guardrails is still not a first-class investigative pivot from the main run list. |
| Observe | Run detail | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Run detail can surface guardrail effects indirectly through request evidence, but Guardrails still lacks a clean drillback from run detail into the runtime-protection surface. |
| Observe | Request flow | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Request Flow is one of the better places to follow guardrail impacts, but the guardrail workflow still resolves back into dedicated Guardrails evidence surfaces rather than staying native to request analysis. |
| Observe | Request explorer | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Request Explorer can help investigate guardrail-related request behavior, but the user still has to pivot into Guardrails for the real rule, event, and alert workflow. |
| Observe | Model usage | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Model Usage aggregates cached-token counts and cache-hit rate meaningfully, and it also has a real relationship to guardrails and rate limits because blocked, filtered, or throttled traffic changes how usage should be interpreted even if those controls are managed elsewhere. |
| Observe | Monitoring | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Monitoring can reflect guardrail-related runtime outcomes, but Guardrails still operates mainly through its own event and alert workflow rather than a unified monitoring control loop. |
| Observe | Telemetry | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Telemetry is now correctly treated as observability rather than integration setup. |
| Observe | Analytics economics | `STRONG` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Analytics economics includes cache-hit rate plus throughput and quota effects, but Response Cache and Rate Limits are still measured there more as outcome evidence than as directly managed economics controls. |
| Observe | Cost and savings | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Cost and Savings is tightly coupled to Response Cache because cache hits are a first-class savings attribution category with direct avoided-cost storytelling. |
