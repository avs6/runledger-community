# FinOps — Cohesion Matrix

Last updated: 2026-08-25 (03-OBSERVE WU-014)

This file tracks how FinOps features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

This first populated matrix follows the diagram pattern more closely while staying readable in Markdown:

- left side = audited major feature plus its subfeatures
- top side = major/minor features from the other feature families
- cells = current cohesion state for the relationship
- because Markdown tables cannot merge header cells like the sketch, each column is labeled as `Major Feature: Minor Feature`
- because one true mega-table would be too wide to audit properly, the full column set is split into aligned sub-matrices by feature family

Current row major feature under audit: `FinOps`

### 11.2a FinOps x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| FinOps | Budgets | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | Telemetry downstream posture now returns budget_count. Telemetry page links to Budgets. Users page cross-links to Budgets for user-scoped spend accountability. AI hub drills into model-scoped budgets via cost posture endpoint. |
| FinOps | Budget detail | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | Telemetry downstream posture returns budget_count which includes budget detail scope. Telemetry page links to Budgets. Users page cross-links to Budgets. AI hub cost posture drills through to budget detail. |
| FinOps | Budget overrides | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | Telemetry downstream posture returns budget_count encompassing overrides. Telemetry page links to Budgets. Budget overrides are workspace-scoped. Workspace page links to Budgets. |
| FinOps | Budget notifications | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | GET /analytics/ai-hub-runtime-posture returns budget_notification_count. AI hub now surfaces budget notification count through the runtime posture endpoint. Telemetry downstream posture also returns budget_notification_count. |
| FinOps | Billing periods | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | Telemetry downstream posture returns active_billing_periods. Telemetry page links to Billing Periods. Users page cross-links to Billing Periods. AI hub cost posture shows billing period count. Workspace page links directly to Billing Periods. |
| FinOps | Billing period detail | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | Telemetry downstream posture returns active_billing_periods encompassing detail scope. Telemetry page links to Billing Periods. Users page cross-links to Billing Periods. Workspace page links to Billing Periods. |
| FinOps | Chargeback | `STRONG` | `N/A` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | MCP Registry page links to Chargeback. GET /analytics/mcp-registry-posture returns chargeback_rule_count. MCP tool execution generates attributable usage flowing into chargeback. Telemetry downstream posture also returns chargeback_rule_count. |
| FinOps | Ledger | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | AI hub page links to Ledger. Model catalog usage generates financial evidence that flows into ledger entries. Telemetry page also links to Ledger. Workspace page links to Ledger. |

### 11.2b FinOps x Gateway & Routing

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------|
| FinOps | Budgets | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | GET /analytics/guardrails-finops-posture returns budget count. Guardrails page FinOps Posture card links to Budgets. Gateway FinOps Posture card also links to Budgets. Guardrail block/modify outcomes influence avoided-spend attribution. |
| FinOps | Budget detail | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | GET /analytics/guardrails-finops-posture returns budget count. Guardrails page FinOps Posture card links to Budget Detail. Gateway FinOps Posture card also links to Budget Detail. Budget performance posture returns cache/throttle economics. |
| FinOps | Budget overrides | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `STRONG` | Gateway FinOps Posture card shows override count/active and links to Budget Overrides. GET /analytics/response-cache-economics-posture returns budget override count. Cache Economics card links to Budget Overrides. Cache savings interact with override-adjusted spend thresholds. |
| FinOps | Budget notifications | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | GET /analytics/response-cache-economics-posture and rate-limit-scope-posture return budget notification count. Cache Economics and Rate Limit Scope cards link to Budget Notifications. Cache savings and throttle impacts feed into notification threshold calculations. |
| FinOps | Billing periods | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | GET /analytics/guardrails-finops-posture returns billing period count. Guardrails page FinOps Posture card links to Billing Periods. Gateway FinOps Posture card also links to Billing Periods. |
| FinOps | Billing period detail | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | Gateway FinOps Posture card links to Billing Period Detail. Billing period detail shows Performance Economics with cache/throttle data. |
| FinOps | Chargeback | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | GET /analytics/rate-limit-scope-posture returns chargeback rule count. Rate Limit Scope card links to Chargeback. Throttle decisions affect per-group cost attribution and chargeback evidence. Guardrail enforcement outcomes also contribute to chargeback evidence. |
| FinOps | Ledger | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | GET /analytics/response-cache-economics-posture and rate-limit-scope-posture return ledger snapshot count. Cache Economics and Rate Limit Scope cards link to Ledger. Ledger snapshots provide compliance evidence for cache savings and throttle cost impact. |

### 11.2c FinOps x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-------------------|------------------|-----------------|------------------------|-------------|------------|---------|
| FinOps | Budgets | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | WU-015 adds Budgets and Budget Detail drill-through links to Sessions list and Session detail investigation bars. Sessions surfaces show per-session and per-turn cost data, enabling operators to pivot directly into budget context. Prior: Analytics overview, Economics, Cost & Savings, Outcomes, and Monitoring all show budget posture via dedicated endpoints. |
| FinOps | Budget detail | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | WU-019 adds Budget Detail drill-through link to Monitoring FinOps Monitoring Context card. Monitoring N/A→P. Prior WU-018 adds Budget Detail to Outcomes. Budget detail linked from Analytics overview, Model usage, all investigation surfaces, Analytics Economics, and Cost & Savings with budget utilization context and drill-through links. |
| FinOps | Budget overrides | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Override counts visible on Analytics overview, investigation surfaces, Analytics Economics, Cost & Savings, and Monitoring via posture endpoints with drill-through to Budget Overrides. |
| FinOps | Budget notifications | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Notification counts now visible on Analytics overview, Analytics Economics, Cost & Savings, and Monitoring via posture endpoints with drill-through to Notifications page. |
| FinOps | Billing periods | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Billing period counts now visible on Analytics overview, Model usage, Economics, Cost & Savings, Outcomes, and Monitoring via posture endpoints with drill-through to Billing Periods. |
| FinOps | Billing period detail | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Billing period detail reachable from Analytics overview, Model usage, Economics, Cost & Savings, Outcomes, and Monitoring through FinOps posture drill-through links. |
| FinOps | Chargeback | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Chargeback rule count visible on Analytics overview, Model usage, Economics, Cost & Savings, Outcomes, and Monitoring with drill-through to Chargeback page. |
| FinOps | Ledger | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | Ledger snapshots now visible on Analytics Economics, Cost & Savings, and Monitoring via posture endpoints with drill-through to Ledger page. |

### 11.2d FinOps x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| FinOps | Budgets | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Governance evidence exists, but budget policy lifecycle is still not tightly integrated with approvals, alerts, and tagging. |
| FinOps | Budget detail | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budget detail is operationally real now, but it still is not a fully governed review surface with rich traceability. |
| FinOps | Budget overrides | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Overrides are the clearest place where approval-driven governance should exist and still are only partially integrated there. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notification and evidence paths are stronger than the main budget workflow today. |
| FinOps | Billing periods | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Billing has useful evidence hooks, but not a deeply governed operator story yet. |
| FinOps | Billing period detail | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Reconciliation detail can support governance, but the user flow still feels finance-only rather than policy-aware. |
| FinOps | Chargeback | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tagging and evidence are important here, but the overall governance relationship is still moderate rather than strong. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | Ledger is primarily a compliance evidence surface, so governance-pack cohesion is one of the strongest relationships in the matrix. |

### 11.2e FinOps x Build & Improve

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | FinOps should increasingly act as a feedback loop into optimization, workflows, and prompt/model improvement rather than sitting as a separate finance island. |
| FinOps | Budget detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Budget detail now exists, but it still does not yet drive improvement work across the build surfaces as strongly as it could. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Override decisions should eventually be visible as explicit engineering or evaluation exceptions. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Notifications should feed operators and builders when spend issues affect workflow improvement loops. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Billing and optimization already want to work together; the product should lean into that relationship more intentionally. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Reconciliation detail should become a stronger input into experimentation and optimization decisions. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Chargeback is most cohesive when tied to workflows and improvement programs rather than only to flat finance reports. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger is largely outside the day-to-day build loop except as downstream evidence, with only a light tie to optimization/replay feedback loops. |

### 11.2f FinOps x Platform and Utility

| Row Major Feature | Row Subfeature | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|-------------------|-------------------|---------|---------|
| FinOps | Budgets | `PARTIAL` | `PARTIAL` | `PARTIAL` | FinOps should surface clearly at both org and platform scope, but platform ownership is still under-structured outside the main workspace budget shell. |
| FinOps | Budget detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | Platform operators still lack a strong detail view for cross-org spend governance. |
| FinOps | Budget overrides | `PARTIAL` | `PARTIAL` | `PARTIAL` | Override governance should eventually include platform-level review and reporting. |
| FinOps | Budget notifications | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notifications need stronger platform-level visibility and administration. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | Billing already has platform relevance, but the user workflow is not fully unified yet. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | Platform-side billing drilldowns should become more operational and less passive. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | Chargeback belongs at both org and platform layers, but the allocation model needs deepening. |
| FinOps | Ledger | `PARTIAL` | `STRONG` | `PARTIAL` | Ledger is the clearest FinOps-to-platform-settings relationship in the current product. |

### 11.2g FinOps x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| FinOps | Budgets | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budgets is the intended FinOps control-plane anchor and now has real internal ties to detail, overrides, and notifications, though the downstream billing and allocation links are still looser. |
| FinOps | Budget detail | `STRONG` | `N/A` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Budget detail now exists and gives the FinOps domain a real internal drillback, but it still is not the fully connective tissue the bundle blueprint ultimately wants. |
| FinOps | Budget overrides | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Overrides are real and now live inside the main budget lifecycle, though they still are not as deeply governed as the rest of the control plane should become. |
| FinOps | Budget notifications | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notification behavior exists and is tied to budgets, but it still is not tightly embedded into the day-to-day FinOps operator experience. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `STRONG` | Billing is internally one of the most cohesive FinOps blocks today, especially across period detail, chargeback handoff, and ledger closure. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | Billing detail is structurally sound and closely tied to the rest of the downstream FinOps flow, even though its ties back into budget governance remain more moderate. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `N/A` | `STRONG` | Chargeback belongs inside FinOps and now has real ties into billing and closure, but it still behaves more like an adjacent allocation engine than a fully woven control-plane feature. |
| FinOps | Ledger | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | Ledger closes the loop for evidence and verification and is now strongly connected to billing and chargeback, even though the upstream budget-to-closure chain is still not seamless. |

### 11.2h Matrix Reading Notes

- `FinOps -> Budgets x Workspaces = STRONG`
  Means the current implementation already has a meaningful real relationship there.
- `FinOps -> Budgets x Access groups = GAP`
  Means the relationship should exist, but the current product and runtime do not yet expose it strongly enough.
- `FinOps -> Budget detail x Provider profiles = GAP`
  Means the detail experience is too weak to expose a relationship that Bundle A should eventually support.
- `FinOps -> Billing periods x Analytics economics = STRONG`
  Means the relationship is already real in the shipped suite, even if the operator workflow still needs tightening.
- `FinOps -> Chargeback x Workflow detail = STRONG`
  Means the product direction is clearest when financial attribution is tied back to workflows rather than to legacy organizational abstractions.
- `FinOps -> Budgets x Budget detail = GAP`
  Means the main control-plane feature still lacks the internal detail experience needed to make the rest of FinOps cohesive.

### 11.2i FinOps Bundle A Audit Findings

These findings should directly shape `Bundle A - Spend Control Plane`:

1. `Budgets` must become access-aware.
   Current code and UI treat workspace as the main real scope, but the next implementation pass should explicitly support access groups and API keys as first-class budget scopes.
2. `Budgets` must become gateway-aware but not gateway-owned.
   Gateway quota tiers and model quotas are related, but spend governance should remain owned by FinOps while cross-linking clearly into Gateway technical controls.
3. `Budget detail` is the biggest current cohesion gap.
   Without a true detail page, budgets cannot meaningfully connect to organization rollups, access scopes, API keys, provider profiles, approvals, or policy history.
4. `Budget overrides` must be approval-aware.
   The current lifecycle is useful, but it behaves like a detached exception table instead of a governed override workflow.
5. `Budget notifications` should be pulled into the main Spend Control Plane.
   The backend is already stronger than the UI here, so this is a high-value cohesion win for Bundle A.
6. `Provider profiles` and `Tags / workflows` are missing as first-class budget dimensions.
   These are essential if FinOps is going to become one of the strongest feature families instead of remaining workspace-only.
7. `Audit log` and `Governance pack` already provide the right evidence direction.
   Bundle A should lean into these instead of inventing separate evidence flows.
8. `Organization profile` should consume budget rollups, but Bundle A should remain the canonical spend-policy owner.
   This keeps FinOps cohesive without scattering budget editing into org admin pages.
