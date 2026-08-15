# RunLedger Feature Status Dashboard

Last updated: 2026-08-14

## Purpose

This file is the **cross-feature bundle status matrix**. It shows every bundle's cohesion status against every other major feature family, with GAP and PARTIAL counts computed from the per-folder COHESION-MATRIX.md files.

This file is **derived** — update the per-folder files first, then update this dashboard.

Cell notation: `G:X P:Y` = X gaps, Y partials. `P:Y` = no gaps, Y partials. `OK` = only STRONG/N/A. `—` = all N/A or no data.

---

## 1. Cross-Feature Bundle Matrix

### 01 — Org & Access

| Bundle | Features | 01-Self | 02-Gateway | 03-Observe | 04-Safety | 05-FinOps | 06-Build | 07-Platform |
|--------|----------|---------|------------|------------|-----------|-----------|----------|-------------|
| **A** — Org Foundation | Organization profile, Org settings | P:9 | P:4 | P:17 | P:8 | G:1 P:7 | P:14 | P:1 |
| **B** — Identity & Scope | Users, Workspaces, Access groups, API keys | P:24 | P:13 | G:4 P:38 | P:32 | G:9 P:14 | P:44 | P:8 |
| **C** — Onboarding & Setup | Onboarding, Integrations, Telemetry, MCP registry | P:16 | P:9 | P:20 | P:24 | P:8 | P:39 | P:6 |
| **D** — Capability Catalog | AI hub, Projects, Team models | P:5 | P:1 | P:8 | P:7 | G:1 P:4 | P:14 | P:2 |

**Hot spots**: 01-B x 05 has **9 GAPs** (access groups and API keys not yet first-class budget scopes). 01-B x 03 has **4 GAPs** (access-group scope missing in observability investigation).

---

### 02 — Gateway & Routing

| Bundle | Features | 01-Org | 02-Self | 03-Observe | 04-Safety | 05-FinOps | 06-Build | 07-Platform |
|--------|----------|--------|---------|------------|-----------|-----------|----------|-------------|
| **A** — Provider & Routing | Provider profiles, Model gateway | P:11 | P:6 | P:19 | P:15 | G:1 P:12 | P:21 | P:4 |
| **B** — Runtime Protection | Guardrails | P:6 | P:1 | P:7 | P:8 | — | P:13 | P:1 |
| **C** — Performance Controls | Response cache, Rate limits | P:5 | P:5 | P:18 | P:8 | G:2 P:8 | P:19 | P:3 |

**Hot spots**: 02-A x 05 has **1 GAP** (provider profiles missing budget override cohesion). 02-C x 05 has **2 GAPs** (cache/rate-limit detail pages missing FinOps bridges).

---

### 03 — Observe

| Bundle | Features | 01-Org | 02-Gateway | 03-Self | 04-Safety | 05-FinOps |
|--------|----------|--------|------------|---------|-----------|-----------|
| **A** — Overview & Entry | Analytics overview + dashboards | P:7 | P:3 | P:3 | P:5 | G:1 P:7 |
| **B** — Investigation | Runs, Sessions, Request flow/explorer | G:4 P:20 | P:16 | P:7 | P:28 | G:2 P:22 |
| **C** — Economics & Intel | Model usage, Economics, Cost, ROI, Users, Scorecards | P:7 | P:5 | P:12 | P:1 | G:1 P:16 |
| **D** — Ops & Monitoring | Engineering, Monitoring, Telemetry, Quality scores | P:7 | P:5 | P:8 | P:10 | P:6 |

**Hot spots**: 03-B x 01 has **4 GAPs** (access-group scope missing across investigation surfaces). 03-B x 05 has **2 GAPs** (request flow/explorer missing budget detail bridges). 03-C x 05 has **1 GAP** (model usage missing budget detail bridge).

---

### 04 — Safety & Governance

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 04-Self | 05-FinOps |
|--------|----------|--------|------------|------------|---------|-----------|
| **A** — Tool Governance | Tool registry, Tool policies, MCP servers, Search tools, Policy dry run | P:13 | P:7 | P:10 | P:10 | G:1 P:2 |
| **B** — Exception Workflows | Approvals, Alert rules | P:11 | P:4 | P:4 | P:11 | G:2 P:2 |
| **C** — Data & Security | Data capture, Security, Tags | P:18 | P:9 | P:13 | P:15 | G:1 P:3 |
| **D** — Evidence & Audit | Audit log, Governance pack | P:11 | P:7 | P:10 | P:10 | P:7 |

**Hot spots**: 04-B x 05 has **2 GAPs** (approvals disconnected from budget overrides and budget detail). 04-A x 05 has **1 GAP** (tool registry missing budget detail bridge). 04-C x 05 has **1 GAP** (tags missing budget detail bridge).

---

### 05 — FinOps

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 04-Safety | 05-Self | 06-Build | 07-Platform |
|--------|----------|--------|------------|------------|-----------|---------|----------|-------------|
| **A** — Budget Control | Budgets, Budget detail, Budget overrides | G:9 P:7 | G:6 P:5 | G:10 P:33 | G:7 P:10 | G:4 P:18 | G:12 P:31 | G:1 P:5 |
| **B** — Billing & Recon | Billing periods, Billing period detail | G:2 P:9 | P:8 | P:30 | P:10 | P:12 | P:26 | P:4 |
| **C** — Attribution | Chargeback | P:5 | P:3 | P:15 | P:5 | G:1 P:5 | P:13 | P:2 |
| **D** — Compliance | Ledger | P:3 | — | P:5 | P:2 | G:1 P:6 | — | P:1 |

**Hot spots**: 05-A is the most GAP-heavy bundle in the entire product — **49 total GAPs** across all major features. Budget detail is the single biggest cohesion blocker. 05-B x 01 has **2 GAPs** (billing periods missing access-group scope).

---

### 06 — Build & Improve

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 05-FinOps | 06-Self |
|--------|----------|--------|------------|------------|-----------|---------|
| **A** — Interactive Build | Playground, Prompts list, Prompt detail | P:5 | P:6 | P:16 | P:2 | P:9 |
| **B** — Managed Execution | Agents, Workflows, Vector stores | P:3 | P:4 | P:5 | P:2 | P:2 |
| **C** — Eval & Replay | Datasets, Eval studio, Experiments, Replay, Runbooks | P:8 | P:9 | P:24 | P:3 | P:14 |
| **D** — Optimization | Optimization opp/sim, Model scorecards | P:7 | P:9 | P:20 | P:5 | P:11 |

**Hot spots**: No GAPs in Build & Improve — all relationships are PARTIAL or better. Highest PARTIAL density is in 06-C x 03 (24 partials between eval/replay and observe).

---

### 07 — Platform & Utility

| Bundle | Features | 01-Org | 02-Gateway | 03-Observe | 04-Safety | 05-FinOps | 06-Build | 07-Self |
|--------|----------|--------|------------|------------|-----------|-----------|----------|---------|
| **A** — Platform Lifecycle | All organizations | P:4 | P:2 | P:1 | P:2 | P:4 | — | P:1 |
| **B** — Platform Settings | Platform settings | P:5 | P:2 | OK | P:1 | P:3 | — | P:1 |
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
| B | Workspaces | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Access groups | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | API keys | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Onboarding | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Integrations | `LEGACY` | `LEGACY` | `OK` | `RE-AUDIT REQUIRED` |
| C | Telemetry | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | MCP registry | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| D | AI hub | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
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
| A | MCP servers | `LEGACY` | `LEGACY` | `OK` | `RE-AUDIT REQUIRED` |
| A | Search tools | `LEGACY` | `LEGACY` | `OK` | `RE-AUDIT REQUIRED` |
| A | Tool registry | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| A | Tool policies | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| A | Policy dry run | `LEGACY` | `LEGACY` | `OK` | `RE-AUDIT REQUIRED` |
| B | Approvals | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Alert rules | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Data capture | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Security | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Tags | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| D | Audit log | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| D | Governance pack | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |

### 05 — FinOps

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Budgets | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| A | Budget detail | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| A | Budget overrides | `PARTIAL` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| B | Billing periods | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| B | Billing period detail | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| C | Chargeback | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| D | Ledger | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |

### 06 — Build & Improve

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Playground | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| A | Prompts list | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| A | Prompt detail and versions | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |
| B | Agents list | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Agent detail | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Agent memory | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Workflows list | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Workflow detail | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Workflow run detail | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Vector stores list | `OK` | `PARTIAL` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| B | Vector store detail | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Datasets | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Evaluation studio | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Experiments | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Replay lab | `PARTIAL` | `PARTIAL` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Replay experiment detail | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| C | Runbooks | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| D | Optimization opportunities | `PARTIAL` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| D | Optimization simulator | `OK` | `OK` | `PARTIAL` | `RE-AUDIT REQUIRED` |
| D | Model scorecards | `OK` | `OK` | `OK` | `RE-AUDIT REQUIRED` |

### 07 — Platform & Utility

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | All organizations | `OK` | `OK` | `NO` | `RE-AUDIT REQUIRED` |
| B | Platform settings | `PARTIAL` | `PARTIAL` | `NO` | `RE-AUDIT REQUIRED` |
| C | Plugins | `PARTIAL` | `LEGACY` | `OK` | `RE-AUDIT REQUIRED` |

### 08 — Planned Architecture

| Bundle | Minor Feature | Backend | UI | Complete | Fix Status |
|--------|---------------|---------|-----|----------|------------|
| A | Gateway service split | `PARTIAL` | `MISSING` | `NO` | `RE-AUDIT REQUIRED` |
| A | Gateway module review | `PARTIAL` | `N/A` | `NO` | `RE-AUDIT REQUIRED` |
| A | Router collapse | `PARTIAL` | `N/A` | `NO` | `RE-AUDIT REQUIRED` |
| A | Legacy deprecation | `PARTIAL` | `PARTIAL` | `NO` | `RE-AUDIT REQUIRED` |
| B | Scope-aware enforcement | `PARTIAL` | `N/A` | `NO` | `RE-AUDIT REQUIRED` |
| C | Pipeline studio | `MISSING` | `MISSING` | `NO` | `RE-AUDIT REQUIRED` |
| C | API explorer | `PARTIAL` | `PARTIAL` | `NO` | `RE-AUDIT REQUIRED` |
| C | Help hub | `MISSING` | `MISSING` | `NO` | `RE-AUDIT REQUIRED` |
| D | Theme refresh | `PARTIAL` | `PARTIAL` | `NO` | `RE-AUDIT REQUIRED` |
| D | Docs IA | `PARTIAL` | `N/A` | `NO` | `RE-AUDIT REQUIRED` |
| D | Repo naming cleanup | `PARTIAL` | `N/A` | `NO` | `RE-AUDIT REQUIRED` |

---

## 3. GAP Summary — Highest Priority

Bundles ranked by total cross-feature GAP count (most urgent first):

| Rank | Bundle | Total GAPs | Worst Relationship | Root Cause |
|------|--------|------------|--------------------|-----------| 
| 1 | **05-A** Budget Control | **49** | 05-A x 06-Build (12G) | Budget detail page is the single biggest cohesion blocker across the entire product |
| 2 | **01-B** Identity & Scope | **13** | 01-B x 05-FinOps (9G) | Access groups and API keys not yet first-class budget/billing scopes |
| 3 | **03-B** Investigation | **6** | 03-B x 01-Org (4G) | Access-group scope missing across investigation surfaces |
| 4 | **05-B** Billing & Recon | **2** | 05-B x 01-Org (2G) | Billing periods missing access-group/API-key scope |
| 5 | **04-B** Exception Workflows | **2** | 04-B x 05-FinOps (2G) | Approvals disconnected from budget overrides |
| 6 | **02-C** Performance Controls | **2** | 02-C x 05-FinOps (2G) | Cache/rate-limit detail missing FinOps bridges |
| 7 | **05-C** Attribution | **1** | 05-C x 05-Self (1G) | Chargeback internal cohesion gap with budget detail |
| 8 | **05-D** Compliance | **1** | 05-D x 05-Self (1G) | Ledger internal cohesion gap with budget detail |
| 9 | **01-A** Org Foundation | **1** | 01-A x 05-FinOps (1G) | Org profile missing budget detail bridge |
| 10 | **01-D** Capability Catalog | **1** | 01-D x 05-FinOps (1G) | AI hub missing budget detail bridge |
| 11 | **02-A** Provider & Routing | **1** | 02-A x 05-FinOps (1G) | Provider profiles missing budget override bridge |
| 12 | **03-A** Overview & Entry | **1** | 03-A x 05-FinOps (1G) | Analytics overview missing budget detail bridge |
| 13 | **03-C** Economics & Intel | **1** | 03-C x 05-FinOps (1G) | Model usage missing budget detail bridge |
| 14 | **04-A** Tool Governance | **1** | 04-A x 05-FinOps (1G) | Tool registry missing budget detail bridge |
| 15 | **04-C** Data & Security | **1** | 04-C x 05-FinOps (1G) | Tags missing budget detail bridge |
| 16 | **07-A** Platform Lifecycle | **0** | — | — |

**Pattern**: Budget detail (05-A) is the root cause behind **most GAPs across the entire product**. Fixing budget detail unlocks cohesion improvements in 6 of the other 7 major features.

---

## 4. Active Work Units

Work units live inside each major feature folder at `{folder}/WORK-UNITS/WU-NNN-<slug>.md`. This section indexes all active WUs across the product.

| ID | Owner Folder | Target | Paired Features | Status | Bundle |
|----|--------------|--------|-----------------|--------|--------|
| WU-001 | 01-ORG-AND-ACCESS | Access groups × FinOps scoping | 05-FINOPS | NOT_STARTED | 01-B |
| WU-002 | 01-ORG-AND-ACCESS | API keys × budget ownership | 05-FINOPS | NOT_STARTED | 01-B |
| WU-003 | 01-ORG-AND-ACCESS | Access groups × Observe investigation | 03-OBSERVE | NOT_STARTED | 01-B |
| WU-004 | 01-ORG-AND-ACCESS | Org profile × FinOps rollup | 05-FINOPS | NOT_STARTED | 01-A |
| WU-005 | 01-ORG-AND-ACCESS | Users × FinOps attribution | 05-FINOPS | NOT_STARTED | 01-B |
| WU-006 | 01-ORG-AND-ACCESS | Identity & scope × Safety & Governance | 04-SAFETY-AND-GOVERNANCE | NOT_STARTED | 01-B |
| WU-007 | 01-ORG-AND-ACCESS | Identity & scope × Build & Improve | 06-BUILD-AND-IMPROVE | NOT_STARTED | 01-B |
| WU-008 | 01-ORG-AND-ACCESS | Org profile × Observe & Gateway rollups | 03-OBSERVE, 02-GATEWAY | NOT_STARTED | 01-A |
| WU-009 | 01-ORG-AND-ACCESS | Onboarding setup completeness | 02/03/04/05 | NOT_STARTED | 01-C |
| WU-010 | 01-ORG-AND-ACCESS | AI hub × governance & org links | 04/05/07 | NOT_STARTED | 01-D |
| WU-011 | 01-ORG-AND-ACCESS | API keys × Observe dimension | 03-OBSERVE | NOT_STARTED | 01-B |
| WU-012 | 01-ORG-AND-ACCESS | Workspace × Observe/FinOps strengthen | 03/05 | NOT_STARTED | 01-B |
| WU-013 | 01-ORG-AND-ACCESS | Internal cohesion tightening | 07-PLATFORM | NOT_STARTED | 01-A/B/C/D |
| WU-001 | 02-GATEWAY-AND-ROUTING | Provider profiles × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 02-A |
| WU-002 | 02-GATEWAY-AND-ROUTING | Performance controls × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 02-C |
| WU-003 | 02-GATEWAY-AND-ROUTING | Model gateway × FinOps deepening | 05-FINOPS | NOT_STARTED | 02-A |
| WU-004 | 02-GATEWAY-AND-ROUTING | Provider profiles × Org & Access links | 01-ORG-AND-ACCESS | NOT_STARTED | 02-A |
| WU-005 | 02-GATEWAY-AND-ROUTING | Gateway & guardrails × Org scope | 01-ORG-AND-ACCESS | NOT_STARTED | 02-A/B |
| WU-006 | 02-GATEWAY-AND-ROUTING | Provider profiles × Observe visibility | 03-OBSERVE | NOT_STARTED | 02-A |
| WU-007 | 02-GATEWAY-AND-ROUTING | Gateway & perf controls × Observe strengthen | 03-OBSERVE | NOT_STARTED | 02-A/C |
| WU-008 | 02-GATEWAY-AND-ROUTING | Guardrails × Observe traceability | 03-OBSERVE | NOT_STARTED | 02-B |
| WU-009 | 02-GATEWAY-AND-ROUTING | Gateway × Safety & Governance deepening | 04-SAFETY-AND-GOVERNANCE | NOT_STARTED | 02-A/B/C |
| WU-010 | 02-GATEWAY-AND-ROUTING | Gateway × Build & Improve integration | 06-BUILD-AND-IMPROVE | NOT_STARTED | 02-A/B/C |
| WU-011 | 02-GATEWAY-AND-ROUTING | Performance controls × Org & scope | 01/07 | NOT_STARTED | 02-C |
| WU-012 | 02-GATEWAY-AND-ROUTING | Gateway internal & platform cohesion | 02/06/07 | NOT_STARTED | 02-A/B/C/D |
| WU-001 | 03-OBSERVE | Investigation × access-group scope | 01-ORG-AND-ACCESS | NOT_STARTED | 03-B |
| WU-002 | 03-OBSERVE | Investigation × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 03-B |
| WU-003 | 03-OBSERVE | Overview & economics × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 03-A/C |
| WU-004 | 03-OBSERVE | Investigation × Org identity & scope | 01-ORG-AND-ACCESS | NOT_STARTED | 03-B |
| WU-005 | 03-OBSERVE | Investigation × Safety & Governance traceability | 04-SAFETY-AND-GOVERNANCE | NOT_STARTED | 03-B |
| WU-006 | 03-OBSERVE | Investigation × Gateway runtime context | 02-GATEWAY-AND-ROUTING | NOT_STARTED | 03-B |
| WU-007 | 03-OBSERVE | Economics & outcomes × FinOps strengthening | 05-FINOPS | NOT_STARTED | 03-C/D |
| WU-008 | 03-OBSERVE | Overview × cross-feature posture cards | 01/02/04 | NOT_STARTED | 03-A |
| WU-009 | 03-OBSERVE | Economics & model intel × Gateway links | 01/02/03/04 | NOT_STARTED | 03-C |
| WU-010 | 03-OBSERVE | Monitoring & ops × governance integration | 01/02/03/04 | NOT_STARTED | 03-D |
| WU-011 | 03-OBSERVE | User analytics & overview × Org links | 01/03 | NOT_STARTED | 03-A/C |
| WU-001 | 04-SAFETY-AND-GOVERNANCE | Tool registry × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 04-A |
| WU-002 | 04-SAFETY-AND-GOVERNANCE | Approvals & alert rules × FinOps budget bridge | 05-FINOPS | NOT_STARTED | 04-B |
| WU-003 | 04-SAFETY-AND-GOVERNANCE | Tags × FinOps budget detail bridge | 05-FINOPS | NOT_STARTED | 04-C |
| WU-004 | 04-SAFETY-AND-GOVERNANCE | Tool governance × Org & Access scope | 01-ORG-AND-ACCESS | NOT_STARTED | 04-A |
| WU-005 | 04-SAFETY-AND-GOVERNANCE | Tool governance × Gateway & Observe traceability | 02/03 | NOT_STARTED | 04-A |
| WU-006 | 04-SAFETY-AND-GOVERNANCE | Exception workflows × Org & Access scope | 01-ORG-AND-ACCESS | NOT_STARTED | 04-B |
| WU-007 | 04-SAFETY-AND-GOVERNANCE | Exception workflows × Gateway & Observe | 02/03 | NOT_STARTED | 04-B |
| WU-008 | 04-SAFETY-AND-GOVERNANCE | Data protection × Org & Access scope | 01-ORG-AND-ACCESS | NOT_STARTED | 04-C |
| WU-009 | 04-SAFETY-AND-GOVERNANCE | Data protection × Gateway & Observe | 02/03 | NOT_STARTED | 04-C |
| WU-010 | 04-SAFETY-AND-GOVERNANCE | Evidence & audit × cross-feature linkage | 01/02/03/05 | NOT_STARTED | 04-D |
| WU-011 | 04-SAFETY-AND-GOVERNANCE | Internal cohesion tightening | 04-SELF | NOT_STARTED | 04-A/B/C/D |
| WU-001 | 05-FINOPS | Budget control × Org & Access scope | 01-ORG-AND-ACCESS | NOT_STARTED | 05-A |
| WU-002 | 05-FINOPS | Budget control × Gateway & Routing | 02-GATEWAY-AND-ROUTING | NOT_STARTED | 05-A |
| WU-003 | 05-FINOPS | Budget detail × Observe surfaces bridge | 03-OBSERVE | NOT_STARTED | 05-A |
| WU-004 | 05-FINOPS | Budget control × Safety & Governance | 04-SAFETY-AND-GOVERNANCE | NOT_STARTED | 05-A |
| WU-005 | 05-FINOPS | Budget detail × Build & Improve surfaces | 06-BUILD-AND-IMPROVE | NOT_STARTED | 05-A |
| WU-006 | 05-FINOPS | Budget control × Platform scope | 07-PLATFORM-AND-UTILITY | NOT_STARTED | 05-A |
| WU-007 | 05-FINOPS | Billing × Org access-group scope | 01-ORG-AND-ACCESS | NOT_STARTED | 05-B |
| WU-008 | 05-FINOPS | Internal FinOps cohesion | 05-SELF | NOT_STARTED | 05-A/C/D |
| WU-009 | 05-FINOPS | Budget control × Observe PARTIAL strengthen | 03-OBSERVE | NOT_STARTED | 05-A |
| WU-010 | 05-FINOPS | Budget control × Build PARTIAL strengthen | 06-BUILD-AND-IMPROVE | NOT_STARTED | 05-A |
| WU-011 | 05-FINOPS | Billing × cross-feature strengthen | 02/04/07 | NOT_STARTED | 05-B |
| WU-012 | 05-FINOPS | Chargeback × cross-feature strengthen | 01/02/04/07 | NOT_STARTED | 05-C |
| WU-013 | 05-FINOPS | Ledger × cross-feature strengthen | 01/03/04/07 | NOT_STARTED | 05-D |
| WU-001 | 06-BUILD-AND-IMPROVE | Interactive Build × Org & Gateway scope | 01/02 | NOT_STARTED | 06-A |
| WU-002 | 06-BUILD-AND-IMPROVE | Interactive Build × Observe bridge | 03-OBSERVE | NOT_STARTED | 06-A |
| WU-003 | 06-BUILD-AND-IMPROVE | Managed assets × cross-feature strengthen | 01/02/03/05 | NOT_STARTED | 06-B |
| WU-004 | 06-BUILD-AND-IMPROVE | Evaluation & Replay × Org & Gateway scope | 01/02 | NOT_STARTED | 06-C |
| WU-005 | 06-BUILD-AND-IMPROVE | Evaluation & Replay × Observe bridge | 03-OBSERVE | NOT_STARTED | 06-C |
| WU-006 | 06-BUILD-AND-IMPROVE | Optimization × Org & Gateway scope | 01/02 | NOT_STARTED | 06-D |
| WU-007 | 06-BUILD-AND-IMPROVE | Optimization × Observe bridge | 03-OBSERVE | NOT_STARTED | 06-D |
| WU-008 | 06-BUILD-AND-IMPROVE | Build × FinOps strengthen | 05-FINOPS | NOT_STARTED | 06-A/C/D |
| WU-009 | 06-BUILD-AND-IMPROVE | Internal Build cohesion tightening | 06-SELF | NOT_STARTED | 06-A/B/C/D |
| WU-001 | 07-PLATFORM-AND-UTILITY | All organizations delivery & posture completion | 01/02/04/05 | NOT_STARTED | 07-A |
| WU-002 | 07-PLATFORM-AND-UTILITY | Platform settings convergence & delivery completeness | 01/02/03/04/05 | NOT_STARTED | 07-B |
| WU-003 | 07-PLATFORM-AND-UTILITY | Plugins collapse & discovery ownership cleanup | 01/06 | NOT_STARTED | 07-C |
| WU-004 | 07-PLATFORM-AND-UTILITY | Platform admin cohesion & posture rollups | 01/02/03/04/06 | NOT_STARTED | 07-A/B/C |
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
