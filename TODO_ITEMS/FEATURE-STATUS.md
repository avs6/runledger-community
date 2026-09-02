# RunLedger Feature Status Dashboard

Last updated: 2026-08-31

## Purpose

This file is the **cross-feature bundle status matrix**. It shows every bundle's cohesion status against every other major feature family, with GAP and PARTIAL counts computed from the per-folder COHESION-MATRIX.md files.

This file is **derived** — update the per-folder files first, then update this dashboard.

Cell notation: `G:X P:Y` = X gaps, Y partials. `P:Y` = no gaps, Y partials. `OK` = only STRONG/N/A. `—` = all N/A or no data.

---

## 1. Cross-Feature Bundle Matrix

### 01 — Org & Access

| Bundle | Features | 01-Self | 02-Gateway | 03-Observe | 04-Safety | 05-FinOps | 06-Build | 07-Platform |
|--------|----------|---------|------------|------------|-----------|-----------|----------|-------------|
| **A** — Org Foundation | Organization profile, Org settings | OK | S:4 P:1 | S:17 P:1 | S:7 P:3 | — | — | OK |
| **B** — Identity & Scope | Users, Workspaces, Access groups, API keys | P:10 | S:15 P:3 | S:35 P:18 | S:36 P:7 | S:28 P:4 | S:34 P:27 | OK |
| **C** — Onboarding & Setup | Onboarding, Integrations, Telemetry, MCP registry | P:7 | S:8 P:5 | S:12 P:22 | S:24 P:2 | S:12 P:4 | S:5 P:38 | P:5 |
| **D** — Capability Catalog | AI hub, Projects, Team models | P:4 | S:2 P:3 | S:6 P:3 | OK | OK | S:1 P:14 | OK |

**Hot spots** (recomputed 2026-08-21 after status cleanup — all GAPs eliminated from Bundles A and B):

01-A x 04 is now S:7 P:3 after WU-008 upgraded Org profile × Data capture P→S and Org profile × Tags P→S via data-protection-org-posture drill-through. Prior: S:5 P:5 after WU-006. 01-A x 06 corrected from P:14 to — (both Org profile and Org settings are all N/A against Build). 01-A x 03 corrected from S:16 to S:17 P:1 (one STRONG cell was missed in a prior count).

01-B x 02 is now S:9 P:8 after status cleanup reclassified 4 Users x Gateway GAPs: Provider profiles and Response cache → N/A (users are people, not runtime primitives), Model gateway, Guardrails, Rate limits → PARTIAL (indirect through role and API key usage). No GAPs remain. 01-B x 03 is now S:35 P:18 after status cleanup changed Users x Runs list from GAP to PARTIAL and full recount. All remaining PARTIALs are in the Users row — Users page links to entry points but does not expose user-scoped views; deeper integration requires 03-OBSERVE work. 01-B x 04 recomputed to S:36 P:7. 01-B x 05 recomputed to S:28 P:4 (no GAPs — prior G:4 was stale). 01-B x 06 recomputed to S:34 P:27.

01-C and 01-D: No changes in this cleanup. Remaining PARTIALs are structurally correct — Onboarding is a setup guide, Telemetry observes but does not control downstream surfaces, MCP registry has partial Build ties, and AI hub consumes gateway/economics context indirectly.

---

### 02 — Gateway & Routing

| Bundle | Features | 01-Org | 02-Self | 03-Observe | 04-Safety | 05-FinOps | 06-Build | 07-Platform |
|--------|----------|--------|---------|------------|-----------|-----------|----------|-------------|
| **A** — Provider & Routing | Provider profiles, Model gateway | P:10 | P:3 | P:8 | P:3 | P:3 | P:3 | OK |
| **B** — Runtime Protection | Guardrails | P:4 | OK | OK | OK | OK | OK | OK |
| **C** — Performance Controls | Response cache, Rate limits | P:2 | P:3 | OK | P:3 | S:10 | P:14 | OK |

**Hot spots**: WU-011 added Billing Cross-Feature Posture endpoint and emerald card to Billing and Billing Period Detail with gateway, safety, and platform context (24 cells P→S: 8 Gateway, 10 Safety, 4 Platform across Billing periods + detail). WU-012 added Chargeback Cross-Feature Posture endpoint and emerald card to Chargeback with org, gateway, safety, and platform context (15 cells P→S: 5 Org, 3 Gateway, 5 Safety, 2 Platform). 05-B × 04 and 05-B × 07 now **OK**. 05-C × 01, 05-C × 04, and 05-C × 07 now **OK**. Prior: WU-015 closed 4 FinOps cells for Guardrails. 02-B × 05 at **OK**. 02-C × 06 at **P:14**.

---

### 03 — Observe

| Bundle | Features | 01-Org | 02-Gateway | 03-Self | 04-Safety | 05-FinOps |
|--------|----------|--------|------------|---------|-----------|-----------|
| **A** — Overview & Entry | Analytics overview + dashboards | P:1 | OK | OK | P:4 | P:0 |
| **B** — Investigation | Runs, Sessions, Request flow/explorer | P:9 | OK | P:7 | P:28 | P:4 |
| **C** — Economics & Intel | Model usage, Economics, Cost, ROI, Users, Scorecards | P:2 | OK | P:2 | OK | OK |
| **D** — Ops & Monitoring | Engineering, Monitoring, Telemetry, Quality scores | OK | OK | P:2 | P:2 | OK |

**Hot spots**: WU-001 added investigation-access-group-posture endpoint and Analytics Overview Investigation Scope card; all 5 target cells were already STRONG. 03-B x 01 no longer carries access-group investigation GAPs now that the core Observe chain supports scoped drill-through. WU-002 closed the 03-B x 05 budget detail GAPs: all 4 investigation surfaces now show inline FinOps budget posture with Budget Detail, Budget Overrides, and Billing Period Detail drill-through links. WU-003 closed the 03-A x 05 and 03-C x 05 GAPs: Analytics overview now shows FinOps Budget Posture card (budget, billing, spend, notifications) and Model usage shows per-model budget utilization card. All FinOps GAPs in 03-OBSERVE are now closed (was G:2, now G:0). WU-004 closed 7 PARTIAL cells in 03-B x 01 (Users and Telemetry columns): investigation surfaces now show org identity posture card, identity provenance panel, and accept api_key_id/end_user_id filters with drill-through to Organization, Users, API Keys, Telemetry, and MCP Registry (was P:16, now P:9). WU-006 added gateway runtime posture cards (violet theme) to all 4 investigation surfaces via `GET /analytics/investigation-gateway-runtime-posture` with provider, guardrail, cache, and rate limit context; 16 target cells were already STRONG from prior gateway-side WUs, so no cell state changes needed — WU-006 deepens the integration with a dedicated observe-side posture endpoint and drill-through links. WU-007 closed 18 FinOps cells across Economics, Cost & Savings, Outcomes & ROI, and Monitoring: 3 new posture endpoints (`economics-finops-posture`, `outcomes-finops-posture`, `monitoring-finops-posture`) power emerald-themed FinOps context cards with budget, billing, notification, ledger, and spend context. 03-C × 05 moves from **P:12** to **OK**, 03-D × 05 moves from **P:6** to **OK**. All FinOps PARTIALs in 03-OBSERVE are now closed. WU-008 added 3 cross-feature posture cards to Analytics Overview: Gateway Posture (violet, `overview-gateway-posture`), Governance Posture (amber, `overview-governance-posture`), and Org Identity (blue, `overview-org-posture`). 8 cells moved P→S: Org (Users, Telemetry), Gateway (Guardrails), Safety (Security, Alert rules, Audit log, Governance pack, Tags). 03-A × 01 moves from **P:3** to **P:1**, 03-A × 02 from **P:2** to **P:1**, 03-A × 04 from **P:5** to **OK**. WU-009 added gateway and investigation context to Model Usage, Economics, and Cost & Savings via 2 new posture endpoints (`model-usage-gateway-posture`, `economics-gateway-posture`). Model Usage shows Gateway & Intelligence Context card (violet) with routes, models, runs, and tags. Economics and Cost & Savings show Gateway & Provider Context cards (violet) with providers, routes, runs, and monitoring alerts. Model Scorecards adds workspace scope bar linking to Workspaces. 03-C × 01 moves from **P:4** to **P:3**, 03-C × 03 from **P:12** to **P:2**, 03-C × 04 from **P:1** to **OK**. WU-010 added gateway, governance, and org context to Monitoring and Telemetry via 2 new posture endpoints (`monitoring-ops-posture`, `telemetry-ops-posture`). Monitoring shows 3 ops posture cards: Gateway Ops (violet), Governance Ops (amber), Org & Investigation (blue). Telemetry shows matching cards. 30 cohesion cells closed (17 Monitoring + 13 Telemetry). 03-D × 01 moves from **P:3** to **OK**, 03-D × 02 from **P:3** to **OK**, 03-D × 03 from **P:8** to **P:2**, 03-D × 04 from **P:10** to **P:2**. WU-011 added org/workspace context to Analytics Users via `GET /analytics/user-analytics-org-posture` (blue-themed card with org name, workspace count, users, API keys, telemetry). Analytics Overview now includes Monitoring as a first-class investigation destination in header nav, next actions, and investigation scope card. Model Usage adds Telemetry drill-through link. 03-A × 03 moves from **P:3** to **OK**, 03-C × 01 moves from **P:3** to **P:2**. WU-012 enriches Analytics Overview with scope posture data via `GET /analytics/overview-scope-posture`: gateway card gains Response Cache and Rate Limits sub-cards (P→S), governance card gains Tool Registry, Tool Policies, Approvals, and Data Capture sub-cards (N/A→P), org card gains Access Groups tile and drill-through. 03-A × 02 moves from **P:1** to **OK**, 03-A × 04 moves from **OK** to **P:4**. 02-C × 03 moves from **P:2** to **OK**. WU-013 enriches Runs list investigation bridge: governance card gains explicit Approvals and Data Capture stat tiles with drill-through links (cells were already PARTIAL from prior governance posture). Org identity card gains Access Groups tile. FinOps card gains Budget Detail drill-through link. Most target cells were already at or beyond target from prior WUs — WU-013 deepens the UI integration without changing cell states. WU-014 enriches Run detail with workspace/MCP/telemetry sub-cards in Identity Provenance, Approvals/Data Capture in governance panel, Budget Detail drill-through, and guardrail events in gateway panel. Actual cell changes: Approvals N/A→P, Data capture N/A→P in 11.5c. WU-015 adds FinOps drill-through links (Budgets, Budget Detail, Chargeback) to Sessions list and Identity & Investigation context bar to Session detail. Cell changes: API keys × Sessions N/A→P (01-ORG), Budgets × Sessions N/A→P (05-FINOPS). WU-016 adds pending approvals count, capture policy count, and Approvals drill-through to Request flow governance card; Data Capture drill-through and capture policy count to Request explorer governance evidence. Cell changes: Request flow × Approvals N/A→P, Request explorer × Data capture N/A→P in 11.5c. WU-017 adds guardrail rule count and RPM-limited route count to Model Usage gateway posture card with Guardrails and Rate Limits drill-through links. Cell changes: Guardrails P→S, Rate limits P→S in 11.5c.

---

### 04 — Safety & Governance

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 04-Self | 05-FinOps |
|--------|----------|--------|------------|------------|---------|-----------|
| **A** — Tool Governance | Tool registry, Tool policies, MCP servers, Search tools, Policy dry run | P:6 S:7 | OK | P:10 | P:2 | P:3 |
| **B** — Exception Workflows | Approvals, Alert rules | S:3 P:8 | P:1 | OK | P:1 | S:5 |
| **C** — Data & Security | Data capture, Security, Tags | P:1 | P:1 | P:1 | P:2 | S:3 |
| **D** — Evidence & Audit | Audit log, Governance pack | P:2 | OK | OK | P:2 | OK |

**Hot spots**: 04-A x 01 closed 7 PARTIALs by WU-004 (tool registry and tool policies now have Org & Access Scope posture cards with org, user, access-group, API key, and MCP context; drill-through to Organization, Users, Workspaces, Access Groups, API Keys, MCP Registry; **P:6** remaining). 04-B x 05 GAPs closed by WU-002 (**S:4**). 04-A x 05 GAP closed by WU-001 (**P:5** remaining). 04-C x 05 GAP closed by WU-003 (**S:3**). 04-B x 02 updated by WU-007: Alert rules×Response cache P→S (**P:3** remaining). 04-B x 03 updated by WU-007: Approvals×Runs list/Run detail/Request flow/Request explorer P→S (**P:2** remaining — both Monitoring columns). 04-C x 01 updated by WU-008: Data capture×Org profile P→S, ×MCP registry P→S, Tags×Org profile P→S, ×Workspaces P→S, ×MCP registry P→S (**P:3** remaining). 04-C x 02 corrected to **P:3** (Data capture × Provider profiles/Response cache/Rate limits). 04-C x 03 updated by WU-009: Data capture × Runs list/Run detail/Request flow/Request explorer P→S. Recount from current matrix: **P:2** remaining (Analytics overview × Data capture + Monitoring × Security). 04-D x 01/02/03/05 updated by WU-010: Cross-Feature Evidence Posture card (amber theme) added to Audit Log and Governance Pack via `GET /analytics/evidence-audit-cross-posture` with FinOps, Org, Gateway, and Observe context. 10 cells P→S (Audit log×Budgets/Budget detail/Chargeback/Ledger/Org profile, Governance pack×Budgets/Budget detail/Chargeback/Org profile/Rate limits). 04-D × 01 moves from **P:11** to **P:2** (Onboarding only), 04-D × 02 moves from **P:2** to **OK**, 04-D × 03 moves from **P:10** to **OK**, 04-D × 05 moves from **P:7** to **OK**. WU-011 closes all non-diagonal self-cohesion PARTIALs across all 4 bundles via Governance Cohesion posture card (rose theme, `GET /analytics/governance-internal-posture`). 51 off-diagonal cells P→S. Only diagonal cells remain PARTIAL (self×self). 04-A × 04 moves from **P:10** to **P:2**, 04-B × 04 moves from **P:11** to **P:1**, 04-C × 04 moves from **P:15** to **P:2**, 04-D × 04 moves from **P:14** to **P:2**. WU-012 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/tool-registry-runtime-posture`) to Tool Registry with workspace scope, API key attribution, MCP scope, gateway runtime, observe evidence, and budget linkage. All 10 target cells already STRONG — no column count changes. WU-013 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/tool-policies-runtime-posture`) to Tool Policies with scope context, gateway enforcement, observe evidence, budget context, and ledger context. 2 cells closed: Tool policies × Budgets P→S, × Ledger P→S. 04-A × 05 moves from **P:5** to **P:3**. WU-014 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/approvals-runtime-posture`) to Approvals with requester context, gateway escalation, observe evidence, monitoring context, and budget context. 1 cell closed: Approvals × Monitoring P→S. 04-B × 03 moves from **P:2** to **P:1**. WU-015 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/data-capture-runtime-posture`) to Data Capture with capture scope, gateway evidence, observe evidence, budget context, and ledger context. 4 cells closed: Data capture × Budgets P→S, × Ledger P→S (11.6a), × Provider profiles P→S, × Response cache P→S (11.6b). 04-C × 01 moves from **P:3** to **P:1**, 04-C × 02 moves from **P:3** to **P:1**, 04-C × 05 updated. WU-016 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/security-runtime-posture`) to Security with identity context, gateway posture, observe evidence, monitoring context, and FinOps context. 5 cells closed: Security × Chargeback P→S, × Ledger P→S, × Org profile P→S, × Workspaces P→S (11.6a), × Monitoring P→S (11.6b). 04-C × 03 moves from **P:2** to **P:1**. WU-017 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/alert-rules-runtime-posture`) to Alert Rules with ops context, gateway runtime, observe evidence, and FinOps context. 4 cells closed: Alert rules × Chargeback P→S (11.6a), × Model gateway P→S, × Rate limits P→S, × Monitoring P→S (11.6b). 04-B × 02 moves from **P:3** to **P:1**, 04-B × 03 moves from **P:1** to **OK**, 04-B × 05 updated. WU-018 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/audit-log-runtime-posture`) to Audit Log with evidence scope, gateway lineage, observe lineage, and FinOps lineage. All 10 target cells already STRONG from prior WUs — no cell state changes. WU-019 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/governance-pack-runtime-posture`) to Governance Pack with scope context, governance sources, monitoring evidence, and FinOps evidence. All 8 target cells already STRONG from prior WUs — no cell state changes. WU-020 adds Runtime Scope & Evidence posture card (cyan theme, `GET /analytics/tags-runtime-posture`) to Tags with taxonomy scope, governance attribution, observe attribution, and FinOps attribution. All 10 target cells already STRONG from prior WUs — no cell state changes.

---

### 05 — FinOps

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 04-Safety | 05-Self | 06-Build | 07-Platform |
|--------|----------|--------|------------|------------|-----------|---------|----------|-------------|
| **A** — Budget Control | Budgets, Budget detail, Budget overrides | P:1 | P:1 | G:10 P:29 | P:1 | G:4 P:18 | G:12 P:31 | G:1 P:5 |
| **B** — Billing & Recon | Billing periods, Billing period detail | G:1 P:7 | OK | P:30 | OK | P:12 | P:26 | OK |
| **C** — Attribution | Chargeback | OK | OK | P:15 | OK | G:1 P:5 | P:13 | OK |
| **D** — Compliance | Ledger | P:1 | P:1 | P:4 | P:1 | G:1 P:6 | — | OK |

**Hot spots**: WU-018 added Billing Detail Evidence Posture endpoint and emerald card to Billing Period Detail with identity, gateway, observe, and build context. 3 cells P→S: Billing period detail × Users (05-B × 01), × Sessions list (05-B × 03), × Replay lab (05-B × 06, P:25 → **P:24**). WU-019 added Chargeback Attribution Posture endpoint and emerald card to Chargeback with identity, runtime, monitoring, and optimization context. 3 cells P→S: Chargeback × Users (05-C × 01), × Monitoring (05-C × 03), × Optimization opportunities (05-C × 06). Prior: WU-017 added billing reconciliation posture (2 cells P→S).

---

### 06 — Build & Improve

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 05-FinOps | 06-Self |
|--------|----------|--------|------------|------------|-----------|---------|
| **A** — Interactive Build | Playground, Prompts list, Prompt detail | P:5 | P:3 | P:16 | P:2 | P:9 |
| **B** — Managed Execution | Agents, Workflows, Vector stores | P:3 | P:2 | P:5 | P:2 | P:2 |
| **C** — Eval & Replay | Datasets, Eval studio, Experiments, Replay, Runbooks | P:8 | P:2 | P:24 | P:3 | P:14 |
| **D** — Optimization | Optimization opp/sim, Model scorecards | P:7 | OK | P:20 | P:5 | P:11 |

**Hot spots**: No GAPs in Build & Improve — all relationships are PARTIAL or better. WU-010 closed 35 Gateway cells to STRONG. WU-012 closed 5 more Gateway cells — 06-C × 02 down from P:4 to **P:2** (Replay lab/exp × RL closed), 06-D × 02 is now **OK** (Opt opp/sim × RL and Model scorecards × RC closed). Residual PARTIALs in 02 column are mostly Response cache columns. Highest PARTIAL density is in 06-C x 03 (24 partials between eval/replay and observe).

---

### 07 — Platform & Utility

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 04-Safety | 05-FinOps | 06-Build | 07-Self |
|--------|----------|--------|------------|------------|-----------|-----------|----------|---------|
| **A** — Platform Lifecycle | All organizations | P:2 | OK | P:1 | P:2 | P:4 | — | P:1 |
| **B** — Platform Settings | Platform settings | P:1 | OK | OK | P:1 | P:3 | — | P:1 |
| **C** — Utility Collapse | Plugins | OK | — | — | — | — | P:1 | OK |

**Hot spots**: None — Platform is the leanest feature family with no GAPs and mostly light PARTIALs.

---

### 08 — Planned Architecture

No cohesion matrix — features are not yet shipped. Status tracked in GAP-MATRIX.md only.

---

## 2. Bundle Contents — Minor Feature Status

Each minor feature's GAP-MATRIX completion status. See per-folder GAP-MATRIX.md for full column detail.

### 01 — Org & Access

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Organization profile | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| A | Org settings | `LEGACY` | `LEGACY` | `NO` | `RE-AUDIT REQUIRED` |
| B | Users | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Workspaces | `OK` | `OK` | `OK` | `AUDITED` |
| B | Access groups | `OK` | `OK` | `OK` | `RE-AUDITED: PARTIAL` |
| B | API keys | `OK` | `OK` | `OK` | `RE-AUDITED: PARTIAL` |
| C | Onboarding | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Integrations | `LEGACY` | `LEGACY` | `OK` | `RE-AUDIT REQUIRED` |
| C | Telemetry | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | MCP registry | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| D | AI hub | `OK` | `OK` | `OK` | `AUDITED` |
| D | Projects | `LEGACY` | `LEGACY` | `NO` | `RE-AUDIT REQUIRED` |
| D | Team models | `LEGACY` | `LEGACY` | `NO` | `RE-AUDIT REQUIRED` |

### 02 — Gateway & Routing

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Provider profiles | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| A | Model gateway | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| B | Guardrails | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| C | Response cache | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| C | Rate limits | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |

### 03 — Observe

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Workspace dashboard | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| A | Analytics overview | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Runs list | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Run detail | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Sessions list | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Session detail | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Request flow | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Request flow focus | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Request explorer | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Model usage | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Analytics economics | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Cost and savings | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Billing summary | `LEGACY` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Outcomes and ROI | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Analytics users | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Analytics user detail | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Model scorecards | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| D | Engineering | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| D | Monitoring | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |

### 04 — Safety & Governance

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | MCP servers | `LEGACY` | `LEGACY` | `OK` | `RE-AUDITED: OK` |
| A | Search tools | `LEGACY` | `LEGACY` | `OK` | `RE-AUDITED: OK` |
| A | Tool registry | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |
| A | Tool policies | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |
| A | Policy dry run | `LEGACY` | `LEGACY` | `OK` | `RE-AUDITED: OK` |
| B | Approvals | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Alert rules | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Data capture | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |
| C | Security | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |
| C | Tags | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |
| D | Audit log | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| D | Governance pack | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |

### 05 — FinOps

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Budgets | `OK` | `OK` | `NO` | `RE-AUDITED: PARTIAL (WU-001)` |
| A | Budget detail | `OK` | `OK` | `NO` | `RE-AUDITED: PARTIAL (WU-001)` |
| A | Budget overrides | `PARTIAL` | `OK` | `NO` | `RE-AUDITED: PARTIAL (WU-001)` |
| B | Billing periods | `OK` | `OK` | `OK` | `RE-AUDITED: OK (WU-011)` |
| B | Billing period detail | `OK` | `OK` | `OK` | `RE-AUDITED: OK (WU-011)` |
| C | Chargeback | `OK` | `OK` | `OK` | `RE-AUDITED: PARTIAL (WU-012)` |
| D | Ledger | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |

### 06 — Build & Improve

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Playground | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| A | Prompts list | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| A | Prompt detail and versions | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |
| B | Agents list | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Agent detail | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Agent memory | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Workflows list | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Workflow detail | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Workflow run detail | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Vector stores list | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Vector store detail | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Datasets | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Evaluation studio | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Experiments | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Replay lab | `PARTIAL` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Replay experiment detail | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Runbooks | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| D | Optimization opportunities | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| D | Optimization simulator | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| D | Model scorecards | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |

### 07 — Platform & Utility

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | All organizations | `OK` | `OK` | `OK` | `RE-AUDITED: OK` |
| B | Platform settings | `OK` | `OK` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Plugins | `PARTIAL` | `LEGACY` | `PARTIAL` | `RE-AUDITED: PARTIAL` |

### 08 — Planned Architecture

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Gateway service split | `PARTIAL` | `MISSING` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| A | Gateway module review | `PARTIAL` | `N/A` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| A | Router collapse | `PARTIAL` | `N/A` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| A | Legacy deprecation | `PARTIAL` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| B | Scope-aware enforcement | `PARTIAL` | `N/A` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Pipeline studio | `MISSING` | `MISSING` | `MISSING` | `RE-AUDITED: MISSING` |
| C | API explorer | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| C | Help hub | `MISSING` | `MISSING` | `MISSING` | `RE-AUDITED: MISSING` |
| D | Theme refresh | `PARTIAL` | `PARTIAL` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| D | Docs IA | `PARTIAL` | `N/A` | `PARTIAL` | `RE-AUDITED: PARTIAL` |
| D | Repo naming cleanup | `PARTIAL` | `N/A` | `PARTIAL` | `RE-AUDITED: PARTIAL` |

---

## 3. GAP Summary — Highest Priority

Bundles ranked by total cross-feature GAP count (most urgent first):

| Rank | Bundle | Total GAPs | Worst Relationship | Root Cause |
|------|--------|------------|--------------------|-----------| 
| 1 | **05-A** Budget Control | **22** | 05-A x 07-Platform (0G) | WU-001 closed 8 GAPs in 05-A × 01-Org. WU-003 closed 4 PARTIALs in 05-A × 03-Observe. WU-005 closed 12 PARTIALs in 05-A × 06-Build. WU-006 closed 6 PARTIALs in 05-A × 07-Platform (Budgets/Budget detail/Overrides × All orgs/Platform settings P→S). |
| 2 | **01-B** Identity & Scope | **9** | 01-B x 05-FinOps (5G) | Access groups and API keys propagate through FinOps, Observe, Safety & Governance, and Build & Improve. WU-006 closed 22 Safety cells, WU-007 closed 22 Build cells to STRONG. WU-013 closed 14 internal and 8 Platform cells to STRONG. Remaining pressure is FinOps and Observe drill-through. |
| 2b | **01-A** Org Foundation | **5** | 01-A x 04-Safety (5G) | Organization profile Safety & Governance row has 5 remaining GAPs (MCP servers, search tools, policy dry run, approvals, data capture). WU-014 closed 4 GAPs to PARTIAL (tool registry, tool policies, governance pack, tags). |
| 3 | **03-B** Investigation | **0** | — | WU-002 closed all FinOps budget-detail GAPs. All 4 investigation surfaces now show inline budget posture with drill-through. |
| 4 | **04-B** Exception Workflows | **0** | — | WU-007 adds Gateway & Observe Runtime posture cards to Approvals and Alert Rules. 5 cells closed (Approvals×Runs list/Run detail/Request flow/Request explorer P→S, Alert rules×Response cache P→S). Prior: WU-006 Org & Access card, WU-002 FinOps Budget Context card. |
| 5 | **02-C** Performance Controls | **0** | — | All FinOps bridges closed by WU-002. WU-016 added cache economics posture (15 cells closed). WU-017 added rate-limit scope posture (15 cells closed). Bundle complete. |
| 6 | **05-B** Billing & Recon | **1** | 05-B x 01-Org (1G) | Remaining org and user billing ownership bridges are still uneven |
| 7 | **05-C** Attribution | **1** | 05-C x 05-Self (1G) | Chargeback internal cohesion gap with budget detail |
| 8 | **05-D** Compliance | **1** | 05-D x 05-Self (1G) | Ledger internal cohesion gap with budget detail |
| 9 | **02-A** Provider & Routing | **1** | 02-A x 05-FinOps (1G) | Provider profiles missing budget override bridge |
| 10 | **03-A** Overview & Entry | **0** | — | WU-003 closed the analytics overview budget detail GAP via overview-finops-budget-posture endpoint |
| 11 | **03-C** Economics & Intel | **0** | — | WU-003 closed the model usage budget detail GAP via model-budget-utilization endpoint |
| 12 | **04-A** Tool Governance | **1** | 04-A x 05-FinOps (1G) | Tool registry missing budget detail bridge |
| 13 | **04-C** Data & Security | **0** | — | WU-009 adds Gateway & Observe Runtime posture cards to Data Capture, Security, and Tags. 4 cells closed (Data capture × Runs list/Run detail/Request flow/Request explorer P→S). Prior: WU-008 Org & Access card (5 cells), WU-003 FinOps Budget Attribution card. |
| 14 | **04-D** Evidence & Audit | **0** | — | WU-018/019 add Runtime Scope & Evidence posture cards (cyan) to Audit Log and Governance Pack. All target cells already STRONG from prior WUs — no cell changes needed. Remaining PARTIALs are diagonal self-cohesion (P:2) and Onboarding (P:2). Prior: WU-011 self-cohesion closure, WU-010 Cross-Feature Evidence card. |
| 15 | **01-D** Capability Catalog | **0** | — | WU-010 closed the AI hub budget detail GAP and all Safety & Governance and Platform gaps |
| 15 | **07-A** Platform Lifecycle | **0** | — | — |

**Pattern**: Budget detail (05-A) is the root cause behind **most GAPs across the entire product**. Fixing budget detail unlocks cohesion improvements in 6 of the other 7 major features.

---

## 4. Active Work Units

Work units live inside each major feature folder at `{folder}/WORK-UNITS/WU-NNN-<slug>.md`. This section indexes all active WUs across the product.

| ID | Owner Folder | Target | Paired Features | Status | Bundle |
|----|--------------|--------|-----------------|--------|--------|
| WU-001 | 01-ORG-AND-ACCESS | Access groups × FinOps scoping | 05-FINOPS | COMPLETED | 01-B |
| WU-002 | 01-ORG-AND-ACCESS | API keys × budget ownership | 05-FINOPS | COMPLETED | 01-B |
| WU-003 | 01-ORG-AND-ACCESS | Access groups × Observe investigation | 03-OBSERVE | COMPLETED | 01-B |
| WU-004 | 01-ORG-AND-ACCESS | Org profile × FinOps rollup | 05-FINOPS | COMPLETED | 01-A |
| WU-005 | 01-ORG-AND-ACCESS | Users × FinOps attribution | 05-FINOPS | COMPLETED | 01-B |
| WU-006 | 01-ORG-AND-ACCESS | Identity & scope × Safety & Governance | 04-SAFETY-AND-GOVERNANCE | COMPLETED | 01-B |
| WU-007 | 01-ORG-AND-ACCESS | Identity & scope × Build & Improve | 06-BUILD-AND-IMPROVE | COMPLETED | 01-B |
| WU-008 | 01-ORG-AND-ACCESS | Org profile × Observe & Gateway rollups | 03-OBSERVE, 02-GATEWAY | COMPLETED | 01-A |
| WU-009 | 01-ORG-AND-ACCESS | Onboarding setup completeness | 02/03/04/05 | COMPLETED | 01-C |
| WU-010 | 01-ORG-AND-ACCESS | AI hub × governance & org links | 04/05/07 | COMPLETED | 01-D |
| WU-011 | 01-ORG-AND-ACCESS | API keys × Observe dimension | 03-OBSERVE | COMPLETED | 01-B |
| WU-012 | 01-ORG-AND-ACCESS | Workspace × Observe/FinOps strengthen | 03/05 | COMPLETED | 01-B |
| WU-013 | 01-ORG-AND-ACCESS | Internal cohesion tightening | 07-PLATFORM | COMPLETED | 01-A/B/C/D |
| WU-014 | 01-ORG-AND-ACCESS | Organization profile cross-suite rollups refresh | 03/04/05 | COMPLETED | 01-A |
| WU-015 | 01-ORG-AND-ACCESS | Onboarding cross-suite readiness refresh | 02/03/04/05 | COMPLETED | 01-C |
| WU-016 | 01-ORG-AND-ACCESS | Users scope attribution and governance refresh | 03/04/05 | COMPLETED | 01-B |
| WU-017 | 01-ORG-AND-ACCESS | Workspaces scope backbone refresh | 03/04/05 | DONE | 01-B |
| WU-018 | 01-ORG-AND-ACCESS | Access groups scope propagation refresh | 02/03/04/05/06 | DONE | 01-B |
| WU-019 | 01-ORG-AND-ACCESS | API keys runtime FinOps and Observe refresh | 02/03/04/05 | DONE | 01-B |
| WU-020 | 01-ORG-AND-ACCESS | Telemetry FinOps and governance bridge refresh | 04/05 | DONE | 01-C |
| WU-021 | 01-ORG-AND-ACCESS | MCP registry runtime governance and Observe refresh | 02/03/04/05/06 | DONE | 01-C |
| WU-022 | 01-ORG-AND-ACCESS | AI hub catalog runtime FinOps refresh | 02/03/04/05 | DONE | 01-D |
| WU-001 | 02-GATEWAY-AND-ROUTING | Provider profiles × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 02-A |
| WU-002 | 02-GATEWAY-AND-ROUTING | Performance controls × FinOps budget bridge | 05-FINOPS | COMPLETED | 02-C |
| WU-003 | 02-GATEWAY-AND-ROUTING | Model gateway × FinOps deepening | 05-FINOPS | COMPLETED | 02-A |
| WU-004 | 02-GATEWAY-AND-ROUTING | Provider profiles × Org & Access links | 01-ORG-AND-ACCESS | COMPLETED | 02-A |
| WU-005 | 02-GATEWAY-AND-ROUTING | Gateway & guardrails × Org scope | 01-ORG-AND-ACCESS | COMPLETED | 02-A/B |
| WU-006 | 02-GATEWAY-AND-ROUTING | Provider profiles × Observe visibility | 03-OBSERVE | COMPLETED | 02-A |
| WU-007 | 02-GATEWAY-AND-ROUTING | Gateway & perf controls × Observe strengthen | 03-OBSERVE | COMPLETED | 02-A/C |
| WU-008 | 02-GATEWAY-AND-ROUTING | Guardrails × Observe traceability | 03-OBSERVE | COMPLETED | 02-B |
| WU-009 | 02-GATEWAY-AND-ROUTING | Gateway × Safety & Governance deepening | 04-SAFETY-AND-GOVERNANCE | COMPLETED | 02-A/B/C |
| WU-010 | 02-GATEWAY-AND-ROUTING | Gateway × Build & Improve integration | 06-BUILD-AND-IMPROVE | COMPLETED | 02-A/B/C |
| WU-011 | 02-GATEWAY-AND-ROUTING | Performance controls × Org & scope | 01/07 | COMPLETED | 02-C |
| WU-012 | 02-GATEWAY-AND-ROUTING | Gateway internal & platform cohesion | 02/06/07 | COMPLETED | 02-A/B/C/D |
| WU-013 | 02-GATEWAY-AND-ROUTING | Provider profiles runtime FinOps and governance refresh | 01/03/04/05/06 | COMPLETED | 02-A |
| WU-014 | 02-GATEWAY-AND-ROUTING | Model gateway control plane bridge refresh | 01/03/04/07 | COMPLETED | 02-A |
| WU-015 | 02-GATEWAY-AND-ROUTING | Guardrails runtime traceability refresh | 01/03/04/05/06 | COMPLETED | 02-B |
| WU-016 | 02-GATEWAY-AND-ROUTING | Response cache economics and evidence refresh | 01/03/04/05/06 | COMPLETED | 02-C |
| WU-017 | 02-GATEWAY-AND-ROUTING | Rate limits scope and throttle explainability refresh | 01/03/04/05/06 | COMPLETED | 02-C |
| WU-001 | 03-OBSERVE | Investigation × access-group scope | 01-ORG-AND-ACCESS | COMPLETED | 03-B |
| WU-002 | 03-OBSERVE | Investigation × FinOps budget bridge | 05-FINOPS | COMPLETED | 03-B |
| WU-003 | 03-OBSERVE | Overview & economics × FinOps budget bridge | 05-FINOPS | COMPLETED | 03-A/C |
| WU-004 | 03-OBSERVE | Investigation × Org identity & scope | 01-ORG-AND-ACCESS | COMPLETED | 03-B |
| WU-005 | 03-OBSERVE | Investigation × Safety & Governance traceability | 04-SAFETY-AND-GOVERNANCE | COMPLETED | 03-B |
| WU-006 | 03-OBSERVE | Investigation × Gateway runtime context | 02-GATEWAY-AND-ROUTING | COMPLETED | 03-B |
| WU-007 | 03-OBSERVE | Economics & outcomes × FinOps strengthening | 05-FINOPS | COMPLETED | 03-C/D |
| WU-008 | 03-OBSERVE | Overview × cross-feature posture cards | 01/02/04 | COMPLETED | 03-A |
| WU-009 | 03-OBSERVE | Economics & model intel × Gateway links | 01/02/03/04 | COMPLETED | 03-C |
| WU-010 | 03-OBSERVE | Monitoring & ops × governance integration | 01/02/03/04 | COMPLETED | 03-D |
| WU-011 | 03-OBSERVE | User analytics & overview × Org links | 01/03 | COMPLETED | 03-A/C |
| WU-012 | 03-OBSERVE | Analytics overview scope posture refresh | 01/02/04 | COMPLETED | 03-A |
| WU-013 | 03-OBSERVE | Runs list investigation bridge refresh | 01/02/04/05 | COMPLETED | 03-B |
| WU-014 | 03-OBSERVE | Run detail runtime evidence refresh | 01/02/04/05 | COMPLETED | 03-B |
| WU-015 | 03-OBSERVE | Sessions investigation scope refresh | 01/05 | COMPLETED | 03-B |
| WU-016 | 03-OBSERVE | Request analysis scope and evidence refresh | 01/02/04/05 | COMPLETED | 03-B |
| WU-017 | 03-OBSERVE | Model usage economics and runtime refresh | 01/02/05 | COMPLETED | 03-C |
| WU-018 | 03-OBSERVE | Analytics users outcomes and identity refresh | 01/02/05 | COMPLETED | 03-C |
| WU-019 | 03-OBSERVE | Monitoring telemetry ops and governance refresh | 01/02/04/05 | COMPLETED | 03-D |
| WU-020 | 03-OBSERVE | Scorecards replay and runbooks support refresh | 01/02/04 | COMPLETED | 03-C/D |
| WU-001 | 04-SAFETY-AND-GOVERNANCE | Tool registry × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 04-A |
| WU-002 | 04-SAFETY-AND-GOVERNANCE | Approvals & alert rules × FinOps budget bridge | 05-FINOPS | COMPLETED | 04-B |
| WU-003 | 04-SAFETY-AND-GOVERNANCE | Tags × FinOps budget detail bridge | 05-FINOPS | COMPLETED | 04-C |
| WU-004 | 04-SAFETY-AND-GOVERNANCE | Tool governance × Org & Access scope | 01-ORG-AND-ACCESS | COMPLETED | 04-A |
| WU-005 | 04-SAFETY-AND-GOVERNANCE | Tool governance × Gateway & Observe traceability | 02/03 | COMPLETED | 04-A |
| WU-006 | 04-SAFETY-AND-GOVERNANCE | Exception workflows × Org & Access scope | 01-ORG-AND-ACCESS | COMPLETED | 04-B |
| WU-007 | 04-SAFETY-AND-GOVERNANCE | Exception workflows × Gateway & Observe | 02/03 | COMPLETED | 04-B |
| WU-008 | 04-SAFETY-AND-GOVERNANCE | Data protection × Org & Access scope | 01-ORG-AND-ACCESS | COMPLETED | 04-C |
| WU-009 | 04-SAFETY-AND-GOVERNANCE | Data protection × Gateway & Observe | 02/03 | COMPLETED | 04-C |
| WU-010 | 04-SAFETY-AND-GOVERNANCE | Evidence & audit × cross-feature linkage | 01/02/03/05 | COMPLETED | 04-D |
| WU-011 | 04-SAFETY-AND-GOVERNANCE | Internal cohesion tightening | 04-SELF | COMPLETED | 04-A/B/C/D |
| WU-012 | 04-SAFETY-AND-GOVERNANCE | Tool registry runtime FinOps scope refresh | 01/02/03/05 | COMPLETED | 04-A |
| WU-013 | 04-SAFETY-AND-GOVERNANCE | Tool policies runtime scope refresh | 01/02/03/05 | COMPLETED | 04-A |
| WU-014 | 04-SAFETY-AND-GOVERNANCE | Approvals exception cross suite refresh | 01/02/03/05 | COMPLETED | 04-B |
| WU-015 | 04-SAFETY-AND-GOVERNANCE | Data capture evidence runtime refresh | 01/02/03/05 | COMPLETED | 04-C |
| WU-016 | 04-SAFETY-AND-GOVERNANCE | Security scope runtime evidence refresh | 01/02/03/05 | COMPLETED | 04-C |
| WU-017 | 04-SAFETY-AND-GOVERNANCE | Alert rules ops FinOps governance refresh | 01/02/03/05 | COMPLETED | 04-B |
| WU-018 | 04-SAFETY-AND-GOVERNANCE | Audit log evidence lineage refresh | 01/02/03/05 | COMPLETED | 04-D |
| WU-019 | 04-SAFETY-AND-GOVERNANCE | Governance pack compliance closure refresh | 01/02/03/05 | COMPLETED | 04-D |
| WU-020 | 04-SAFETY-AND-GOVERNANCE | Tags taxonomy attribution refresh | 01/02/03/05 | COMPLETED | 04-C |
| WU-001 | 05-FINOPS | Budget control × Org & Access scope | 01-ORG-AND-ACCESS | COMPLETED | 05-A |
| WU-002 | 05-FINOPS | Budget control × Gateway & Routing | 02-GATEWAY-AND-ROUTING | COMPLETED | 05-A |
| WU-003 | 05-FINOPS | Budget detail × Observe surfaces bridge | 03-OBSERVE | COMPLETED | 05-A |
| WU-004 | 05-FINOPS | Budget control × Safety & Governance | 04-SAFETY-AND-GOVERNANCE | COMPLETED | 05-A |
| WU-005 | 05-FINOPS | Budget detail × Build & Improve surfaces | 06-BUILD-AND-IMPROVE | COMPLETED | 05-A |
| WU-006 | 05-FINOPS | Budget control × Platform scope | 07-PLATFORM-AND-UTILITY | COMPLETED | 05-A |
| WU-007 | 05-FINOPS | Billing × Org access-group scope | 01-ORG-AND-ACCESS | COMPLETED | 05-B |
| WU-008 | 05-FINOPS | Internal FinOps cohesion | 05-SELF | COMPLETED | 05-A/C/D |
| WU-009 | 05-FINOPS | Budget control × Observe PARTIAL strengthen | 03-OBSERVE | COMPLETED | 05-A |
| WU-010 | 05-FINOPS | Budget control × Build PARTIAL strengthen | 06-BUILD-AND-IMPROVE | COMPLETED | 05-A |
| WU-011 | 05-FINOPS | Billing × cross-feature strengthen | 02/04/07 | COMPLETED | 05-B |
| WU-012 | 05-FINOPS | Chargeback × cross-feature strengthen | 01/02/04/07 | COMPLETED | 05-C |
| WU-013 | 05-FINOPS | Ledger × cross-feature strengthen | 01/03/04/07 | COMPLETED | 05-D |
| WU-014 | 05-FINOPS | Budgets scope runtime governance refresh | 01/02/03/04/07 | COMPLETED | 05-A |
| WU-015 | 05-FINOPS | Budget detail drillback refresh | 01/02/03/04/06 | COMPLETED | 05-A |
| WU-016 | 05-FINOPS | Budget overrides exception refresh | 01/02/03/04/07 | COMPLETED | 05-A |
| WU-017 | 05-FINOPS | Billing periods reconciliation refresh | 01/02/03/04/06/07 | COMPLETED | 05-B |
| WU-018 | 05-FINOPS | Billing detail evidence refresh | 01/02/03/04/06/07 | COMPLETED | 05-B |
| WU-019 | 05-FINOPS | Chargeback attribution refresh | 01/02/03/04/06/07 | COMPLETED | 05-C |
| WU-001 | 06-BUILD-AND-IMPROVE | Interactive Build × Org & Gateway scope | 01/02 | NOT_STARTED | 06-A |
| WU-002 | 06-BUILD-AND-IMPROVE | Interactive Build × Observe bridge | 03-OBSERVE | NOT_STARTED | 06-A |
| WU-003 | 06-BUILD-AND-IMPROVE | Managed assets × cross-feature strengthen | 01/02/03/05 | NOT_STARTED | 06-B |
| WU-004 | 06-BUILD-AND-IMPROVE | Evaluation & Replay × Org & Gateway scope | 01/02 | NOT_STARTED | 06-C |
| WU-005 | 06-BUILD-AND-IMPROVE | Evaluation & Replay × Observe bridge | 03-OBSERVE | NOT_STARTED | 06-C |
| WU-006 | 06-BUILD-AND-IMPROVE | Optimization × Org & Gateway scope | 01/02 | NOT_STARTED | 06-D |
| WU-007 | 06-BUILD-AND-IMPROVE | Optimization × Observe bridge | 03-OBSERVE | NOT_STARTED | 06-D |
| WU-008 | 06-BUILD-AND-IMPROVE | Build × FinOps strengthen | 05-FINOPS | NOT_STARTED | 06-A/C/D |
| WU-009 | 06-BUILD-AND-IMPROVE | Internal Build cohesion tightening | 06-SELF | NOT_STARTED | 06-A/B/C/D |
| WU-010 | 06-BUILD-AND-IMPROVE | Playground live lab refresh | 01/02/03/05 | NOT_STARTED | 06-A |
| WU-011 | 06-BUILD-AND-IMPROVE | Prompts list registry refresh | 01/02/03/05 | NOT_STARTED | 06-A |
| WU-012 | 06-BUILD-AND-IMPROVE | Prompt detail runtime loop refresh | 01/02/03/05 | NOT_STARTED | 06-A |
| WU-013 | 06-BUILD-AND-IMPROVE | Agents list lifecycle refresh | 01/02/03/05 | NOT_STARTED | 06-B |
| WU-014 | 06-BUILD-AND-IMPROVE | Agent detail memory governance refresh | 02/03/04 | NOT_STARTED | 06-B |
| WU-015 | 06-BUILD-AND-IMPROVE | Workflows list catalog refresh | 01/02/03/05 | NOT_STARTED | 06-B |
| WU-016 | 06-BUILD-AND-IMPROVE | Workflow detail cross loop refresh | 01/02/03/05 | NOT_STARTED | 06-B |
| WU-017 | 06-BUILD-AND-IMPROVE | Workflow run evidence refresh | 02/03/04/05 | NOT_STARTED | 06-B |
| WU-018 | 06-BUILD-AND-IMPROVE | Datasets evaluation asset refresh | 01/03/05 | NOT_STARTED | 06-C |
| WU-019 | 06-BUILD-AND-IMPROVE | Evaluation studio parent refresh | 01/02/03/05 | NOT_STARTED | 06-C |
| WU-020 | 06-BUILD-AND-IMPROVE | Experiments comparison refresh | 01/02/03/05 | NOT_STARTED | 06-C |
| WU-021 | 06-BUILD-AND-IMPROVE | Replay lab mode refresh | 02/03/05 | NOT_STARTED | 06-C |
| WU-022 | 06-BUILD-AND-IMPROVE | Replay result analysis refresh | 02/03/05 | NOT_STARTED | 06-C |
| WU-023 | 06-BUILD-AND-IMPROVE | Runbooks remediation loop refresh | 02/03/04/05 | NOT_STARTED | 06-C |
| WU-024 | 06-BUILD-AND-IMPROVE | Optimization opportunities rationale refresh | 02/03/05 | NOT_STARTED | 06-D |
| WU-025 | 06-BUILD-AND-IMPROVE | Optimization simulator decision refresh | 02/03/05 | NOT_STARTED | 06-D |
| WU-026 | 06-BUILD-AND-IMPROVE | Model scorecards intelligence refresh | 01/02/03/05 | NOT_STARTED | 06-D |
| WU-027 | 06-BUILD-AND-IMPROVE | Vector stores list lifecycle refresh | 01/03/05 | NOT_STARTED | 06-B |
| WU-028 | 06-BUILD-AND-IMPROVE | Vector store detail evidence refresh | 03/05 | NOT_STARTED | 06-B |
| WU-001 | 07-PLATFORM-AND-UTILITY | All organizations delivery & posture completion | 01/02/04/05 | NOT_STARTED | 07-A |
| WU-002 | 07-PLATFORM-AND-UTILITY | Platform settings convergence & delivery completeness | 01/02/03/04/05 | NOT_STARTED | 07-B |
| WU-003 | 07-PLATFORM-AND-UTILITY | Plugins collapse & discovery ownership cleanup | 01/06 | NOT_STARTED | 07-C |
| WU-004 | 07-PLATFORM-AND-UTILITY | Platform admin cohesion & posture rollups | 01/02/03/04/06 | NOT_STARTED | 07-A/B/C |
| WU-005 | 07-PLATFORM-AND-UTILITY | All organizations posture refresh | 01/02/03/04/05/06 | NOT_STARTED | 07-A |
| WU-006 | 07-PLATFORM-AND-UTILITY | Platform settings converged posture refresh | 01/02/03/04/05/06 | NOT_STARTED | 07-B |
| WU-007 | 07-PLATFORM-AND-UTILITY | Plugins collapse ownership refresh | 01/03/04/06 | NOT_STARTED | 07-C |
| WU-001 | 08-PLANNED-ARCHITECTURE | Rust runtime boundary cleanup | 02/03/04/05 | NOT_STARTED | 08-A |
| WU-002 | 08-PLANNED-ARCHITECTURE | Sidecar collapse and runtime consolidation | 02/03/04 | NOT_STARTED | 08-A |
| WU-003 | 08-PLANNED-ARCHITECTURE | Consumer migration and legacy cleanup | 02/03/05/06 | NOT_STARTED | 08-A |
| WU-004 | 08-PLANNED-ARCHITECTURE | Runtime scope model definition | 01/02/04 | NOT_STARTED | 08-B |
| WU-005 | 08-PLANNED-ARCHITECTURE | Scope-aware enforcement and evidence loop | 01/02/03/04 | NOT_STARTED | 08-B |
| WU-006 | 08-PLANNED-ARCHITECTURE | Pipeline studio and flow builder | 02/03/04/05/06 | NOT_STARTED | 08-C |
| WU-007 | 08-PLANNED-ARCHITECTURE | API explorer and generated Swagger UI | ALL | NOT_STARTED | 08-C |
| WU-008 | 08-PLANNED-ARCHITECTURE | In-app help hub | 01/02/03 | NOT_STARTED | 08-C |
| WU-009 | 08-PLANNED-ARCHITECTURE | Design system and dark-mode refresh | ALL | NOT_STARTED | 08-D |
| WU-010 | 08-PLANNED-ARCHITECTURE | Documentation IA and hierarchy | ALL | NOT_STARTED | 08-D |
| WU-011 | 08-PLANNED-ARCHITECTURE | Repo naming and historical cleanup | ALL | NOT_STARTED | 08-D |
| WU-012 | 08-PLANNED-ARCHITECTURE | Rust gateway split posture refresh | 02/03/04/05 | NOT_STARTED | 08-A |
| WU-013 | 08-PLANNED-ARCHITECTURE | Python hot path migration refresh | 02/03/04 | NOT_STARTED | 08-A |
| WU-014 | 08-PLANNED-ARCHITECTURE | Router collapse refresh | 02/03/05 | NOT_STARTED | 08-A |
| WU-015 | 08-PLANNED-ARCHITECTURE | Consumer migration refresh | 02/03/05/06 | NOT_STARTED | 08-A |
| WU-016 | 08-PLANNED-ARCHITECTURE | Scope aware governance runtime refresh | 01/02/03/04 | NOT_STARTED | 08-B |
| WU-017 | 08-PLANNED-ARCHITECTURE | Pipeline studio concept refresh | 02/03/04/05/06 | NOT_STARTED | 08-C |
| WU-018 | 08-PLANNED-ARCHITECTURE | API explorer surface refresh | 01/02/06/07 | NOT_STARTED | 08-C |
| WU-019 | 08-PLANNED-ARCHITECTURE | Help hub concept refresh | 01/02/03/07 | NOT_STARTED | 08-C |
| WU-020 | 08-PLANNED-ARCHITECTURE | Design system refresh pass | 06/07 | NOT_STARTED | 08-D |
| WU-021 | 08-PLANNED-ARCHITECTURE | Docs IA and repo cleanup refresh | 07/08-SUPPORT | NOT_STARTED | 08-D |

---

## 5. Completion Criteria

A bundle moves from `RE-AUDIT REQUIRED` → `IN_PROGRESS` when:
- Its folder files (GAP-MATRIX, COHESION-MATRIX, DELIVERY-STATUS) are populated
- At least one WU is created and active

A bundle moves from `IN_PROGRESS` → `DONE` when:
- All WUs for that bundle are DONE
- No GAP cells remain in the cohesion matrix for features in that bundle
- All PARTIAL cells are either closed to STRONG or justified as N/A

A bundle moves from `DONE` → `VERIFIED` when:
- A fresh re-audit confirms the DONE state still holds
