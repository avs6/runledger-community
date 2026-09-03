# FinOps — Cohesion Matrix

Last updated: 2026-09-03 (06-BUILD WU-028)

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
| FinOps | Budgets | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | WU-014: Budget Scope Governance Posture endpoint and emerald card on Budgets page with identity context (workspace users, API keys, access groups, hub models). Users P→S via identity scope tile with drill-through to Users page. Prior WU-001: Access groups and API keys are first-class budget scopes. |
| FinOps | Budget detail | `STRONG` | `N/A` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | WU-015: Budget Detail Drillback Posture endpoint and emerald card on Budget Detail with scope owners (users, access groups, API keys). Users P→S via scope context tile with drill-through to Users page. Prior WU-001: Org & Access Scope Context card with user/key/group counts. |
| FinOps | Budget overrides | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | WU-001: Overrides inherit access-group and API-key scope from parent budget. Override creation form shows scope context label. Telemetry downstream posture returns budget_count encompassing overrides. Workspace page links to Budgets. |
| FinOps | Budget notifications | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | GET /analytics/ai-hub-runtime-posture returns budget_notification_count. AI hub now surfaces budget notification count through the runtime posture endpoint. Telemetry downstream posture also returns budget_notification_count. |
| FinOps | Billing periods | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | WU-017: Billing Reconciliation Posture endpoint and emerald card on Billing page with identity context (workspace users, API keys, access groups). Users P→S via identity context tile with drill-through to Users page. Prior: Telemetry downstream posture returns active_billing_periods, AI hub cost posture shows billing period count. |
| FinOps | Billing period detail | `STRONG` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | WU-018: Billing Detail Evidence Posture endpoint and emerald card on Billing Period Detail with identity context (workspace users, API keys, access groups). Users P→S via identity context tile with drill-through to Users page. Prior: Telemetry downstream posture returns active_billing_periods. |
| FinOps | Chargeback | `STRONG` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | WU-019: Chargeback Attribution Posture endpoint and emerald card on Chargeback page with identity context (workspace users, API keys, access groups). Users P→S via identity context tile with drill-through to Users page. Prior: MCP Registry posture returns chargeback_rule_count, Telemetry downstream posture also returns chargeback_rule_count. |
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
| FinOps | Budgets | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-009: Budget Control Observe Posture endpoint and emerald card added to Analytics Users, User Detail, Engineering, and Model Usage with budget policy (active, breached, at-risk, avg utilization), override status, notification summary, and spend context. Analytics users P→S, User detail P→S, Engineering P→S. Prior: WU-015 Sessions drill-through, WU-003 budget posture on Observe surfaces. |
| FinOps | Budget detail | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | WU-003: Budget detail observe posture card added to Workspace Dashboard, Analytics Users, User Detail, and Engineering Dashboard with drill-through links. Prior: WU-002 (03-OBSERVE) adds Budget Detail to Runs/Request flow/Request explorer. Budget detail linked from all major Observe surfaces. |
| FinOps | Budget overrides | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-009: Budget Control Observe Posture card shows override status (total/active overrides) on Analytics Users, User Detail, Engineering, and Model Usage. Analytics users P→S, User detail P→S, Engineering P→S, Model usage P→S. Prior: WU-002 Override drill-through on investigation surfaces. |
| FinOps | Budget notifications | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-009: Budget Control Observe Posture card shows notification summary (total notifications) on Analytics Users, User Detail, Engineering. Analytics users P→S, User detail P→S, Engineering P→S. Prior: Notification counts on Analytics overview, Economics, Cost & Savings, Monitoring. |
| FinOps | Billing periods | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | Billing period counts now visible on Analytics overview, Model usage, Economics, Cost & Savings, Outcomes, and Monitoring via posture endpoints with drill-through to Billing Periods. |
| FinOps | Billing period detail | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | WU-018: Billing Detail Evidence Posture endpoint and emerald card on Billing Period Detail with observe context (sessions, requests). Sessions list P→S via observe context tile with drill-through to Sessions page. Prior: WU-002 adds Billing Period Detail drill-through to Runs list, Run detail, Request flow, Request explorer. |
| FinOps | Chargeback | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | WU-019: Chargeback Attribution Posture endpoint and emerald card on Chargeback page with monitoring context (alert rules, audit events, tags). Monitoring P→S via monitoring context tile with drill-through to Monitoring page. Prior: Chargeback rule count visible on Monitoring through FinOps posture drill-through. |
| FinOps | Ledger | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | WU-013: Ledger Cross-Feature Posture endpoint and emerald card on Platform Settings with observe context (billing periods, 30-day spend, distinct models). Billing summary P→S via observe context tile with drill-through to Billing. Prior: Ledger snapshots visible on Economics, Cost & Savings, Monitoring. |

### 11.2d FinOps x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| FinOps | Budgets | `N/A` | `N/A` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | 04-SAFETY WU-015 adds Runtime Scope & Evidence posture card (cyan theme) to Data Capture via `GET /analytics/data-capture-runtime-posture` with budget context (total budgets, budget notifications 30d). Data capture N/A→S. Prior: WU-013 Tool policies P→S, WU-010 Audit log/Governance pack P→S, WU-003 Tags P→S. |
| FinOps | Budget detail | `N/A` | `N/A` | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | 04-SAFETY WU-010 adds Cross-Feature Evidence Posture card to Audit Log and Governance Pack via `GET /analytics/evidence-audit-cross-posture` with budget context and drill-through. Audit log P→S, Governance pack P→S. Prior WU-003 Tags GAP→S. |
| FinOps | Budget overrides | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | 05-FINOPS WU-004 adds Budget Override Governance Posture card (amber theme) to Budget Detail via `GET /analytics/budget-override-governance-posture` with approval workflow context, alert rule coverage, audit events, governance coverage, and tag attribution. Approvals P→S, Alert rules P→S, Audit log P→S, Governance pack P→S, Tags P→S. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notification and evidence paths are stronger than the main budget workflow today. |
| FinOps | Billing periods | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-011: Billing Cross-Feature Posture endpoint and emerald card added to Billing page with safety context (tool registry count, alert rules, audit events, tags). Tool registry P→S, Alert rules P→S, Audit log P→S, Governance pack P→S, Tags P→S. |
| FinOps | Billing period detail | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-011: Billing Cross-Feature Posture card added to Billing Period Detail with safety context. Tool registry P→S, Alert rules P→S, Audit log P→S, Governance pack P→S, Tags P→S. |
| FinOps | Chargeback | `STRONG` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-012: Chargeback Cross-Feature Posture endpoint and emerald card added to Chargeback page with safety context (MCP servers, tool registry, audit events, tags). MCP servers P→S. Prior: WU-017 Alert rules N/A→S, WU-016 Security N/A→S, WU-010 Audit log/Governance pack P→S, WU-003 Tags P→S. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | 05-FINOPS WU-013: Ledger Cross-Feature Posture endpoint and emerald card on Platform Settings with safety context (audit events, tags). Tags P→S via safety context tile with drill-through to Tags. Prior: 04-SAFETY WU-016 Security P→S, WU-015 Data capture N/A→S, WU-013 Tool policies N/A→S, WU-010 Audit log P→S. |

### 11.2e FinOps x Build & Improve

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|---------|
| FinOps | Budgets | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | `STRONG` | 06-BUILD WU-008: Optimization FinOps posture card adds active budgets, total limit, 30d spend with Budgets drill-through. Optimization opportunities P→S, Optimization simulator P→S. Prior WU-010: 14 Build page cells P→S. |
| FinOps | Budget detail | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `PARTIAL` | 06-BUILD WU-017: Workflow run detail amber FinOps & Audit Context card shows budgets and cost 30d with Budget Detail drill-through. Workflow run detail P→S. Prior 05-FINOPS WU-005: 12 cells P→S via budget detail build posture. Remaining PARTIALs: Optimization opportunities, Optimization simulator, Datasets, Runbooks. |
| FinOps | Budget overrides | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | `STRONG` | WU-010: Budget Control Build Posture card shows override context (total/active overrides) on all 14 Build pages. 14 cells P→S. Remaining PARTIALs: Optimization opportunities, Optimization simulator. Prior: Override decisions were not visible as engineering context. |
| FinOps | Budget notifications | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | Notifications should feed operators and builders when spend issues affect workflow improvement loops. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `N/A` | `STRONG` | 06-BUILD WU-023: Runbooks Remediation amber card shows billing periods with Billing Periods drill-through. Runbooks P→S. Prior WU-020: Experiments P→S. Prior WU-019: Evaluation studio P→S. Prior WU-008: Optimization simulator P→S, Model scorecards P→S. Prior WU-003: Workflow detail P→S. Prior WU-017: Optimization opportunities P→S. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | WU-018: Billing Detail Evidence Posture endpoint and emerald card on Billing Period Detail with build context (replay experiments). Replay lab P→S via build context tile with drill-through to Replay Lab. Prior: Reconciliation detail should be a stronger input into experimentation. |
| FinOps | Chargeback | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | 06-BUILD WU-028: Vector Store Detail Evidence amber card shows chargeback_rules with Chargeback drill-through. Vector store detail N/A→S. Prior WU-027: Vector stores list N/A→S. WU-020: Experiments P→S. WU-021: Replay lab P→S. WU-019: Evaluation studio P→S. WU-018: Datasets N/A→S. WU-016: Workflow detail P→S. WU-013: Agents list P→S. WU-012: Prompt detail P→S. WU-008: Opt sim/Scorecards P→S. |
| FinOps | Ledger | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `N/A` | Ledger is largely outside the day-to-day build loop except as downstream evidence, with only a light tie to optimization/replay feedback loops. |

### 11.2f FinOps x Platform and Utility

| Row Major Feature | Row Subfeature | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|-------------------|-------------------|---------|---------|
| FinOps | Budgets | `STRONG` | `STRONG` | `PARTIAL` | 05-FINOPS WU-006 adds Budget Control Platform Posture endpoint (`GET /analytics/budget-control-platform-posture`) and emerald Budget Control — Platform Posture card to All Organizations and Platform Settings with cross-org budget totals, per-org breakdowns, override context, and spend. All organizations P→S, Platform settings P→S. |
| FinOps | Budget detail | `STRONG` | `STRONG` | `PARTIAL` | 05-FINOPS WU-006: Budget detail context now visible on All Organizations and Platform Settings via platform posture card. All organizations P→S, Platform settings P→S. |
| FinOps | Budget overrides | `STRONG` | `STRONG` | `PARTIAL` | 05-FINOPS WU-006: Override context (total/active overrides) now visible on All Organizations and Platform Settings via platform posture card. All organizations P→S, Platform settings P→S. |
| FinOps | Budget notifications | `PARTIAL` | `PARTIAL` | `PARTIAL` | Notifications need stronger platform-level visibility and administration. |
| FinOps | Billing periods | `STRONG` | `STRONG` | `PARTIAL` | WU-011: Billing Cross-Feature Posture card added to Billing page with platform context (total organizations). All organizations P→S, Platform settings P→S. |
| FinOps | Billing period detail | `STRONG` | `STRONG` | `PARTIAL` | WU-011: Billing Cross-Feature Posture card added to Billing Period Detail with platform context. All organizations P→S, Platform settings P→S. |
| FinOps | Chargeback | `STRONG` | `STRONG` | `PARTIAL` | WU-012: Chargeback Cross-Feature Posture card added to Chargeback page with platform context (total organizations, chargeback rules). All organizations P→S, Platform settings P→S. |
| FinOps | Ledger | `STRONG` | `STRONG` | `PARTIAL` | WU-013: Ledger Cross-Feature Posture endpoint and emerald card on Platform Settings with platform context (total organizations). All organizations P→S via platform context tile. Prior: Ledger is the clearest FinOps-to-platform-settings relationship in the current product. |

### 11.2g FinOps x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| FinOps | Budgets | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-008: FinOps Internal Posture endpoint and emerald card on Budgets page now surface billing period count, chargeback rules, ledger snapshots, overrides, and notifications with drill-through to Billing, Chargeback, and Ledger. All downstream links now STRONG. |
| FinOps | Budget detail | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-008: FinOps Internal Posture card on Budget Detail shows billing periods, chargeback rules, ledger snapshots, overrides, and notifications with drill-through links. Budget detail is now fully connected to all FinOps surfaces. |
| FinOps | Budget overrides | `STRONG` | `STRONG` | `N/A` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | WU-008: Overrides inherit FinOps Internal Posture context from budget detail. The override lifecycle now surfaces billing, chargeback, ledger, and notification counts through the posture card. |
| FinOps | Budget notifications | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `N/A` | `STRONG` | WU-008: Notifications inherit FinOps Internal Posture context. Billing, billing detail, and ledger counts are now visible through the posture card with drill-through links. |
| FinOps | Billing periods | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `STRONG` | Billing is internally one of the most cohesive FinOps blocks today, especially across period detail, chargeback handoff, and ledger closure. |
| FinOps | Billing period detail | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `STRONG` | `STRONG` | Billing detail is structurally sound and closely tied to the rest of the downstream FinOps flow, even though its ties back into budget governance remain more moderate. |
| FinOps | Chargeback | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | `STRONG` | `STRONG` | `N/A` | `STRONG` | WU-008: FinOps Internal Posture card on Chargeback page now surfaces budget totals, billing periods, ledger snapshots, overrides, and notifications with drill-through to Budgets, Billing, and Ledger. Budget and budget detail cells P→S. |
| FinOps | Ledger | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `STRONG` | `N/A` | WU-008: Ledger inherits FinOps Internal Posture context through the posture card on budget surfaces. Budget and budget detail cells P→S via posture drill-through. |

### 11.2h Matrix Reading Notes

- `FinOps -> Budgets x Workspaces = STRONG`
  Means the current implementation already has a meaningful real relationship there.
- `FinOps -> Budgets x Access groups = STRONG`
  WU-001 made access groups first-class budget scopes with entity selector, org posture card, and drill-through links.
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

1. ~~`Budgets` must become access-aware.~~ **RESOLVED (WU-001)**
   Access groups and API keys are now first-class budget scopes. CreateBudgetModal has entity selector dropdowns, BudgetDetailClient shows org scope posture card, and the analytics endpoint provides cross-feature context.
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
