# Observe — Delivery Status

Last updated: 2026-08-25

---

## Delta — 2026-08-25 (WU-020)

WU-020 (Scorecards Replay and Runbooks Support Refresh) COMPLETED. UI enrichment of Model Scorecards, Replay Lab, and Runbooks pages:

- Model scorecards: Workspace context bar expanded with Model Usage and Evaluation Studio drill-through links alongside existing Workspaces link.
- Replay lab: Gateway context bar (violet theme) added with Model Gateway, Provider Profiles, and Routes drill-through links.
- Runbooks: Gateway and audit context bar added with Model Gateway (violet), Audit Log (amber), and Runs (blue) drill-through links.

Cell changes: Model scorecards × Workspaces already STRONG (WU-009), Replay lab × Model gateway P→S (03×02, 03-OBSERVE 11.5c), Runbooks × Model gateway P→S (03×02, 03-OBSERVE 11.5c), Runbooks × Audit log P→S (03×04, 03-OBSERVE 11.5c).

---

## Delta — 2026-08-25 (WU-019)

WU-019 (Monitoring Telemetry Ops and Governance Refresh) COMPLETED. Drill-through link additions to Monitoring and Telemetry pages:

- Monitoring: Budget Detail link added to FinOps card. Approvals link added to Governance Ops Context card. API Keys link added to Org & Investigation Context card.
- Telemetry: Guardrails, Response Cache, and Rate Limits links added to Gateway Context card. Tool Registry and Tool Policies links added to Governance Context card.

Cell changes: Monitoring × Budget detail N/A→P (03×05), Monitoring × API keys P→S (03×01), Monitoring × Approvals N/A→P (03×04), Telemetry × Guardrails N/A→P, Response cache N/A→P, Rate limits N/A→P (03×02), Telemetry × Tool registry N/A→P, Tool policies N/A→P (03×04).

---

## Delta — 2026-08-25 (WU-018)

WU-018 (Analytics Users Outcomes and Identity Refresh) COMPLETED. UI enrichment of Analytics users and Outcomes pages:

- Analytics users: Gateway & Model Context card (violet theme) added via `GET /analytics/model-usage-gateway-posture` showing active routes, distinct models, routing policies, and gateway request volume. Drill-through links to Model Gateway, Provider Profiles, and Routes. API Key Detail link added to Org & Workspace Context card.
- Outcomes: Budget Detail drill-through link added to FinOps Outcomes Context card. Workspace & Identity Context card (blue theme) added via `GET /analytics/investigation-org-identity-posture` showing workspace name, user counts, end user volume, and API key status. Drill-through links to Workspaces, Users, API Keys, and Organization.

Cell changes: Analytics users × API keys N/A→S (01-ORG), Analytics users × Model gateway N/A→S (03-OBSERVE 11.5c), Outcomes × Budget detail P→S (05-FINOPS), Outcomes × Workspaces N/A→S (03-OBSERVE 11.5b).

---

## Delta — 2026-08-25 (WU-017)

WU-017 (Model Usage Economics and Runtime Refresh) COMPLETED. UI enrichment of Model usage page:

- Gateway & Intelligence Context card: Now shows guardrail rule count and RPM-limited route count from `GET /analytics/investigation-gateway-runtime-posture`. Guardrails and Rate Limits drill-through links added.

Most WU-017 target cells (Budgets, Budget detail, API keys) were already at STRONG from prior WUs. Actual cell changes: Guardrails P→S, Rate limits P→S in 11.5c (03-OBSERVE × 02-GATEWAY).

---

## Delta — 2026-08-25 (WU-016)

WU-016 (Request Analysis Scope and Evidence Refresh) COMPLETED. UI enrichment of Request flow and Request explorer pages:

- Request flow: Governance card now shows pending approvals count and capture policy count from `GET /analytics/overview-scope-posture`. Approvals drill-through link added.
- Request explorer: Governance evidence section shows capture policy count from `GET /analytics/overview-scope-posture`. Data Capture drill-through link added.

Most WU-016 target cells (Access groups, Budget detail, Guardrails) were already at STRONG from prior WUs. Actual cell changes: Approvals N/A→P (Request flow × 04-SAFETY), Data capture N/A→P (Request explorer × 04-SAFETY) in 11.5c.

---

## Delta — 2026-08-25 (WU-015)

WU-015 (Sessions Investigation Scope Refresh) COMPLETED. UI enrichment of Sessions list and Session detail pages:

- Sessions list: FinOps drill-through links (Budgets, Budget Detail, Chargeback) added to existing Org Identity bar.
- Session detail: Identity & Investigation context bar added with User Runs, Users, API Keys, Telemetry, Budgets, Budget Detail, and Chargeback drill-through links.

Cell changes: API keys × Sessions list N/A→P, API keys × Session detail N/A→P (01-ORG), Budgets × Sessions list N/A→P, Budgets × Session detail N/A→P (05-FINOPS). Users × Sessions already PARTIAL, Chargeback × Sessions already PARTIAL.

---

## Delta — 2026-08-25 (WU-014)

WU-014 (Run Detail Runtime Evidence Refresh) COMPLETED. UI enrichment of the Run detail page:

- Identity Provenance panel: Workspace context (name, user count), MCP Registry context (servers, tool calls 30d), and Telemetry context (batches, runs 30d) added as dedicated sub-cards via `GET /analytics/investigation-org-identity-posture`. Workspaces drill-through link added.
- Governance evidence panel: Pending approval count and capture policy count added inline. Approvals and Data Capture drill-through links added via `GET /analytics/overview-scope-posture`.
- Budget context panel: Budget Detail drill-through link added.
- Gateway runtime panel: Guardrail events (30d) count added alongside block count.

Most WU-014 target cells (Budgets, Budget detail, Workspaces, MCP registry, Guardrails) were already at STRONG from prior WUs. Actual cell changes: Approvals N/A→P, Data capture N/A→P in 11.5c.

---

## Delta — 2026-08-25 (WU-013)

WU-013 (Runs List Investigation Bridge Refresh) COMPLETED. UI enrichment of the Runs list page:

- Governance card: Approvals and Data Capture now shown as explicit stat tiles (total + pending, capture policy count) with drill-through links. Prior cells were already PARTIAL from existing governance posture.
- Org Identity card: Access Groups tile added (active/total, member count) via `GET /analytics/overview-scope-posture` with drill-through link.
- FinOps card: Budget Detail drill-through link added alongside Budgets, Billing Periods, Chargeback, and Model Budgets.

Most WU-013 target cells were already at or beyond target from prior WUs (WU-004 org identity, WU-006 gateway runtime). No cell state changes — WU-013 deepens existing integration.

---

## Delta — 2026-08-25 (WU-012)

WU-012 (Analytics Overview Scope Posture Refresh) COMPLETED. 6 cohesion cells closed:

- Response cache P→S (03-A × 02): gateway card gains cache sub-card with enabled/total configs, hits, and savings
- Rate limits P→S (03-A × 02): gateway card gains rate limit sub-card with limited vs unlimited routes
- Tool registry N/A→P (03-A × 04): governance card gains tool registry sub-card with entry count
- Tool policies N/A→P (03-A × 04): governance card gains tool policies sub-card with active/total
- Approvals N/A→P (03-A × 04): governance card gains approvals sub-card with pending count
- Data capture N/A→P (03-A × 04): governance card gains data capture sub-card with policy count

Access groups tile added to Org Identity card. New endpoint: `GET /analytics/overview-scope-posture`.
03-A × 02 moves from P:1 to OK. 03-A × 04 moves from OK to P:4. 02-C × 03 moves from P:2 to OK.

---

## Delta — 2026-08-25 (WU-011)

WU-011 (User Analytics & Overview Org Links) COMPLETED. 4 cohesion cells closed:

- **Backend**: 1 new posture endpoint (`user-analytics-org-posture`) with org, user, and workspace context.
- **UI — Analytics Users**: Org & Workspace Context card (blue theme) with org name, workspace count, workspace users, end users (active/total), API keys (active/total). Drill-through links to Organization, Workspaces, Users, API Keys, and Telemetry.
- **UI — Analytics Overview**: Monitoring added as first-class investigation destination in header nav, next actions section, and investigation scope card.
- **UI — Model Usage**: Telemetry drill-through link added to gateway posture card.
- **Docs**: "User analytics & overview org links" section in analytics.mdx.
- **Example**: `examples/83_user_analytics_org.py`.
- **Postman**: User Analytics Org Posture entry.
- **Status**: 03-A × 03 P:3→OK, 03-C × 01 P:3→P:2.

---

## Delta — 2026-08-25 (WU-010)

WU-010 (Monitoring & Ops Governance Integration) COMPLETED. 30 cohesion cells closed (Monitoring 17 + Telemetry 13):

- **Backend**: 2 new posture endpoints (`monitoring-ops-posture`, `telemetry-ops-posture`) with gateway, governance, org, and investigation context.
- **UI — Monitoring**: 3 ops posture cards — Gateway Ops Context (violet: providers, routes, guardrails, cache, rate limits), Governance Ops Context (amber: tool registry, tool policies, capture, audit, approvals, tags), Org & Investigation Context (blue: users, MCP servers, runs, gateway requests) with 18 drill-through links.
- **UI — Telemetry**: 3 ops posture cards — Gateway Context (violet: routes, models, gateway requests), Governance Context (amber: capture, security, alerts, audit, approvals, tags), Org & Investigation Context (blue: users, batches, runs, provider calls) with 14 drill-through links.
- **Docs**: "Monitoring & ops governance integration" section in analytics.mdx.
- **Example**: `examples/82_monitoring_ops_governance.py`.
- **Postman**: Monitoring Ops Posture and Telemetry Ops Posture entries.
- **Status**: 03-D × 01 P:3→OK, 03-D × 02 P:3→OK, 03-D × 03-Self P:8→P:4, 03-D × 04 P:10→P:5.

---

## Audited Overrides

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 3.1 | Dashboard | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `N/A` | `PARTIAL` | Dashboard is now a deliberate Observe entry collapse rather than a standalone feature family: `/dashboard`, `/organization/dashboard`, and `/global-dashboard` all redirect into the scoped `/analytics` overview shell, while org rollups remain backed by `GET /org/dashboard`. The redirect behavior, docs, and demo/manual usage are real; the remaining weakness is support-surface naming consistency because README/demo assets and some examples still use broad “dashboard” language rather than always identifying `/analytics` as the canonical owner. |
| 3.2 | Runs | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `N/A` | `PARTIAL` | Runs is a working investigative ledger surface: backend filters, cursor pagination, export, and drill-in all work, and the UI adds summary context plus direct pivots into Request Flow and Request Explorer. It now also supports access-group-scoped investigation through `access_group_id`, including scoped export and drill-through from `/access-groups`. Docs, README, Postman, and lab coverage are solid; the softer surfaces are dedicated runnable examples and assertive automation, which remain more adjacent than purpose-built for the run list itself. |
| 3.3 | Run detail | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `N/A` | `N/A` | Run detail is real end-to-end: `/runs/{id}`, `/runs/{id}/graph`, and `/runs/{id}/cancel` are backed by code and surfaced in the page through DAG visualization, payload viewers, provider/tool/span tables, and the cancel action for stuck runs. It now preserves access-group investigation scope for both the detail page and the graph endpoint, keeping scoped pivots consistent when operators drill in from access-group investigation flows. README coverage is indirect rather than detail-specific, and example/automation coverage is mostly shared through sessions and adjacent investigation flows rather than a dedicated run-detail script. |
| 3.4 | Sessions | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `N/A` | `N/A` | Sessions is complete as a conversation-level investigative surface: grouped session lists, backend search/filter/pagination, CSV export, and the corresponding UI all align, with strong docs, README, Postman, lab, and dedicated example coverage. The only softer area is automated verification, which exists through tests and scenario traffic rather than a richer end-to-end lab assertion script. |
| 3.5 | Session detail | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `PARTIAL` | `N/A` | `N/A` | Session detail provides the intended drilldown with ordered turns, cumulative cost-over-turns, total duration/cost context, and per-turn run pivots. Docs, Postman, manual lab guidance, and Example 16 are all aligned; README coverage remains indirect, and automation is still broader test/scenario coverage rather than a dedicated session-detail regression script. |
| 3.6 | Request flow | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `N/A` | `PARTIAL` | Request Flow is the live request-causality surface over `/runs/flow`: the backend supports workspace/org/platform scope plus multiple modes and metrics, and the UI exposes the Sankey, focus mode, zoom/export, and drill-ins into Request Explorer and Analytics. It now also supports workspace-scoped `access_group_id`, including preserved scope through focus mode and Request Explorer pivots. Docs, README, Postman, and manual walkthroughs are strong; the lighter surfaces are dedicated examples and assertive automation, and the focused large-canvas mode is still taught mostly through shared support material. |
| 3.7 | Request explorer | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Request Explorer is implemented as a real investigative page and API: `/analytics/request-explorer` powers filterable pagination, and the UI drills into runs, payload capture, route/gateway evidence, outcomes, tools, and sessions. It now supports access-group-scoped investigation and preserves that scope into run detail. The main weakness is support accuracy rather than feature behavior: the docs were corrected to the actual response shape, while example coverage and manual/automated walkthroughs are still lighter than for Runs and Sessions. |
| 3.8 | Analytics | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | Analytics is the real scoped overview shell for Observe: the UI supports workspace, org, and platform scope tabs plus range/view switches, and the backend exposes `/analytics/scoped-summary` with supporting summary, export, request-analysis, and org-rollup contracts. It now also accepts workspace-scoped `access_group_id`, making access groups a real investigation drill-down from `/access-groups` into the overview shell. Docs, README, Postman, and guided demo usage are aligned; the remaining softer surfaces are example depth and broader support/cohesion material that still talks about dashboards generically or relies on adjacent analytics examples instead of a dedicated overview example. |
| 3.9 | Economics | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Economics is now clearly the overview bridge for the bundle rather than a shallow duplicate page: regressions, version compare, annotations, and top-cost workflows are live, and the UI deliberately routes deeper work into Model Usage, Cost & Savings, and Billing. README coverage is indirect, and the lighter surfaces are dedicated manual/automated feature walkthroughs rather than the core shipped page. |
| 3.10 | Users analytics | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Users analytics is complete as a spend-investigation surface: list and detail pages are backed by cohort, anomaly, and per-user detail APIs, and the UI bridges cleanly into Request Explorer, Request Flow, and Outcomes & ROI. The softer areas are README specificity and dedicated lab/automation coverage, which remain shared across broader analytics traffic rather than purpose-built for this feature family. |
| 3.11 | Engineering | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `N/A` | `PARTIAL` | Engineering is implemented end-to-end as an operational read surface: `/analytics/engineering` returns the KPIs, lifecycle, cost dimensions, and quality funnel that the page renders, and the UI bridges into Request Explorer, Request Flow, and Model Usage. The softer areas are README specificity plus thinner example and automation coverage rather than missing runtime behavior. |
| 3.12 | Model usage | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `N/A` | `PARTIAL` | Model Usage is a strong live drilldown over real traffic: scope-aware charts, route/provider distribution, cost-latency-quality comparison, and best-value signals all work and fit the economics workflow. The weaker surfaces are support-specific rather than runtime-specific, because README, examples, Postman, and automation are more adjacent to the underlying analytics family than tightly centered on this exact page. |
| 3.13 | Monitoring | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `OK` | Monitoring is a functioning triage shell rather than a broken feature: the page composes security events, alert history, gateway request logs, and a direct telemetry handoff, while deeper operational ownership stays in Security, Alert Rules, Gateway, and Telemetry. Support remains somewhat diffuse across those underlying systems, and some docs/labs still speak in legacy OTLP terms even though the redirect path is preserved. |
| 3.14 | Model scorecards | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `N/A` | `PARTIAL` | Model Scorecards is a real comparative decision surface with sortable cost, latency, reliability, cache, quality, and trend evidence per model plus bridges into Model Usage and Evaluation. Docs and workflow fit are strong; the remaining softness is dedicated runnable example and automation depth rather than missing feature behavior. |
| 3.15 | Replay lab | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Replay Lab is implemented as a real replay/experiment workflow: `/replay` manages datasets and experiments, experiment detail compares configs and can create route recommendations, and the backend plus tests/Postman/example coverage are all present. The softer area is ownership clarity rather than missing behavior, because the canonical route is `/replay` while docs and feature naming still emphasize “Replay Lab” without a matching compatibility route. |
| 3.16 | Runbooks | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | `N/A` | `PARTIAL` | Runbooks is close but not fully closed: generation and listing are real in backend and UI, and the feature is well represented in README, demo/lab material, Postman, and scenario traffic. The missing piece is export completeness, because the UI advertises markdown/JSON export through an endpoint that is not currently implemented server-side, and the docs overstate that capability. |
| 3.17 | Optimization simulator | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | Optimization Simulator is a working what-if tool over live telemetry with a real API contract, dashboard workflow, docs, README mention, and Postman coverage. Its remaining weakness is support depth: there is no dedicated example, lab walkthrough, or direct API test for the simulator, so the implementation is ahead of the verification story. |
| 3.18 | Cost and savings views | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `N/A` | `PARTIAL` | Cost & Savings is the primary optimization drilldown for FinOps: spend-versus-saved framing, savings attribution, dimension pivots, ROI targeting, and budget context are all present and documented. The support story is still somewhat shared across adjacent analytics/optimization surfaces, so example, Postman, and automation coverage are not as page-specific as the implementation quality itself. |
| 3.19 | Outcomes and ROI | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `N/A` | `OK` | Outcomes & ROI is fully delivered end-to-end: backend CRUD and analytics routes exist, the page exposes outcome ledger management plus summary/trend/workflow/correlation views, and the docs, README, Postman collection, labs, examples, and supporting simulation traffic all align with the shipped lifecycle. |
| 3.20 | Evaluations (score submit) | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `OK` | Quality-score submission and review are fully delivered inside the evaluation suite: `/evaluations` redirects into the scores tab, `/evaluations/scores` is covered by API routes, tests, examples, and Postman, and the broader Evaluation page owns the score workflow cleanly. README wording is broader than score-submit specifically, but the collapse itself is correct and complete. |

## Recent Re-Audit Delta

- `2026-08-25` — WU-009 Economics & Model Intelligence Gateway Links: 17 cohesion cells closed across Model Usage, Analytics Economics, Cost & Savings, and Model Scorecards × Gateway, Self-Observe, Safety, and Org. Backend: 2 new posture endpoints (`GET /analytics/model-usage-gateway-posture`, `GET /analytics/economics-gateway-posture`) with `ModelUsageGatewayPosture` and `EconomicsGatewayPosture` schemas. Frontend: TS types, API functions, and violet-themed gateway context cards on 3 pages — Model Usage (Gateway & Intelligence Context card with routes, models, runs, tags; 6 drill-through links: Model Gateway, Provider Profiles, Runs, Request Flow, Request Explorer, Tags), Analytics Economics (Gateway & Provider Context card with providers, routes, runs, alerts; 6 drill-through links: Provider Profiles, Model Gateway, Runs, Request Flow, Request Explorer, Monitoring), Cost & Savings (same card as Economics). Model Scorecards adds workspace scope context bar with link to Workspaces. Postman: 2 new entries. Docs: analytics.mdx updated with economics & model intelligence gateway links section. Example: 81_economics_gateway_intel.py. 03-C × 01 moves from P:4 to P:3, 03-C × 03 from P:12 to P:2, 03-C × 04 from P:1 to OK.
- `2026-08-24` — WU-008 Overview Cross-Feature Posture Cards: 14 cohesion cells closed across Analytics Overview × Org, Gateway, and Safety. Backend: 3 new posture endpoints (`GET /analytics/overview-gateway-posture`, `GET /analytics/overview-governance-posture`, `GET /analytics/overview-org-posture`) with `OverviewGatewayPosture`, `OverviewGovernancePosture`, `OverviewOrgPosture` schemas. Frontend: TS types, API functions, and 3 themed posture cards on Analytics Overview — Gateway Posture (violet theme, 4 stat tiles: Providers, Routes, Guardrails, Blocks 30d; 5 drill-through links: Provider Profiles, Model Gateway, Guardrails, Gateway Routes, Rate Limits), Governance Posture (amber theme, 4 stat tiles: Security Events, Alert Rules, Audit 30d, Tags; 5 drill-through links: Security, Alert Rules, Audit Log, Governance Pack, Tags), Org Identity (blue theme, 5 stat tiles: Users, API Keys, Telemetry 30d, MCP Servers, AI Hub Models; 6 drill-through links: Onboarding, Users, API Keys, Telemetry, MCP Registry, AI Hub). Postman: 3 new entries. Docs: analytics.mdx updated with overview cross-feature posture section. Example: 80_overview_cross_feature_posture.py. 8 cells moved P→S: Org (Users, Telemetry), Gateway (Guardrails), Safety (Security, Alert rules, Audit log, Governance pack, Tags). 03-A × 01 moves from P:3 to P:1, 03-A × 02 from P:2 to P:1, 03-A × 04 from P:5 to OK.
- `2026-08-24` — WU-007 Economics & Outcomes FinOps Strengthening: 18 cohesion cells closed across Analytics Economics, Cost & Savings, Outcomes & ROI, and Monitoring × FinOps. Backend: 3 new posture endpoints (`GET /analytics/economics-finops-posture`, `GET /analytics/outcomes-finops-posture`, `GET /analytics/monitoring-finops-posture`) with `EconomicsFinopsPosture`, `OutcomesFinopsPosture`, `MonitoringFinopsPosture` schemas. Frontend: TS types, API functions, and emerald-themed FinOps context cards on all 4 pages — Analytics Economics (Budget Context card with budgets, overrides, notifications, ledger stat tiles and 7 drill-through links), Cost & Savings (Detail Context card with billing periods, overrides, notifications, ledger stat tiles and 6 drill-through links), Outcomes & ROI (Outcomes Context card with budgets, breaches, billing periods, outcomes stat tiles and 4 drill-through links), Monitoring (Monitoring Context card with budgets, overrides, notifications, billing periods stat tiles and 6 drill-through links). Postman: 3 new entries. Docs: economics-finops-bridge.mdx created, analytics.mdx updated with economics/outcomes FinOps bridge section. Example: 79_economics_finops_posture.py. 03-C × 05 moves from P:12 to OK, 03-D × 05 moves from P:6 to OK.
- `2026-08-24` — WU-006 Investigation Gateway & Runtime Context: All 4 investigation surfaces (Runs list, Run detail, Request flow, Request explorer) now show gateway runtime context. Backend: `GET /analytics/investigation-gateway-runtime-posture` endpoint returning provider context (distinct providers, active/total routes, routing policies), route context (30d gateway requests, cache hits, passthrough endpoints), guardrail context (active rules, 30d events/blocks), cache context (enabled configs, entries, hits, savings USD), and rate limit context (routes with RPM/cost limits). Frontend: `InvestigationGatewayRuntimePosture` TypeScript type and API function. Runs list shows gateway runtime posture card (violet theme) with 4 stat tiles (Providers, Gateway Traffic, Guardrails, Cache) and 5 drill-through links (Provider Profiles, Gateway Routes, Guardrails, Response Cache, Rate Limits). Run detail shows GatewayRuntimePanel (violet theme) with provider, guardrail, cache, and rate limit summary. Request flow shows gateway runtime context card with counts and drill-through links. Request explorer shows gateway runtime posture card with 4 lifecycle cards and drill-through links. Postman entry, docs (gateway-investigation.mdx + analytics.mdx updated), and example script (78_investigation_gateway_runtime.py) added. 16 target cohesion cells were already STRONG from prior gateway-side WUs; WU-006 deepens integration with a dedicated observe-side posture endpoint.
- `2026-08-24` — WU-004 Investigation Org Identity & Scope Strengthening: All 5 investigation surfaces (Runs list, Run detail, Request flow, Request explorer, Sessions) now show org identity context. Backend: `GET /analytics/investigation-org-identity-posture` endpoint returning org, user, API key, telemetry, and MCP context. `GET /runs/flow` now accepts `end_user_id` filter. Frontend: `InvestigationOrgIdentityPosture` TypeScript type and API function. Runs list shows org identity posture card (blue theme) with 4 stat tiles and 5 drill-through links; accepts `api_key_id` filter in RunFilters. Run detail shows Identity Provenance panel (end user, API key, model, feature tag) with 7 drill-through links. Request flow shows org identity posture card and passes `api_key_id`/`end_user_id` to flow endpoint. Request explorer shows org identity posture card, adds `api_key_id` FilterBar input and API Key fact card. Sessions adds `api_key_id` filter input and org identity navigation links. Postman entry, docs (org-identity-investigation.mdx + analytics.mdx updated), and example script (77_investigation_org_identity_posture.py) added. 7 cohesion cells updated from PARTIAL to STRONG across 03-OBSERVE and 01-ORG-AND-ACCESS matrices (Users×4, Telemetry×3). FEATURE-STATUS 03-B × 01 reduced from P:16 to P:9.
- `2026-08-24` — WU-003 Overview & Economics FinOps Budget Bridge: Analytics overview now shows FinOps Budget Posture card via `GET /analytics/overview-finops-budget-posture` with budget, billing, spend, and notification context (4 stat tiles, 3 lifecycle cards, 9 drill-through links to Budgets, Budget Detail, Budget Overrides, Notifications, Billing Periods, Billing Detail, Chargeback, Ledger, Model Budgets). Model usage now shows FinOps Model Budget Utilization card via `GET /analytics/model-budget-utilization` with per-model spend vs. budget limit, utilization percentage, and 6 drill-through links. Backend: 2 new endpoints + `OverviewFinopsBudgetPosture`, `ModelBudgetUtilization`, `ModelBudgetUtilizationItem` schemas. Frontend: TS types, API functions, UI cards on both pages. Postman entries, docs (finops-investigation.mdx + analytics.mdx updated), example script (76_overview_economics_finops_bridge.py). 13 cohesion cells updated across 03-OBSERVE and 05-FINOPS matrices.
- `2026-08-24` — WU-002 Investigation FinOps Budget Bridge: All 4 investigation surfaces (Runs list, Run detail, Request flow, Request explorer) now show inline FinOps budget posture via `GET /analytics/investigation-finops-budget-posture` with drill-through links to Budgets, Billing Periods, Chargeback, and Model Budgets. Backend endpoint wired to `InvestigationFinopsBudgetPosture` response model. Frontend API function, TypeScript type, and UI budget cards added to all 4 surfaces. Postman entry, docs page (finops-investigation.mdx), and example script (75_investigation_finops_budget_bridge.py) added. 25 cohesion cells updated from PARTIAL/GAP to STRONG across 03-OBSERVE and 05-FINOPS matrices. FEATURE-STATUS 03-B × 05 GAPs closed (was G:2 P:22, now P:4).
- `2026-08-22` — WU-001 Investigation Access-Group Scope: GET /analytics/investigation-access-group-posture returns access group context (groups, total members) and investigation context (30-day runs, requests, active users, active routes). Analytics Overview page adds Investigation Scope card with 4 data tiles and 8 cross-links (Access Groups, Runs, Request Flow, Request Explorer, Users, Workspaces, Analytics Users, Model Usage). All 5 target cohesion cells (Runs list, Run detail, Request flow, Request explorer, Analytics overview × Access groups) were already at STRONG from prior work; no matrix cell changes needed. Docs (analytics.mdx), Postman, and example updated.
