# RunLedger Product TODO And Implementation Plan

## Phase Index And Status Tracker

Use this as the top-level checklist. Update the status checkbox when a phase is complete.

| Done | Phase | Effort | Impact | Plan |
|---|---|---:|---:|---|
| [x] | Phase 0 - Product And Data Alignment | M | H | Dashboard scopes, questions, dimensions, metrics, optimization categories, chart mapping, and API contract guidance are documented. |
| [x] | Phase 1 - Publishable RunLedger Skills | L | H | MVP skill packages, shared instructions, smoke-test helpers, and repeatable validation are complete; live MCP UI checks remain a manual follow-up. |
| [x] | Phase 1A - Integration Options And MCP Connectivity | M | H | MCP tools/resources/prompts, stdio bridge, config generation, docs, and validator are complete; integration kits/scoped keys move to follow-up phases. |
| [x] | Phase 2 - Dashboard Information Architecture | M | H | Platform, Org, and Workspace dashboard IA, navigation, scope context, and shared time controls are complete; deep dimension filters moved to Phase 3 analytics data. |
| [x] | Phase 3 - Data Model And Analytics API | XL | H | Intent classification, optimization attribution, scoped summaries, savings analytics, trends, request explorer API, and demo seeders are complete. |
| [ ] | Phase 3A - Supporting Infrastructure And Observability Backbone | XL | H | Plan S3/MinIO, SMTP, Firebase emulator, OSS monitoring, enhanced OTEL, and customer bring-up infra. |
| [x] | Phase 3B - Scheduled Operations And Professional Rebrand | L | H | Scheduled email controls, backend kill switches, backup UI surface, and enterprise rebrand pass completed. |
| [~] | Phase 3C - Kafka Streaming And Event Bus | L | H | Optional Kafka export MVP is built; retry worker, Redpanda demo profile, and full event producer coverage remain. |
| [x] | Phase 4 - Executive Dashboard | M | H | Platform executive dashboard now shows spend, savings, ROI, requests, latency, cache, trends, waterfall, attribution, and top drivers. |
| [x] | Phase 5 - AI Request Flow Dashboard | L | H | Sankey, alternate views, metrics, hover, Request Explorer drilldown, and backend workspace/org/platform flow API are complete. |
| [x] | Phase 6 - Model Usage And Routing Dashboard | M | H | Model Usage page now shows model trends, routing distribution, model table, and routing decision detail. |
| [x] | Phase 7 - Cost, Savings, And ROI Dashboard | M | H | Cost & Savings page now has scoped cost breakdown, ROI, realized savings attribution, heatmap, next target, and org/platform budget rollups. |
| [x] | Phase 8 - Engineering Dashboard And Request Explorer | L | H | Engineering dashboard with KPI metrics, lifecycle pipeline, agent dependency graph, quality funnel, cost breakdowns, and Request Explorer are complete. |
| [x] | Phase 9 - Optimization Opportunities | M | H | Optimization Opportunities page is live with rule-backed recommendations, experiment launch links, projected savings, and realized savings from provider-call attribution. |
| [x] | Phase 10 - Visual Design And Interaction | M | M | Polish the experience with better interactions, responsive layouts, empty states, and professional UX. |
| [ ] | Phase 11 - Demo Data, Labs, And Scenarios | M | H | Seed realistic enterprise demos showing savings, routing, alerts, MCP filtering, and optimization impact. |
| [x] | Phase 12 - Implementation Order | S | M | Roadmap has been converted into a practical PR sequence with validation checkpoints. |
| [~] | Phase 13 - Product Differentiators And Advanced Roadmap | L | H | Integration Health Center and Optimization Simulator shipped; replay labs, dry-run policy, chargeback, and demo mode remain. |
| [ ] | Phase 14 - Guardrails, Content Safety And Policy Engine | XL | H | Custom guardrails with Python logic, pre-built content filters, partner guardrail integrations, guardrails monitor, and policy dry-run. |
| [ ] | Phase 15 - Traditional AI/ML Intelligence Layer | XL | H | Anomaly detection, cost/token forecasting, top-K analysis, usage prediction, pattern recognition, and intelligent alerting. |
| [ ] | Phase 16 - Agentic Operations And Developer Experience | L | H | Agent lifecycle management, workflow runs, agent memory, API playground, vector store management, and tag management. |

Effort key: `S` = small, `M` = medium, `L` = large, `XL` = very large.

Impact key: `M` = medium, `H` = high.

Status key: `[x]` = complete, `[~]` = partially complete, `[ ]` = not started, `[>]` = moved to a follow-up phase.

## Priority Index - Effort Vs Impact

Use this to find low-hanging fruit and sequence work.

### Do First - Low Effort, High Impact

| Done | Item | Effort | Impact | Why It Is Worth Doing Early |
|---|---|---:|---:|---|
| [x] | Phase 1 - Publishable RunLedger Skills | L | H | Skill packages, README/UI surfacing, instruction generation, and structural validation are complete; live desktop-app verification remains a manual follow-up. |
| [x] | Phase 3B - Professional Theme Rebrand | L | H | Completed first enterprise rebrand pass across logo, README, login, sidebar, Settings, top shell tokens, and major active states. |
| [x] | Phase 5 - AI Request Flow Dashboard | L | H | Sankey, alternate views, metrics, hover, Request Explorer drilldown, and backend workspace/org/platform flow API are complete. |
| [x] | Phase 8 - Request Explorer MVP | L | H | Dedicated Request Explorer now debugs prompt, route, model, tools, cost, latency, cache, and outcome. |
| [x] | Phase 12 - Implementation Order | S | M | Implementation order exists; individual PR rows remain tracked below. |

### Do Next - Medium Effort, High Impact

| Done | Item | Effort | Impact | Why It Matters |
|---|---|---:|---:|---|
| [x] | Phase 0 - Product And Data Alignment | M | H | Completed in `docs/product-data-alignment.md`; future charts and APIs now have a source-of-truth contract. |
| [x] | Phase 1A - MCP Connectivity | M | H | MCP contract, stdio bridge, config generation, docs, and validator are complete; live app UI checks remain manual after rebuild/restart. |
| [x] | Phase 2 - Dashboard Information Architecture | M | H | Platform, Org, and Workspace navigation/scopes are complete; deep filters remain tied to Phase 3. |
| [x] | Phase 4 - Executive Dashboard | M | H | Platform executive dashboard is live; Phase 7 now provides finance-grade savings attribution for Cost & Savings. |
| [x] | Phase 6 - Model Usage And Routing Dashboard | M | H | Makes routing and model spend understandable. |
| [x] | Phase 7 - Cost, Savings, And ROI Dashboard | M | H | Finance dashboard is complete with realized savings attribution and scoped budget rollups. |
| [x] | Phase 9 - Optimization Opportunities | M | H | Rule-backed advisory page is live with projected and measured savings. |
| [ ] | Phase 11 - Demo Data, Labs, And Scenarios | M | H | Lets the product tell a complete story before real customer data exists. |
| [~] | Phase 3C - Kafka Streaming MVP | L | H | Optional Kafka export CRUD/test/delivery log is live; full demo and retry worker remain. |

### Bigger Bets - High Effort, High Impact

| Done | Item | Effort | Impact | Why It Is A Bigger Bet |
|---|---|---:|---:|---|
| [x] | Phase 3 - Data Model And Analytics API | XL | H | Required for durable analytics but touches backend, migrations, APIs, and rollups. |
| [ ] | Phase 3A - Supporting Infrastructure Backbone | XL | H | Important for production readiness but spans S3, SMTP, OTEL, logs, metrics, secrets, and deployment profiles. |
| [~] | Phase 13 - Product Differentiators | L | H | Integration Health Center and Optimization Simulator shipped; remaining items layered after foundation. |
| [ ] | Phase 14 - Guardrails And Content Safety | XL | H | Major competitive gap vs LiteLLM; custom guardrails, content filters, and partner integrations are table stakes. |
| [ ] | Phase 15 - AI/ML Intelligence Layer | XL | H | Transforms RunLedger from reporting to prediction; anomaly detection, forecasting, and pattern recognition. |
| [ ] | Phase 16 - Agentic Operations And DX | L | H | Agent lifecycle, workflow runs, memory, and playground close the gap with LiteLLM Agentic features. |

### Polish After Foundation

| Done | Item | Effort | Impact | Why It Comes Later |
|---|---|---:|---:|---|
| [x] | Phase 10 - Visual Design And Interaction | M | M | Valuable, but deeper chart polish should follow the core dashboard and data contracts. |

## Suggested Low-Hanging Fruit Sequence

1. [x] Finish the professional theme direction and update visible surfaces: login, sidebar, top bar, buttons, active states, major legacy dark panels, fonts, and logo assets.
2. [x] Add an Integration Health Center MVP using existing API Keys, MCP, OTLP, Slack, Gateway, Email/Backup flags, and Kafka export status.
3. [~] Build a seeded Sankey demo from existing run/provider/session data.
4. [x] Add email report schedule requirements to Settings Email and backend scheduler plan.
5. [x] Add backup schedule requirements to Settings or Integrations with MinIO/S3 test-connection plan.
6. [x] Surface published skills in README and Integrations: `runledger-connect-claude`, `runledger-connect-codex`, `runledger-connect-cursor`, and `runledger-connect-devin`.
7. [x] Add request explorer MVP with prompt, model, cost, latency, route, tools, cache status, and outcome.
8. [x] Add optimization recommendation cards using simple rules before ML-based recommendations.
9. [~] Add Kafka export MVP for `run.completed`, `alert.fired`, and `budget.breached` events. Run lifecycle export MVP is built; alert and budget producers remain.
10. [ ] Add built-in content filters (Guardrail Garden) — PII, prompt injection, bias, toxicity detection using keyword/regex (no ML dependency).
11. [ ] Add cost anomaly detection with Z-score + EWMA on rolling windows (Phase 15 quick win).
12. [ ] Add cost forecasting (Holt-Winters) with budget-breach probability on workspace dashboard.
13. [ ] Add Top-K analysis API with period-over-period change detection.
14. [ ] Add API playground for interactive model testing through the gateway.
15. [ ] Add custom guardrail editor with sandboxed Python logic and test playground.

---

## Product Vision

Build RunLedger as the **AI Operations Intelligence platform** for enterprises.

RunLedger should not feel like a billing dashboard. It should feel like the control room for every AI request, agent, model, tool, optimization, dollar spent, and dollar saved.

One-sentence vision:

> Build the Datadog for Enterprise AI: a platform that lets organizations see every AI request, understand every dollar spent, explain every routing decision, and continuously optimize cost, performance, and quality through actionable insights.

## Main Outcomes

- [x] Make RunLedger easy to connect from Claude Desktop, OpenAI Codex, Devin, and Cursor through publishable skills.
- [x] Add default markdown instruction files that those tools can source so every spawned agent knows how to send telemetry to RunLedger.
- [x] Build Platform, Org, and Workspace dashboards that show AI usage, cost, routing, business impact, and savings.
- [~] Make the dashboards feel like an AI Operations Center, not a token-counting invoice page.
- [x] Give executives a 30-second summary and engineers a full request-level debugging path.
- [ ] Add guardrails and content safety engine competitive with LiteLLM's Guardrail Garden and custom guardrails.
- [ ] Add traditional AI/ML intelligence: anomaly detection, cost forecasting, top-K analysis, and pattern recognition.
- [ ] Add agentic operations: agent registry, workflow runs, memory management, and API playground.

---

## Phase 0 - Product And Data Alignment

### Goal

Define the product language, data model, and dashboard scopes before building UI.

### TODO

- [x] Define dashboard scopes:
  - Platform-level Global Dashboard for Platform Admins.
  - Org-level Dashboard for Org Admins.
  - Workspace-level Dashboard for Workspace Admins and read-only Members.
- [x] Define the core dashboard questions:
  - Where is the money going?
  - Why is it being spent?
  - Which requests, agents, models, tools, and teams drive cost?
  - What did RunLedger optimize?
  - What should we optimize next?
- [x] Define standard dimensions:
  - Organization
  - Workspace
  - Team
  - Application
  - User
  - Agent
  - Skill
  - Intent
  - Model
  - Provider
  - Tool
  - Route
  - Outcome
  - Time range
  - Cost center
- [x] Define standard metrics:
  - Requests
  - Input tokens
  - Output tokens
  - Total tokens
  - Cost
  - Savings
  - Latency
  - Error rate
  - Retry rate
  - Cache hit rate
  - Rejected requests
  - Token reduction
  - Cost reduction
  - Quality score
  - Outcome rate
- [x] Define standard optimization categories:
  - Prompt compression
  - Cache hits
  - Smart model routing
  - Local model routing
  - Duplicate request detection
  - Tool optimization
  - Reasoning avoidance
  - Provider fallback
  - Batch/retry reduction

### Acceptance Criteria

- [x] Dashboard API contracts and filter dimensions are documented.
- [x] Every planned chart maps to a clear product question.
- [x] Scope rules are clear for Platform Admin, Org Admin, Workspace Admin, and Member.

---

## Phase 1 - Publishable RunLedger Skills

### Goal

Create publishable skills that make Claude Desktop, OpenAI Codex, Devin, and Cursor easy to connect to RunLedger without requiring users to study the product first.

Each skill should act like an onboarding adapter:

- Install or invoke the skill.
- Provide RunLedger URL and API key.
- Skill creates or updates the right config files.
- Skill adds default markdown instructions.
- Every agent spawned by that tool knows to emit RunLedger telemetry.

### Shared Skill Requirements

- [x] Create a common skill design pattern:
  - `SKILL.md` with short trigger-focused instructions.
  - `references/` for longer setup notes.
  - `scripts/` for deterministic setup and validation.
  - `agents/openai.yaml` metadata where applicable.
- [x] Create a shared RunLedger telemetry contract used by all skills:
  - `runledger_base_url`
  - `runledger_api_key`
  - `runledger_workspace`
  - `agent_client`
  - `agent_session_id`
  - `task_id`
  - `repo`
  - `branch`
  - `model`
  - `tool`
  - `intent`
  - `outcome`
  - `cost`
  - `latency`
- [ ] Provide a shared SDK helper:
  - `record_run_start`
  - `record_span`
  - `record_tool_call`
  - `record_model_call`
  - `record_outcome`
  - `check_budget`
  - `check_policy`
- [ ] Provide a shared MCP tool list:
  - `runledger.budget_check`
  - `runledger.policy_check`
  - `runledger.record_outcome`
  - `runledger.query_runs`
  - `runledger.query_costs`
  - `runledger.recommend_route`
  - `runledger.filter_mcp_tool`
- [x] Provide a setup validation command for each skill.
- [x] Provide a smoke test that sends one event into RunLedger.
- [x] Provide a repeatable validation script:
  - `python skills/shared/scripts/validate_skills.py`
  - `python skills/shared/scripts/validate_skills.py --smoke`
- [x] Ensure secrets are never written into committed markdown examples.

### Skill 1 - Claude Desktop / Claude Code

- [x] Create publishable skill: `runledger-connect-claude`.
- [x] Support Claude Desktop MCP setup through documented config guidance.
- [x] Support Claude Code MCP setup through documented config guidance.
- [x] Generate or update a default `CLAUDE.md` in the target repo.
- [x] Add instructions in `CLAUDE.md` telling Claude-spawned agents to:
  - Check RunLedger budget before long tasks.
  - Record task start and end.
  - Record tool calls and outcomes.
  - Use RunLedger MCP tools for policy and optimization guidance.
- [x] Add optional local stdio MCP bridge if Claude Desktop cannot connect directly to HTTP MCP.
- [x] Add validation:
  - Instruction file generation works.
  - Smoke outcome event appears in RunLedger.
  - MCP server visibility remains a manual app-level follow-up after Claude reload.

### Skill 2 - OpenAI Codex

- [x] Create publishable skill: `runledger-connect-codex`.
- [x] Generate or update root `AGENTS.md`.
- [x] Generate disabled `.codex/runledger-hooks.template.json` for lifecycle capture.
- [>] Add live Codex hook coverage after local hook trust/setup is confirmed:
  - `SessionStart`
  - `SubagentStart`
  - `PreToolUse`
  - `PermissionRequest`
  - `PostToolUse`
  - `Stop`
  - `SessionEnd`
- [x] Add instructions in `AGENTS.md` telling Codex and subagents to:
  - Treat RunLedger as the telemetry and FinOps control plane.
  - Log spawned subagents.
  - Use budget and policy checks before risky or expensive work.
  - Record final outcome and verification status.
- [x] Add validation:
  - Instruction file and disabled hook template are generated.
  - Smoke outcome event appears in RunLedger.
  - Hook trust/setup status remains a manual Codex app-level follow-up.

### Skill 3 - Devin

- [x] Create publishable skill: `runledger-connect-devin`.
- [>] Support live Devin API/service-user configuration once external Devin credentials are available.
- [x] Generate a Devin-facing markdown instruction file after verifying the supported default path.
- [x] Candidate file names reviewed; Phase 1 generates the portable repo-level file:
  - `.devin/runledger.md`
  - `DEVIN.md`
  - `RUNLEDGER_AGENT.md`
- [x] Add a RunLedger Devin bridge pattern:
  - Check budget before creating a Devin session.
  - Create RunLedger run.
  - Create Devin session.
  - Store Devin session ID in RunLedger metadata.
  - Poll or receive webhook completion.
  - Record outcome, PR, branch, elapsed time, and estimated or imported usage.
- [x] Add validation:
  - Devin-facing instruction file is generated.
  - Smoke outcome event appears in RunLedger.
  - Live Devin service-user auth remains a manual follow-up because it needs external Devin credentials.

### Skill 4 - Cursor

- [x] Create publishable skill: `runledger-connect-cursor`.
- [x] Support Cursor MCP setup through documented config guidance.
- [x] Generate or update Cursor rules/instruction files after verifying current supported paths.
- [x] Candidate file names reviewed; Phase 1 generates the supported Cursor rules file:
  - `.cursor/rules/runledger.mdc`
  - `.cursor/rules/runledger.md`
  - `RUNLEDGER_AGENT.md`
- [x] Add Cursor instructions telling agents to:
  - Use RunLedger MCP for budget checks.
  - Record task outcomes.
  - Use RunLedger-recommended model routes where configurable.
  - Log tool usage and expensive actions.
- [x] Add optional Gateway setup guidance for Cursor when custom OpenAI-compatible endpoints are available.
- [x] Add validation:
  - Cursor rule file is generated.
  - Smoke outcome event appears in RunLedger.
  - Cursor MCP visibility remains a manual app-level follow-up after Cursor reload.

### Acceptance Criteria

- [x] A user can install or invoke each skill with minimal instructions.
- [x] Each skill can connect a supported agent tool to RunLedger in under 10 minutes for repo instructions and smoke telemetry.
- [x] Each skill creates or updates the default markdown/config files the tool reads.
- [x] Every spawned agent gets RunLedger instructions by default.
- [x] Skills support out-of-band telemetry everywhere and inline control where the client can route through RunLedger Gateway; native Claude/Codex hosted calls remain non-interceptable without wrappers or configurable endpoints.

---

## Phase 1A - Integration Options And MCP Connectivity

**Status:** Closed for MVP. The source includes the canonical RunLedger MCP server, stdio bridge,
generated config path, docs, and validator. Rebuild/restart the API image before running live
`http://localhost:8201/mcp` validation because the source fix updates the mounted MCP lifespan/path.

### Goal

Make RunLedger extremely easy to connect to any AI app, IDE, agent framework, workflow tool, or model gateway.

RunLedger should support two integration personalities:

- **Inline control plane**: RunLedger sits in the request path and can route, block, optimize, cache, redact, meter, and enforce budgets.
- **Out-of-band intelligence layer**: RunLedger receives traces, metrics, logs, events, and outcomes from tools that cannot be routed through the Gateway.

### MCP Product Direction

Treat MCP as the easiest way for agents to talk to RunLedger.

RunLedger should expose an MCP server that lets external agents ask:

- Can I afford to run this task?
- Which model should I use?
- Is this tool call allowed?
- What did similar tasks cost?
- What route has the best cost/quality tradeoff?
- What experiments are currently running?
- What policy applies to this workspace?
- What outcome should I record?

### MCP Tools To Build

- [x] `runledger.budget_check`
  - Input: org, workspace, task type, estimated tokens, estimated cost.
  - Output: allow, warn, deny, remaining budget, reason.
- [x] `runledger.policy_check`
  - Input: user, workspace, tool name, command, file path, model, request metadata.
  - Output: allow, require approval, deny, reason.
- [x] `runledger.recommend_route`
  - Input: intent, latency target, quality target, budget target, allowed providers.
  - Output: recommended model/route, fallback route, savings estimate.
- [x] `runledger.record_run_start`
  - Input: agent, repo, task, user, workspace, parent run.
  - Output: RunLedger run ID.
- [x] `runledger.record_span`
  - Input: run ID, span name, duration, status, metadata.
  - Output: accepted/rejected.
- [x] `runledger.record_tool_call`
  - Input: run ID, tool name, arguments summary, result summary, status, latency.
  - Output: accepted/rejected.
- [x] `runledger.record_model_call`
  - Input: run ID, model, provider, tokens, cost, cache status, route.
  - Output: accepted/rejected.
- [x] `runledger.record_outcome`
  - Input: run ID, outcome, quality score, business result, verification status.
  - Output: accepted/rejected.
- [x] `runledger.query_runs`
  - Input: filters for org, workspace, repo, model, agent, intent, time range.
  - Output: recent matching runs.
- [x] `runledger.query_costs`
  - Input: filters and grouping.
  - Output: cost, savings, tokens, trends.
- [x] `runledger.query_optimizations`
  - Input: workspace, model, intent, time range.
  - Output: optimization history and savings.
- [x] `runledger.filter_mcp_tool`
  - Input: downstream MCP server, downstream tool, arguments summary, user, workspace.
  - Output: allow, require approval, deny, reason.

### MCP Resources To Expose

- [x] `runledger://orgs/{org_id}/summary`
- [x] `runledger://workspaces/{workspace_id}/budget`
- [x] `runledger://workspaces/{workspace_id}/routes`
- [x] `runledger://workspaces/{workspace_id}/provider-profiles`
- [x] `runledger://workspaces/{workspace_id}/recent-runs`
- [x] `runledger://workspaces/{workspace_id}/optimization-recommendations`
- [x] `runledger://runs/{run_id}/trace`
- [x] `runledger://policies/{workspace_id}/tool-policy`
- [x] `runledger://docs/agent-instructions`

### MCP Prompts To Provide

- [x] `runledger_start_agent_task`
  - Helps an agent start a task with budget and telemetry enabled.
- [x] `runledger_choose_model_route`
  - Helps an agent choose the best model based on cost, quality, and latency.
- [x] `runledger_record_task_outcome`
  - Helps an agent close the loop with outcome and verification status.
- [x] `runledger_optimize_prompt`
  - Helps reduce prompt size and cost while preserving intent.
- [x] `runledger_debug_expensive_request`
  - Helps explain why a request was expensive.

### Connection Methods

- [x] Direct HTTP MCP:
  - Best for tools that support streamable HTTP MCP.
  - Example endpoint: `http://localhost:8201/mcp`.
- [x] Local stdio MCP bridge:
  - Best for tools that only support local command-based MCP servers.
  - Bridge injects RunLedger URL and API key from local env.
- [~] SSE MCP compatibility mode:
  - Useful for older clients that still expect SSE transport.
- [>] One-click install links:
  - Useful for Cursor/Windsurf-style onboarding where supported.
- [x] Generated config snippets:
  - Claude Desktop config.
  - Claude Code command.
  - Cursor MCP config.
  - Windsurf/Cascade MCP config.
  - Codex `config.toml` or hooks config.
- [x] Setup wizard MVP:
  - [x] User selects tool.
  - [x] User selects org/workspace.
  - [>] RunLedger creates scoped API key.
  - [x] RunLedger generates config.
  - [x] User copies or downloads config.
  - [x] Smoke test verifies connection through the command-line validator.

### Integration Surfaces To Support

- [x] Model gateway integration docs and demo path:
  - LiteLLM
  - Open WebUI
  - OpenHands
  - LangGraph
  - Dify
  - n8n
  - AnythingLLM
  - Ollama wrappers
- [x] IDE and desktop agent integration docs and demo path:
  - Claude Desktop
  - Claude Code
  - OpenAI Codex
  - Cursor
  - Windsurf
  - Devin
- [>] Agent framework-specific adapters:
  - LangGraph
  - CrewAI
  - AutoGen
  - Semantic Kernel
  - LlamaIndex agents
  - Haystack
  - LangChain
- [>] Workflow and automation adapters:
  - n8n
  - Dify
  - Zapier-style webhook adapters
  - GitHub Actions
  - CI wrappers
  - Jira/Linear ticket automation
- [x] Observability exporter docs and demo path:
  - OpenTelemetry
  - OpenInference
  - LangSmith-style traces if exportable
  - LiteLLM callbacks
  - Gateway logs

### RunLedger Integration Hub UI

- [x] Add a new `Integrations` hub page.
- [x] Show integration cards:
  - Gateway
  - OTLP
  - MCP
  - SDK
  - Webhooks
  - LiteLLM
  - Open WebUI
  - OpenHands
  - LangGraph
  - Claude
  - Codex
  - Cursor
  - Windsurf
  - Devin
- [x] Integration card MVP:
  - connection status
  - workspace API key used
  - last event received
  - health
  - setup guide
  - copy config
  - test connection
- [>] Add "Generate Integration Kit" action:
  - choose tool
  - choose workspace
  - generate API key
  - generate env file
  - generate markdown instructions
  - generate MCP config
  - generate wrapper script
- [>] Add "Download Agent Instructions" action:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `.cursor/rules/runledger.mdc`
  - `.windsurf/rules/runledger.md`
  - `RUNLEDGER_AGENT.md`

### SDK Improvements

- [>] Add SDK function for one-line setup:

```python
runledger = RunLedger.from_env(agent="cursor", workspace="Desktop Agents")
```

- [>] Add task wrapper:

```python
with runledger.task("Fix failing tests", intent="code_generation") as task:
    task.model_call(model="gpt-5", input_tokens=1000, output_tokens=300)
    task.tool_call("pytest", status="passed")
    task.outcome("completed", quality_score=0.92)
```

- [>] Add JavaScript/TypeScript equivalent.
- [>] Add CLI helper:

```powershell
runledger task start --agent cursor --workspace "Desktop Agents" --intent code_generation
runledger task outcome --run-id rlrun_... --result completed
```

- [>] Add webhook ingestion endpoint for tools that cannot use SDK or MCP.
- [>] Add signed event ingestion for customer environments.

### Security And Governance

- [>] Add scoped integration keys:
  - MCP-only
  - OTLP-only
  - Gateway-only
  - SDK ingest-only
  - read analytics-only
- [>] Add per-integration permissions:
  - can record runs
  - can query costs
  - can query prompts
  - can recommend routes
  - can enforce policy
  - can create API keys
- [>] Add integration audit log:
  - setup event
  - config generated
  - key created
  - key rotated
  - key revoked
  - MCP tool called
  - policy denied
- [>] Add secret redaction for prompts, tool arguments, logs, and traces.
- [>] Add per-workspace data capture policy for MCP/tool payloads.

### Ideas Worth Exploring

- [ ] MCP gateway/proxy:
  - RunLedger sits between agents and third-party MCP servers.
  - It logs tool calls, applies policies, blocks risky tools, and tracks tool cost.
- [ ] MCP marketplace inside RunLedger:
  - Customers register approved MCP servers.
  - Admins define which workspaces can use which servers/tools.
  - Agents discover approved tools from RunLedger.
- [ ] Agent instruction generator:
  - Generates `AGENTS.md`, `CLAUDE.md`, Cursor rules, Windsurf rules, and Devin instructions from one policy template.
- [x] Integration health score:
  - Shows if Gateway, MCP, SDK, OTLP, and email are connected correctly.
- [ ] FinOps policy simulator:
  - "If we route summarization to local Llama, projected savings are $8k/month."
- [ ] Shadow mode:
  - RunLedger observes routing decisions without enforcing them.
  - Useful before customers trust automatic control.
- [ ] Policy dry-run:
  - Show what would have been blocked without actually blocking.
- [ ] Agent budget envelopes:
  - Allocate budget per autonomous task before the agent starts.
- [ ] Tool cost accounting:
  - Assign cost to RAG, browser, code execution, database, and external APIs, not just model calls.
- [ ] Human approval integration:
  - Slack/Teams/email approval for expensive or risky agent actions.

### Acceptance Criteria

- [x] A customer can connect a supported agent using MCP in under 10 minutes.
- [x] RunLedger can operate as MCP server; MCP proxy remains a future enhancement.
- [x] Every MVP integration has a test connection path.
- [x] MVP integrations can emit at least one visible run/event in RunLedger.
- [>] Workspace admins can create scoped keys for their workspace integrations.
- [>] Org admins can manage integration policy across workspaces.
- [x] Platform admins can see integration health platform-wide.

### Official References To Use During Implementation

- Model Context Protocol documentation: https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-local-servers
- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- OpenInference: https://github.com/Arize-ai/openinference

---

## Phase 2 - Dashboard Information Architecture

### Goal

Create three dashboard levels with consistent navigation and role-based access.

### Dashboard Levels

- [x] Global Dashboard:
  - Scope: entire platform.
  - Role: Platform Admin only.
  - Purpose: platform-wide AI spend, org health, usage, savings, and risk.
- [x] Org Dashboard:
  - Scope: one organization.
  - Role: Org Admin and Platform Admin.
  - Purpose: org-level usage, cost, routing, savings, teams, workspaces, and outcomes.
- [x] Workspace Dashboard:
  - Scope: one workspace.
  - Role: Workspace Admin, Org Admin, Platform Admin, and read-only Members.
  - Purpose: application/team/agent-level diagnostics and request exploration.

### Navigation TODO

- [x] Keep `Global Dashboard` for Platform Admin.
- [x] Add `Org Dashboard` or rename current organization analytics accordingly.
- [x] Add workspace dashboard entry or make `Dashboard` clearly workspace-scoped.
- [x] Make dashboard scope visible in the header:
  - Platform
  - Org name
  - Workspace name
- [x] Add consistent Phase 2 dashboard controls:
  - Time range
  - Scope context
  - Dashboard-level dimension chips
  - Org/workspace entry points
  - Note: Team, Application, Agent, Model, Intent, and Outcome drilldown filters move to Phase 3 because they need normalized analytics APIs.

### Acceptance Criteria

- [x] Users always know which scope they are viewing.
- [x] Phase 2 filters and scope controls work consistently across all dashboard pages.
- [x] Role-gating matches RBAC.

### Phase 2 Notes

- [x] Added `/global-dashboard` for Platform Admin platform lifecycle visibility.
- [x] Re-scoped `/organization/dashboard` as the Org Dashboard with range-aware org analytics.
- [x] Re-scoped `/dashboard` as the Workspace Dashboard with range-aware workspace analytics.
- [x] Added dashboard scope chips and shared time range controls to all dashboard levels.
- [x] Dimension chips are visible now; full Team/Application/Agent/Intent/Outcome filtering is tracked under the Phase 3 analytics data model and APIs.

---

## Phase 3 - Data Model And Analytics API

### Goal

Create backend data needed for ultra-rich dashboards.

### TODO

- [x] Add or normalize fields for request lifecycle:
  - request ID
  - trace ID
  - run ID
  - user
  - org
  - workspace
  - application
  - team
  - agent
  - skill
  - intent
  - route
  - model
  - provider
  - tool
  - cache status
  - optimization applied
  - outcome
  - cost
  - savings
  - latency
- [x] Add intent classification storage:
  - reasoning
  - code generation
  - search
  - translation
  - email
  - meeting
  - research
  - summarization
  - vision
  - image
  - OCR
  - chat
  - workflow
  - planning
- [x] Add optimization attribution:
  - baseline cost
  - optimized cost
  - savings amount
  - savings percentage
  - optimization category
  - optimization decision reason
- [x] Add outcome tracking:
  - answered
  - cached
  - rejected
  - failed
  - escalated
  - accepted
  - thumbs up
  - thumbs down
  - PR opened
  - tests passed
  - tests failed
- [x] Add dashboard API endpoints:
  - `GET /analytics/scoped-summary` (scope=workspace|org|platform)
  - `GET /analytics/savings`
  - `GET /analytics/optimization-opportunities`
  - `GET /analytics/trends`
  - `GET /analytics/request-explorer`
  - (existing: /analytics/summary, /analytics/spend-over-time, /runs/flow, /analytics/spend-by-model, /analytics/economics/{run_id})
- [x] Add mock/demo data seeders for visual development.

### Acceptance Criteria

- [x] Frontend can render all planned charts from API responses.
- [x] API supports Platform, Org, and Workspace scopes.
- [x] Demo data shows savings, routing, cache, rejected requests, and outcomes.

---

## Phase 3A - Supporting Infrastructure And Observability Backbone

### Goal

Define the auxiliary infrastructure customers need to run RunLedger as a complete AI Operations suite, not just a web app.

This should support:

- Backup and restore.
- Local development parity.
- Email delivery and testing.
- Stack health monitoring.
- Enhanced OpenTelemetry ingestion.
- Long-term analytics storage.
- Customer-ready deployment patterns.

### Infrastructure Components To Add

| Component | Recommended Default | Purpose |
|---|---|---|
| S3-compatible object storage | MinIO locally, AWS S3/GCS/Azure Blob in production | Backups, exports, snapshots, trace archives, report artifacts |
| Local Firebase-style emulator | Firebase Local Emulator Suite where Firebase-compatible workflows are needed | Local auth/storage/function/pub-sub experiments without cloud dependency |
| Local SMTP server | Mailpit for local/dev | Welcome emails, password reset, invite emails, alert emails, test inbox |
| Production SMTP option | Google SMTP, SES, SendGrid, Postmark, or customer SMTP relay | Real email delivery and compliance with customer mail policy |
| Metrics store | Prometheus or VictoriaMetrics | Service metrics, collector metrics, app metrics, SLO dashboards |
| Logs store | Loki or OpenSearch | API/web/worker/collector logs and audit debugging |
| Trace store | Tempo, Jaeger, or ClickHouse-backed trace storage | Enhanced traces and request lifecycle visualization |
| Dashboarding | Grafana for infra, RunLedger native for AI-OI product dashboards | Avoid rebuilding generic infra observability too early |
| Alerting | Alertmanager plus RunLedger Alert Rules | Infra alerts and AI usage alerts |
| Queue/stream | Redis Streams, NATS, or Kafka-compatible Redpanda | Async ingestion, event fanout, retries, usage rollups |
| Search/analytics | ClickHouse or OpenSearch | High-cardinality request analytics and fast dashboard aggregations |
| Secrets | Docker secrets locally, Vault or cloud secret manager in production | API keys, SMTP credentials, object storage keys |

### S3 Backup And Restore

- [ ] Document current state clearly:
  - Helm already has an optional S3 backup CronJob.
  - `scripts/restore.sh` already restores supported stores from S3.
  - Docker Compose docs include a standalone backup script pattern.
  - The product UI does not yet manage backup schedules, test S3 connectivity, show backup history, or run restore drills.
- [ ] Add S3-compatible backup target configuration:
  - `RUNLEDGER_BACKUP_S3_ENDPOINT`
  - `RUNLEDGER_BACKUP_S3_BUCKET`
  - `RUNLEDGER_BACKUP_S3_REGION`
  - `RUNLEDGER_BACKUP_S3_ACCESS_KEY_ID`
  - `RUNLEDGER_BACKUP_S3_SECRET_ACCESS_KEY`
  - `RUNLEDGER_BACKUP_S3_FORCE_PATH_STYLE`
- [ ] Add MinIO to local auxiliary compose profile.
- [ ] Add backup buckets:
  - `runledger-db-backups`
  - `runledger-exports`
  - `runledger-trace-archives`
  - `runledger-report-artifacts`
- [ ] Add scheduled Postgres backups to S3.
- [ ] Add manual backup command.
- [ ] Add manual restore command.
- [ ] Add snapshot metadata table:
  - snapshot ID
  - org/workspace scope
  - backup type
  - object path
  - size
  - checksum
  - created by
  - created at
  - restore status
- [ ] Add UI for backup/restore under Platform Admin settings.
- [ ] Add restore dry-run validation.
- [ ] Add backup integrity check and alert.
- [ ] Add documentation for customer-provided S3-compatible storage.
- [ ] Add a Docker Compose `backup` profile:
  - optional MinIO service
  - local backup runner
  - scheduled backup example
  - restore drill example
- [ ] Add Platform Admin UI:
  - S3/MinIO connection status
  - test connection
  - last backup status
  - backup schedule
  - retention policy
  - manual backup
  - restore drill status

### Local Firebase / Emulator Support

- [ ] Decide whether Firebase emulation is required for RunLedger core or only for integration demos.
- [ ] If needed, add optional local emulator profile for:
  - Authentication
  - Firestore
  - Cloud Storage
  - Pub/Sub
  - Functions
- [ ] Add environment variables for emulator endpoints.
- [ ] Add docs showing how LocalAIAgentStack can use local Firebase-style services during demos.
- [ ] Do not make Firebase emulator mandatory for the default RunLedger stack unless a core feature depends on it.

### Email Infrastructure

- [ ] Add Mailpit to local auxiliary compose profile.
- [ ] Add email settings for:
  - SMTP host
  - SMTP port
  - username
  - password
  - TLS/STARTTLS
  - from address
  - reply-to address
  - provider type
- [ ] Add local defaults:
  - SMTP host: `mailpit`
  - SMTP port: `1025`
  - Mailpit UI: `http://localhost:8025`
- [ ] Add production examples:
  - Google SMTP
  - Amazon SES
  - SendGrid
  - Postmark
  - Customer SMTP relay
- [ ] Add email templates:
  - Welcome email
  - Organization invite
  - Workspace invite
  - Password reset
  - Email verification
  - Budget alert
  - Usage anomaly alert
  - Backup completed
  - Backup failed
  - Compliance export ready
- [ ] Add email delivery audit table:
  - recipient
  - template
  - status
  - provider message ID
  - error
  - sent at
  - org/workspace context
- [ ] Add resend button for failed invite/welcome emails.
- [ ] Add preview/test-send UI for Platform Admin email settings.

### Stack Monitoring Strategy

- [ ] Do not build a full in-house infrastructure monitoring product first.
- [ ] Use open-source monitoring for generic infrastructure:
  - Prometheus or VictoriaMetrics for metrics.
  - Grafana for infra dashboards.
  - Loki or OpenSearch for logs.
  - Tempo or Jaeger for traces.
  - Alertmanager for infra alert routing.
- [ ] Build RunLedger-native monitoring only for AI-specific intelligence:
  - AI spend.
  - Token usage.
  - Model routing.
  - Agent behavior.
  - Prompt lifecycle.
  - Optimization impact.
  - AI budget enforcement.
  - AI request outcomes.
- [ ] Add a local `observability` compose profile.
- [ ] Add dashboards for:
  - API health
  - Web health
  - Worker health
  - Database health
  - Redis health
  - OTEL collector health
  - Queue lag
  - Ingestion rate
  - Error rate
  - P95/P99 latency
- [ ] Add health checks and readiness endpoints for all RunLedger services.
- [ ] Add alert routing:
  - Local dev: Mailpit
  - Production: SMTP, Slack, Teams, webhook

### Enhanced OpenTelemetry Framework

- [ ] Expand OTEL support beyond simple traces.
- [ ] Add OTEL pipelines for:
  - Traces
  - Metrics
  - Logs
  - Profiles later if needed
- [ ] Add collector processors:
  - batch
  - memory limiter
  - resource detection
  - attributes enrichment
  - tail sampling
  - span metrics
  - transform rules
  - PII redaction
- [ ] Add collector connectors to derive metrics from spans:
  - request count
  - token count
  - cost
  - latency
  - errors
  - cache hits
  - rejected requests
- [ ] Add semantic attributes for AI usage:
  - `runledger.org_id`
  - `runledger.org_name`
  - `runledger.workspace_id`
  - `runledger.workspace_name`
  - `runledger.user_id`
  - `runledger.user_email`
  - `runledger.team`
  - `runledger.application`
  - `runledger.agent`
  - `runledger.skill`
  - `runledger.intent`
  - `runledger.model`
  - `runledger.provider`
  - `runledger.route`
  - `runledger.tool`
  - `runledger.outcome`
  - `runledger.optimization_applied`
  - `runledger.savings_usd`
  - `runledger.cost_usd`
  - `llm.input_tokens`
  - `llm.output_tokens`
  - `llm.total_tokens`
- [ ] Tie users to models in the telemetry model:
  - user -> prompt -> intent -> agent -> route -> model -> tool -> result.
- [ ] Add OTEL correlation to RunLedger runs:
  - trace ID
  - span ID
  - run ID
  - request ID
  - session ID
- [ ] Add collector-level auth and workspace attribution:
  - API key to workspace mapping.
  - tenant/org enrichment.
  - rejected telemetry when key is invalid.
- [ ] Add collector self-observability:
  - collector ingestion rate.
  - dropped spans.
  - processor failures.
  - exporter failures.
  - queue size.
- [ ] Add visualizations for OTEL-derived metrics:
  - requests by user/model.
  - cost by user/model.
  - traces by agent/tool.
  - errors by provider/route.
  - token trend by workspace.

### Additional Infra Recommendations

- [ ] Add Redis durability settings and backup plan if Redis stores non-ephemeral events.
- [ ] Add worker queue visibility:
  - pending jobs
  - failed jobs
  - retry count
  - oldest job age
- [ ] Add ClickHouse evaluation for high-volume analytics:
  - Use Postgres for transactional data.
  - Use ClickHouse for large request/trace/metric rollups if Postgres dashboards become slow.
- [ ] Add object lifecycle rules:
  - keep hot traces for 7-30 days.
  - archive cold traces to S3.
  - expire raw prompts according to retention policy.
- [ ] Add compliance export storage:
  - audit exports.
  - data subject exports.
  - org-level usage exports.
- [ ] Add feature flags:
  - LaunchDarkly-compatible later, simple DB/env flags now.
- [ ] Add rate-limit and abuse protection:
  - per API key
  - per workspace
  - per org
  - per route
  - per user
- [ ] Add policy engine evaluation:
  - start with simple rules in RunLedger.
  - evaluate Open Policy Agent only if policies become complex.
- [ ] Add local certificate/TLS story for realistic customer demos.
- [ ] Add deployment profiles:
  - `core`
  - `dev`
  - `observability`
  - `backup`
  - `email`
  - `full-demo`
  - `production-reference`

### Customer Bring-Up Checklist

- [ ] Database:
  - Postgres endpoint
  - backup policy
  - restore test
- [ ] Cache/queue:
  - Redis endpoint
  - persistence decision
  - queue monitoring
- [ ] Object storage:
  - S3-compatible bucket
  - lifecycle rules
  - encryption
  - restore permissions
- [ ] Email:
  - SMTP provider
  - sender domain
  - verification
  - welcome/invite test
- [ ] Observability:
  - Prometheus/VictoriaMetrics
  - Grafana
  - Loki/OpenSearch
  - Tempo/Jaeger
  - alert routing
- [ ] Security:
  - secrets manager
  - TLS
  - API key rotation
  - audit retention
- [ ] AI telemetry:
  - OTLP endpoint
  - API key/workspace mapping
  - Gateway route setup
  - Provider pricing
  - Budget alerts

### Acceptance Criteria

- [ ] A local developer can run `core` only or opt into `full-demo`.
- [ ] Backup and restore can be demonstrated against MinIO.
- [ ] Welcome, invite, password reset, and alert emails can be tested in Mailpit.
- [ ] Production SMTP can be configured without code changes.
- [ ] OTEL shows traces, metrics, and logs with RunLedger org/workspace/user/model attribution.
- [ ] Infra monitoring is handled by open-source tools while RunLedger focuses on AI Operations Intelligence.
- [ ] Customer bring-up docs clearly state which infra is required and which is optional.

### Official References To Use During Implementation

- OpenTelemetry Collector: https://opentelemetry.io/docs/collector/
- OpenTelemetry Collector architecture: https://opentelemetry.io/docs/collector/architecture/
- MinIO S3-compatible object storage: https://github.com/minio/minio
- Mailpit local SMTP testing: https://mailpit.axllent.org/
- Mailpit SMTP configuration: https://mailpit.axllent.org/docs/configuration/smtp/
- Firebase Local Emulator Suite: https://firebase.google.com/docs/emulator-suite

---

## Phase 3B - Scheduled Operations And Professional Rebrand

### Goal

Add first-class scheduling for operational workflows and refresh the visual identity so RunLedger feels enterprise-grade, calm, and deliberate.

The current product should move away from loud purple gradients and high-impact accent colors. The brand should feel professional, soothing, trustworthy, and designed for daily enterprise operations.

### Email Reporting Schedule

- [x] Add scheduled email report configuration as a real product feature.
- [x] Support report cadence:
  - Never
  - Daily
  - Weekly
  - Monthly
  - Custom cron later
- [x] Support report delivery time:
  - Time of day
  - Timezone
  - Business-day only option later
- [x] Support report recipients:
  - Workspace admins
  - Org admins
  - Platform admins
  - Custom email list
  - Team distribution list
- [x] Support report scope:
  - Platform report
  - Org report
  - Workspace report
  - Team/application report later
- [~] Support report templates:
  - Executive FinOps summary
  - Workspace usage summary
  - Model usage report
  - Savings and optimization report
  - Alert summary
  - Compliance/audit digest
- [x] Add "Send report now" for on-demand testing.
- [~] Add "Send test report to me" before enabling schedule.
- [ ] Add email delivery history:
  - report type
  - recipients
  - status
  - error
  - sent at
  - triggered by schedule or manual action
- [x] Add backend scheduler support:
  - Persist cadence, time, timezone, recipients, and report type.
  - Celery beat or scheduler evaluates schedules.
  - Worker generates correct report scope and sends email.
  - Scheduler respects workspace/org/platform RBAC.
- [x] Add UI location:
  - Platform Admin: Settings -> Email for global defaults.
  - Org Admin: Integrations or Alert Rules for org/workspace reporting schedules.
  - Workspace Admin: optional workspace reporting preferences if allowed.

### Backup Schedule

- [~] Add scheduled backup configuration as a first-class Platform Admin feature.
- [x] Support backup cadence:
  - Daily
  - Weekly
  - Monthly
  - Custom cron later
- [x] Support backup time and timezone.
- [x] Support backup target:
  - Local path for dev
  - MinIO for local full-demo
  - S3-compatible endpoint for customer deployments
  - AWS S3
  - GCS/Azure Blob later
- [x] Support backup contents:
  - Control-plane Postgres
  - Audit ledger snapshots
  - Exports
  - OTEL trace archive
  - Provider profiles
  - Gateway routes
  - Prompt/version metadata
  - Optional optimization-layer stores
- [x] Add backup retention policy:
  - keep last N backups
  - keep daily for N days
  - keep weekly for N weeks
  - keep monthly for N months
- [ ] Add backup encryption and checksum tracking.
- [ ] Add backup history:
  - started at
  - completed at
  - status
  - size
  - target bucket/path
  - checksum
  - error
  - initiated by schedule or manual action
- [ ] Add "Run backup now" action.
- [ ] Add "Restore drill" workflow:
  - validate backup exists
  - verify checksum
  - dry-run restore
  - restore into scratch namespace/environment
- [ ] Add backup alerts:
  - backup failed
  - backup missing
  - restore drill overdue
  - bucket unavailable
  - backup size anomaly
- [x] Add UI location:
  - Platform Admin: Settings -> Backup & Restore.
  - Integrations: S3/MinIO connection card and test connection.

### Professional Theme Rebrand

- [x] Define a new visual direction:
  - calm
  - premium
  - enterprise-ready
  - trustworthy
  - low-glare
  - not loud
  - not neon
  - not generic purple SaaS
- [x] Replace the current purple/violet-heavy brand palette.
- [x] Candidate palettes to explore:
  - Slate + teal + mist blue
  - Graphite + sea glass + soft cyan
  - Warm gray + deep navy + muted emerald
  - Charcoal + mineral blue + sage
- [x] Recommended default palette:
  - Background: soft slate / near-black navy
  - Primary: deep teal
  - Secondary accent: muted cyan
  - Success: restrained emerald
  - Warning: amber but muted
  - Danger: calm red, not neon
  - Charts: balanced categorical palette with no single purple bias
- [x] Update global design tokens:
  - background
  - foreground
  - card
  - primary
  - secondary
  - muted
  - accent
  - border
  - ring
  - chart colors
- [x] Update high-visibility surfaces:
  - Login page
  - Sidebar
  - TopBar
  - Buttons
  - Active navigation states
  - Role badges
  - Form focus states
  - Toast/action states
  - Integration cards
  - Alert Rules cards
  - Settings pages
- [x] Replace harsh gradients with subtle surfaces:
  - soft radial wash
  - low-opacity panel tint
  - thin borders
  - restrained shadows
  - calmer hover states
- [x] Improve light theme:
  - reduce washed-out contrast
  - make sidebar feel intentional
  - avoid pale purple selected states
  - make primary actions professional
- [x] Improve dark theme:
  - avoid over-black empty space
  - reduce neon accents
  - improve input contrast
  - make panels look layered but not glowing
- [x] Add design QA checklist:
  - no unreadable low-contrast text
  - no loud purple gradients
  - no inconsistent active states
  - no button colors outside token system
  - charts remain distinguishable in light and dark mode
  - dashboard screenshots look enterprise-ready

### Acceptance Criteria

- [x] Email report schedules are represented in product requirements and persisted for workspace-level reporting.
- [x] Backup schedules are represented in product requirements and surfaced in Platform Settings.
- [~] Users can test email delivery and backup connectivity before enabling schedules. Email test exists; S3 test connection remains a product-managed backup follow-up.
- [x] The new theme feels calm, professional, and polished in both light and dark mode.
- [x] The login page, sidebar, and dashboard no longer look like a generic purple SaaS template.
- [x] All new scheduling capabilities are role-gated correctly.

### Completion Notes

- [x] Backend flags now default optional jobs off: `EMAIL_ENABLED`, `EMAIL_REPORTS_ENABLED`, and `BACKUP_ENABLED`.
- [x] Scheduled email reports are backed by persisted cadence, hour, timezone, recipient mode, custom recipients, and last-sent timestamp.
- [x] Celery Beat skips scheduled report enqueueing unless email delivery and scheduled reports are enabled.
- [x] Platform Settings now contains Email Delivery and Backup & Restore surfaces.
- [x] New RunLedger logo, calmer shell navigation, Settings cards, and professional login screen are implemented.
- [x] Copy polish: backup wording distinguishes Helm/script backup availability today from future product-managed UI scheduling.
- [x] Font pass completed with Instrument Sans for body copy, Sora for headings/brand, and JetBrains Mono for numeric/code surfaces.
- [x] User-selected blue radial RunLedger mark and `Intelligence, Accounted.` tagline are now the product logo direction.

---

## Phase 3C - Kafka Streaming And Event Bus

### Goal

Add Kafka support so RunLedger can stream AI operations events into customer data platforms in real time.

Start with **Kafka export** as an optional integration. Do not make Kafka required for the default local stack until the product has a clear need for an internal event bus.

### Current State To Verify

- [x] Frontend API helpers already reference Kafka export endpoints:
  - `listKafkaExportConfigs`
  - `createKafkaExportConfig`
  - `updateKafkaExportConfig`
  - `deleteKafkaExportConfig`
  - `testKafkaExportConfig`
  - `listKafkaExportDeliveries`
- [x] Frontend types already define Kafka config and delivery types.
- [x] API dependency list includes `aiokafka`.
- [x] Seed script has opt-in Kafka export config seeding behind `SEED_EXTERNAL=true`.
- [x] Backend router/model/worker implementation still needs to be confirmed or built.
- [x] Integrations page should show Kafka as planned/incomplete until backend routes are real.

### Product Direction

Use Kafka for two related but separate jobs:

- Customer-facing event export: stream RunLedger events into the customer's Kafka/Redpanda/Confluent cluster.
- Internal event bus later: decouple ingestion, rollups, alerting, recommendations, and exports if volume grows.

### Recommended MVP

- [x] Build customer-facing Kafka export first.
- [x] Keep Kafka optional.
- [x] Support Redpanda locally for demos because it is Kafka-compatible and lighter to run.
- [x] Support external Kafka/Confluent/MSK for production.
- [x] Add Kafka Integration card to Integrations Hub.
- [x] Add Kafka config CRUD:
  - label
  - bootstrap servers
  - topic prefix
  - security protocol
  - SASL mechanism
  - SASL username
  - SASL password secret
  - SSL CA cert
  - enabled flag
  - event types
- [x] Add test connection action.
- [x] Add delivery log:
  - event type
  - topic
  - status
  - attempt
  - error
  - delivered at
  - created at
- [ ] Add retry policy for failed deliveries.
- [~] Add dead-letter topic support.

### Events To Stream

- [~] `run.started`
- [x] `run.completed`
- [x] `run.failed`
- [~] `gateway.request.completed`
- [~] `gateway.request.rejected`
- [~] `budget.threshold_crossed`
- [~] `budget.breached`
- [~] `alert.fired`
- [~] `optimization.applied`
- [~] `route.changed`
- [~] `mcp.tool.called`
- [~] `mcp.tool.blocked`
- [~] `approval.requested`
- [~] `approval.decided`
- [~] `email.report.sent`
- [~] `backup.completed`
- [~] `backup.failed`
- [~] `compliance.export.ready`

### Topic Strategy

- [x] Support topic prefix:
  - `runledger.dev`
  - `runledger.prod`
  - `customer.runledger`
- [x] Recommended topics:
  - `{prefix}.runs`
  - `{prefix}.gateway`
  - `{prefix}.alerts`
  - `{prefix}.budgets`
  - `{prefix}.optimizations`
  - `{prefix}.mcp`
  - `{prefix}.approvals`
  - `{prefix}.ops`
  - `{prefix}.deadletter`
- [ ] Support single-topic mode for simple deployments.
- [x] Support event-type-to-topic routing for enterprise deployments.

### Event Envelope

- [x] Define a stable event envelope:

```json
{
  "event_id": "evt_...",
  "event_type": "run.completed",
  "schema_version": "v1",
  "occurred_at": "2026-07-30T12:00:00Z",
  "org_id": "...",
  "workspace_id": "...",
  "user_id": "...",
  "run_id": "...",
  "trace_id": "...",
  "source": "gateway|sdk|otlp|mcp|worker",
  "data": {},
  "metadata": {}
}
```

- [x] Add schema versioning.
- [ ] Add idempotency key.
- [~] Add trace/run correlation IDs.
- [ ] Add optional redaction mode before export.
- [~] Add org/workspace/user/model attribution.

### Security

- [x] Support Kafka security protocols:
  - PLAINTEXT for local only
  - SSL
  - SASL_PLAINTEXT
  - SASL_SSL
- [x] Support SASL mechanisms:
  - PLAIN
  - SCRAM-SHA-256
  - SCRAM-SHA-512
- [ ] Store Kafka credentials encrypted or through secret references.
- [x] Redact secrets from API responses.
- [ ] Add audit log for:
  - config created
  - config updated
  - config deleted
  - test connection
  - event export failure
- [x] Allow org/workspace admins to manage Kafka export only for their permitted scope.

### Local Demo Infra

- [ ] Add optional Redpanda service under a Docker Compose `streaming` or `full-demo` profile.
- [ ] Add Redpanda Console if useful for demos.
- [ ] Add sample consumer script:
  - print RunLedger events
  - verify topic creation
  - validate schema fields
- [ ] Add scenario/lab:
  - trigger a Gateway request
  - fire an alert
  - breach a budget
  - watch events stream in Redpanda Console

### Internal Event Bus Later

- [ ] Consider internal Kafka only after export MVP is stable.
- [ ] Candidate internal producers:
  - Gateway
  - OTLP worker
  - MCP server
  - Alert worker
  - Budget worker
  - Backup worker
  - Email worker
- [ ] Candidate internal consumers:
  - rollup worker
  - anomaly detector
  - optimization recommender
  - external export worker
  - dashboard materialization worker
- [ ] Keep Postgres as source of truth.
- [ ] Use Kafka for streaming/event fanout, not primary storage.

### Acceptance Criteria

- [x] Org or workspace admin can configure Kafka export.
- [x] Test connection sends a test event to Kafka.
- [~] Run, alert, budget, and optimization events can be streamed.
- [~] Failed deliveries are retried and visible in UI.
- [ ] Local full-demo can run Redpanda and show streamed events.
- [x] Kafka remains optional for normal local development.

### Phase 3C Notes

- [x] Added backend Kafka config and delivery models plus Alembic migration `054_kafka_export.py`.
- [x] Added `/integrations/kafka/configs` CRUD, test action, and delivery log endpoints.
- [x] Added fail-open Kafka export service using `aiokafka`.
- [x] Hooked ingest pipeline `run_end` to export `run.completed` and `run.failed`.
- [x] Added Integrations UI for Kafka create/test/enable/delete and recent delivery history.
- [~] Other event producers, failed-delivery retry worker, secret encryption, and local Redpanda demo profile remain.

---

## Phase 4 - Executive Dashboard

### Goal

Give a CTO/CIO a 30-second view of AI operations.

### TODO

- [x] Build KPI cards:
  - Monthly AI spend
  - Savings
  - ROI
  - Total requests
  - Average latency
  - Cache hit rate
  - Token reduction
  - Model routing savings
  - Prompt compression savings
  - Optional carbon saved
- [x] Add top departments/workspaces table:
  - Team
  - Spend
  - Saved
  - Optimization percentage
- [x] Add monthly trend chart:
  - Projected spend
  - Actual spend
  - Optimized spend
  - RunLedger intervention markers.
- [x] Add cost waterfall:
  - Original spend
  - Prompt compression savings
  - Cache savings
  - Model routing savings
  - Local model savings
  - Final spend
- [x] Add savings attribution chart:
  - Prompt compression
  - Cache
  - Small model routing
  - Fine tuning
  - Local LLM
  - Tool optimization

### Acceptance Criteria

- [x] The first screen explains spend, savings, ROI, and trend without technical drilldown.
- [x] Every KPI has a tooltip explaining calculation logic.
- [x] Executives can export or snapshot the view.

### Phase 4 Notes

- [x] Rebuilt `/global-dashboard` as the Platform Admin executive dashboard.
- [x] Uses platform request-flow telemetry for spend, requests, latency, cache hit rate, token reduction, and savings.
- [x] Added trend, cost waterfall, savings attribution, top workspace drivers, CSV export, and ledger snapshot action.
- [x] Keeps platform lifecycle context visible below the executive view.
- [x] Savings category attribution now has finance-grade realized savings fields for new provider calls, with telemetry fallback for legacy traffic.

---

## Phase 5 - AI Request Flow Dashboard

### Goal

Make the Sankey diagram the centerpiece of RunLedger.

### TODO

- [x] Build Sankey flow:
  - Incoming request
  - Intent
  - Skill
  - Agent
  - Model
  - Tool
  - Result
- [x] Support alternate Sankey views:
  - User -> Intent -> Model
  - Prompt -> Skill -> Agent -> Model -> Tool -> Result
  - Request -> Route -> Provider -> Outcome
  - Team -> Application -> Agent -> Model -> Cost
- [x] Use line thickness to represent:
  - Request count by default.
  - Cost as optional mode.
  - Tokens as optional mode.
  - Savings as optional mode.
- [x] On hover show:
  - Requests
  - Input tokens
  - Output tokens
  - Cost
  - Savings
  - Average latency
  - Success rate
- [x] On click drill down to:
  - Matching requests
  - Matching traces
  - Top prompts
  - Top users
  - Top agents
  - Optimization recommendations.

### Acceptance Criteria

- [x] A user can answer "where did every request go?" from this view.
- [x] Sankey supports Platform, Org, and Workspace scopes.
- [x] Sankey links to request explorer.

---

## Phase 6 - Model Usage And Routing Dashboard

### Goal

Show which models are used, why they are selected, and how routing changes cost and quality.

### TODO

- [x] Add 100% stacked resource usage timeline:
  - GPT-5
  - Claude
  - Gemini
  - Local Llama
  - DeepSeek
  - Cached responses
  - Rejected requests
- [x] Tooltip for each date/model:
  - Input tokens
  - Output tokens
  - Cost
  - Savings from cache
  - Latency
  - Outcome rate
- [x] Add model usage table:
  - Model
  - Requests
  - Input tokens
  - Output tokens
  - Total cost
  - Average response time
  - Average quality score
- [x] Add model routing distribution:
  - Claude percentage
  - GPT percentage
  - Gemini percentage
  - Local model percentage
  - Failed/rejected percentage
- [x] Add routing decision detail:
  - Why this model was selected.
  - Which alternatives were considered.
  - Estimated cost difference.
  - Expected quality/latency tradeoff.

### Acceptance Criteria

- [x] Users can see model usage trends over time.
- [x] Users can explain routing decisions.
- [x] Users can compare cost, latency, and quality by model.

### Implementation Notes

- [x] Added `/model-usage`.
- [x] Added 100% stacked model timeline and rich tooltip detail using request-flow telemetry.
- [x] Added model usage table with request, token, cost, latency, and success-rate quality proxy.
- [x] Added routing distribution and route decision explanations.
- [~] Dedicated quality score is currently represented by success/outcome proxy until explicit quality scores are stored per request.

---

## Phase 7 - Cost, Savings, And ROI Dashboard

### Goal

Make every dollar traceable and every saving explainable.

### TODO

- [x] Build cost breakdown drilldowns:
  - Team
  - Project
  - Application
  - User
  - Agent
  - Model
  - Tool
  - Time
- [x] Build ROI table:
  - Engineering
  - Sales
  - Support
  - Finance
  - Marketing
- [x] Table columns:
  - Spend
  - Saved
  - Optimization percentage
  - Requests
  - Cost per request
  - Outcome rate
- [x] Build savings screen:
  - Prompt compression
  - Cache hits
  - Smart model routing
  - Local models
  - Duplicate request detection
  - Tool optimization
- [x] Add cost heatmap:
  - Rows: teams/workspaces/applications.
  - Columns: day of week or hour of day.
  - Color: cost intensity.
- [x] Add budget overlay:
  - Budget used
  - Budget remaining
  - Forecasted overspend
  - Alert status

### Acceptance Criteria

- [x] A customer can explain where spend came from.
- [x] A customer can explain why RunLedger saved money.
- [x] A customer can identify the next highest-value optimization.

### Implementation Notes

- [x] Added `/cost-savings`.
- [x] Added cost breakdown by team, project, application, user, agent, model, tool, and time.
- [x] Added ROI table with spend, saved, optimization percentage, requests, cost/request, and outcome rate.
- [x] Added cost heatmap by day of week.
- [x] Added next optimization target recommendation.
- [x] Savings attribution stores realized `savings_usd`, `savings_category`, and `savings_reason` on provider calls; legacy traffic still has telemetry fallback.
- [x] Budget overlay uses `/budgets/rollup` for workspace, org, and platform budget posture.

---

## Phase 8 - Engineering Dashboard And Request Explorer

### Goal

Give engineers a debugging console for AI systems.

### TODO

- [x] Build engineering dashboard metrics:
  - Latency
  - Error percentage
  - Retry percentage
  - Cache percentage
  - Hallucination percentage
  - Token usage
  - Cost per request
  - Cost per team
  - Cost per agent
  - Cost per tool
- [x] Build prompt lifecycle view:
  - Prompt
  - Cache check
  - RAG check
  - Skill selection
  - Reasoning decision
  - Model selection
  - Response
  - Feedback
- [x] Build agent dependency graph:
  - Agent
  - Sub-agent
  - Memory
  - Policy engine
  - Model
  - Tool
  - Response
- [x] Build prompt quality funnel:
  - Total prompts
  - Valid prompts
  - Routed prompts
  - Cached prompts
  - Answered prompts
  - Accepted prompts
  - Positive feedback prompts
- [x] Build request explorer:
  - Prompt
  - Intent
  - Selected agent
  - Selected model
  - Tools called
  - Token usage
  - Cost
  - Latency
  - Final response
  - Cache status
  - Routing decision
  - Reason for routing
  - Optimization applied
  - Outcome

### Acceptance Criteria

- [x] Engineers can drill from high-level chart to individual request.
- [x] Engineers can understand why a model/tool/route was used.
- [x] Engineers can debug bad outcomes and high-cost traces.

---

## Phase 9 - Optimization Opportunities

### Goal

Make RunLedger feel like an AI consultant, not just a reporting tool.

### TODO

- [x] Build recommendations engine inputs:
  - High-cost intents
  - Expensive model mismatch
  - Low cache hit rate
  - Reasoning overuse
  - High retry rate
  - Tool overuse
  - Latency outliers
  - Poor outcome quality
- [x] Build recommendation cards:
  - Problem
  - Evidence
  - Suggested action
  - Expected savings
  - Expected risk
  - One-click experiment option
- [x] Example recommendations:
  - Engineering is sending documentation requests to GPT-5. Claude Sonnet would reduce cost by 45%.
  - Customer Support cache hit rate is 12%. Expected rate is 45%.
  - 18% of requests are unnecessarily using reasoning models.
  - Local Llama can handle 30% of summarization traffic with projected savings of $8k/month.
- [x] Link recommendations to:
  - Gateway route changes.
  - Prompt compression.
  - Cache policy.
  - Provider profile updates.
  - Experiment creation.

### Acceptance Criteria

- [x] Recommendations are backed by dashboard evidence.
- [x] Users can launch an experiment from a recommendation.
- [x] Users can see projected and realized savings.

### Phase 9 Notes

- [x] Added `/optimization-opportunities`.
- [x] Added rule-backed recommendations for cache hit rate, model mismatch, local-model eligibility, reasoning overuse, tool overuse, latency outliers, and failed spend.
- [x] Each card shows problem, evidence, suggested action, projected savings, risk, confidence, and launch links.
- [x] Wired the page into the Improve sidebar.
- [x] Realized savings is surfaced from persisted provider-call `savings_usd` attribution for the matching recommendation segment.

---

## Phase 10 - Visual Design And Interaction

### Goal

Make the dashboards feel premium, fast, and memorable.

### TODO

- [x] Design language:
  - Datadog clarity.
  - Grafana depth.
  - GitHub Insights readability.
  - Vercel Analytics polish.
- [x] Add interactive chart states:
  - Hover tooltips.
  - Click-to-filter.
  - Brush time range.
  - Compare periods.
  - Drilldown breadcrumbs.
  - Export chart/table.
- [x] Add empty states:
  - No usage yet.
  - No savings yet.
  - No optimizations enabled yet.
  - No request flow available yet.
- [x] Add loading states and skeletons for all charts.
- [x] Add responsive layout for large desktop, laptop, and tablet widths.
- [x] Make the visual hierarchy obvious:
  - Executive summary first.
  - Flow/routing second.
  - Drilldown/debug last.

### Acceptance Criteria

- [x] A first-time user understands the dashboard in under 30 seconds.
- [x] Charts feel interactive and intentional.
- [x] The page does not feel like generic admin UI.

---

## Phase 11 - Demo Data, Labs, And Scenarios

### Goal

Make the dashboard demo believable before real enterprise data exists.

### TODO

- [ ] Add demo seed data for:
  - Multiple orgs
  - Multiple workspaces
  - Teams
  - Applications
  - Models
  - Agents
  - Tools
  - Intents
  - Outcomes
  - Savings categories
- [ ] Add scenarios:
  - Cache optimization reduces spend.
  - Model routing shifts traffic from expensive to cheaper models.
  - Prompt compression reduces token usage.
  - Local model handles summarization traffic.
  - Bad route causes latency/cost spike.
  - Budget alert prevents runaway agent loop.
  - MCP tool filtering blocks risky tool usage.
- [ ] Add visual regression fixtures for dashboards.
- [ ] Add screenshots to product/demo docs.

### Acceptance Criteria

- [ ] Demo dashboard tells a coherent story.
- [ ] Demo shows before/after RunLedger optimization.
- [ ] Demo can be reset and replayed.

---

## Phase 12 - Implementation Order

### Recommended Build Sequence

- [x] PR 1: Analytics data contracts and dashboard API skeleton.
- [x] PR 2: Demo seed data for dashboard development.
- [x] PR 3: Platform, Org, and Workspace dashboard routing and RBAC.
- [x] PR 4: Executive KPI cards, trend chart, ROI table.
- [x] PR 5: Sankey request flow, drilldown interactions, and backend aggregate flow API.
- [x] PR 6: Model usage, stacked resource timeline, and routing details.
- [x] PR 7: Cost breakdown, savings attribution, waterfall, and heatmap.
- [x] PR 8: Engineering dashboard, request explorer, prompt lifecycle, and agent DAG.
- [x] PR 9: Optimization recommendations and experiment launch hooks.
- [x] PR 10: Publishable RunLedger skills for Claude, Codex, Devin, and Cursor.
- [x] PR 11: Skill-generated markdown/config defaults and validation scripts.
- [ ] PR 12: Demo polish, docs, labs, and screenshots.

### Acceptance Criteria

- [ ] Each PR has tests or seeded demo validation.
- [ ] Each dashboard feature works at Platform, Org, and Workspace scope where applicable.
- [x] Each skill has setup validation and a RunLedger smoke event.

---

## Phase 13 - Product Differentiators And Advanced Roadmap

### Goal

Add high-leverage features that make RunLedger feel like an AI operations advisor, not just a reporting and cost dashboard.

These ideas should help customers answer:

- Is RunLedger wired correctly?
- What changed in AI usage?
- What should I optimize next?
- What can I safely enforce?
- How do I prove AI governance and savings?

### Integration Health Center

- [x] Add a single health page for all integration paths.
- [x] Show health for:
  - Gateway
  - OTLP
  - MCP
  - SDK ingestion
  - SMTP/email
  - Backup storage
  - Webhooks
  - LiteLLM
  - Open WebUI
  - OpenHands
  - LangGraph
  - Claude
  - Codex
  - Cursor
  - Windsurf
  - Devin
- [x] Show:
  - connected/disconnected
  - last event received
  - last error
  - API key used
  - workspace mapping
  - test connection
  - setup instructions
- [x] Add a "fix this" action where possible.

### Optimization Simulator

- [x] Add a simulator that previews savings before changing routes or policies.
- [x] Inputs:
  - current route
  - proposed route
  - intent
  - model
  - team/workspace
  - time range
  - cache setting
  - compression setting
- [x] Outputs:
  - projected savings
  - projected latency change
  - projected quality risk
  - projected cache impact
  - affected request count
  - confidence level
- [x] Example:
  - Move summarization from GPT-5 to Claude/local model.
  - Projected savings: `$8.2k/month`.
  - Expected latency: `+120ms`.
  - Quality risk: `low`.

### Policy Dry Run Mode

- [ ] Add dry-run mode for budgets, model routing, tool filtering, and data capture.
- [ ] Show what would have been blocked without actually blocking it.
- [ ] Support dry-run reports:
  - requests that would be rejected
  - agents that would need approval
  - MCP tools that would be blocked
  - models that would be rerouted
  - expected savings
- [ ] Add "promote to enforcement" after review.
- [ ] Add audit log entries for dry-run policy decisions.

### AI Request Replay Lab

- [ ] Add a lab to replay past requests through alternate routes.
- [ ] Compare:
  - model
  - provider
  - prompt compression
  - cache policy
  - local model
  - reasoning on/off
  - tool availability
- [ ] Show side-by-side:
  - response quality
  - cost
  - tokens
  - latency
  - tool usage
  - outcome score
- [ ] Allow replay results to create an experiment.
- [ ] Allow winning replay config to become a Gateway route recommendation.

### Agent Runbooks

- [ ] Auto-generate incident-style summaries for expensive, failed, or risky agent runs.
- [ ] Include:
  - what happened
  - why it cost so much
  - which model was selected
  - which tools were used
  - which policy decisions occurred
  - what failed
  - what to change next
- [ ] Add runbook export for:
  - markdown
  - PDF later
  - Slack/email summary
- [ ] Link runbooks from Request Explorer and Agent Dependency Graph.

### Cost Anomaly Detection

- [>] Moved to Phase 15 - Traditional AI/ML Intelligence Layer with full ML-based implementation (Z-score, EWMA, Isolation Forest, seasonal decomposition).

### Chargeback And Showback Reports

- [ ] Add monthly finance-ready reports by:
  - org
  - workspace
  - team
  - user
  - app
  - model
  - agent
  - provider
  - cost center
- [ ] Support:
  - CSV export
  - JSON export
  - email schedule
  - PDF later
- [ ] Add allocation rules:
  - by workspace
  - by user
  - by app tag
  - by agent tag
  - by API key
- [ ] Add variance vs budget.

### Approval Workflows

- [ ] Add approvals for expensive or risky AI actions.
- [ ] Require approval before:
  - exceeding task budget
  - using premium reasoning model
  - calling external MCP tool
  - running long autonomous agent session
  - exporting sensitive data
  - changing Gateway route policy
- [ ] Support approval channels:
  - RunLedger UI
  - email
  - Slack
  - Teams later
- [ ] Add approval audit trail.
- [ ] Add auto-approval policies for trusted users/workspaces.

### Model Quality Scorecards

- [ ] Add scorecards by model and provider.
- [ ] Compare:
  - cost
  - latency
  - error rate
  - acceptance rate
  - hallucination flags
  - retry rate
  - cache compatibility
  - user feedback
  - eval score
- [ ] Use scorecards to justify routing recommendations.
- [ ] Add model score trend over time.

### Customer Onboarding Wizard

- [ ] Add "Connect your first AI app" guided flow.
- [ ] Steps:
  - create org
  - create workspace
  - choose integration
  - generate API key
  - copy config
  - send test request
  - view first run
  - enable budget alert
- [ ] Add paths for:
  - LiteLLM
  - Open WebUI
  - OpenHands
  - LangGraph
  - Claude
  - Codex
  - Cursor
  - Windsurf
  - Devin
- [ ] Show completion checklist and health status.

### Data Capture Policy Studio

- [ ] Add UI to define what RunLedger stores.
- [ ] Support capture modes:
  - full prompt and response
  - redacted prompt and response
  - prompt metadata only
  - response metadata only
  - no body capture
- [ ] Support policies by:
  - org
  - workspace
  - API key
  - model route
  - user
  - intent
  - agent
- [ ] Add retention policy preview.
- [ ] Add PII redaction testing.
- [ ] Add compliance/audit explanation for each policy.

### AI Governance Audit Pack

- [ ] Add exportable governance evidence bundle.
- [ ] Include:
  - who used which model
  - when it was used
  - what route was selected
  - what data was captured
  - what was redacted
  - which policies were enforced
  - which approvals happened
  - which budget alerts fired
  - which retention policy applies
- [ ] Support export by:
  - org
  - workspace
  - user
  - date range
  - model
  - agent
- [ ] Add compliance-friendly summary page.

### RunLedger Demo Mode

- [ ] Add one-click demo seed mode.
- [ ] Seed:
  - synthetic enterprise org
  - multiple teams
  - multiple workspaces
  - realistic model traffic
  - cache savings
  - route optimizations
  - alerts
  - email reports
  - backup history
  - agent traces
  - MCP tool filtering
  - approval workflows
- [ ] Add demo reset command.
- [ ] Add demo runbook.
- [ ] Add screenshots for sales/product storytelling.

### Acceptance Criteria

- [ ] RunLedger explains what happened, why it happened, what it cost, and what to optimize next.
- [ ] Customers can safely try policy enforcement through dry-run mode.
- [ ] Finance users can produce chargeback/showback reports.
- [ ] Engineers can replay and compare requests.
- [ ] Executives can see savings and governance evidence.
- [ ] Demo mode tells a complete enterprise story without needing live customer data.

---

## Phase 14 - Guardrails, Content Safety And Policy Engine

### Goal

Add a guardrails system that lets customers define, test, and enforce content safety policies on AI requests and responses — matching and exceeding LiteLLM's guardrail capabilities while integrating deeply with RunLedger's cost, routing, and governance features.

### Custom Guardrails Engine

- [ ] Add custom guardrail definition with Python-like logic:
  - guardrail name
  - mode: `pre_call` (request), `post_call` (response), `both`
  - Python logic editor with restricted environment (no imports)
  - available inputs: `texts`, `images`, `tools`, `tool_calls`, `structured_messages`, `model`
  - available request data: `model`, `user_id`, `team_id`, `end_user_id`, `metadata`
  - return values: `allow()`, `block(reason)`, `modify(texts=[], images=[], tool_calls=[])`
  - default on/off toggle
- [ ] Add guardrail CRUD API:
  - `POST /guardrails` — create guardrail
  - `GET /guardrails` — list guardrails
  - `GET /guardrails/{id}` — get guardrail
  - `PUT /guardrails/{id}` — update guardrail
  - `DELETE /guardrails/{id}` — delete guardrail
  - `POST /guardrails/{id}/test` — test guardrail against sample input
- [ ] Add guardrail execution engine:
  - sandboxed Python execution (RestrictedPython or similar)
  - timeout enforcement (max 500ms per guardrail)
  - error handling (guardrail crash does not block request)
  - execution order and priority
  - short-circuit on first `block()`
- [ ] Add guardrail templates:
  - PII detection (email, phone, SSN, credit card)
  - prompt injection detection
  - topic restriction
  - language filter
  - token limit enforcement
  - model restriction by user role
  - cost threshold gate

### Built-In Content Filters (Guardrail Garden)

- [ ] Add zero-config content filters (no external dependencies):
  - Denied Financial Advice — block personalized investment/financial advice
  - Health And Personal Advice — detect health-related advice requests
  - Denied Legal Advice — block unauthorized legal advice
  - Denied Medical Advice — block medical diagnosis/treatment advice
  - Harmful Violence — detect violent content
  - Harmful Self-Harm — detect self-harm content
  - Harmful Child Safety — detect child safety violations
  - Harmful Illegal — detect content related to illegal activities
  - Bias Gender — detect gender-based discrimination
  - Bias Racial — detect racial discrimination and bias
  - Toxicity — detect toxic language and harassment
  - Code Injection — detect attempts to inject executable code
  - Data Exfiltration — detect attempts to extract sensitive data
- [ ] Use keyword + regex + heuristic scoring (no ML dependency for built-in filters)
- [ ] Allow severity thresholds: `off`, `low`, `medium`, `high`, `strict`
- [ ] Add per-workspace and per-org activation

### Partner Guardrail Integrations

- [ ] Add integration framework for third-party guardrail providers:
  - Presidio (Microsoft PII detection)
  - AWS Bedrock Guardrails
  - Lakera Guard (prompt injection, data leakage)
  - OpenAI Moderation API
  - Google Cloud Model Armor
  - Guardrails AI (open-source framework)
  - Prompt Security
  - Lasso Guardrail
- [ ] Add partner guardrail configuration:
  - API key / credentials
  - endpoint URL
  - timeout
  - fallback behavior (allow/block on error)
  - mode (pre_call / post_call / both)
- [ ] Add partner health monitoring
- [ ] Add cost tracking for paid partner guardrail API calls

### Guardrails Monitor

- [ ] Add real-time guardrails monitoring dashboard:
  - total evaluations
  - blocks
  - modifications
  - allow-throughs
  - false positive rate (via user feedback)
  - guardrail latency impact
  - top triggered guardrails
  - top blocked content categories
  - block rate by model/user/workspace
- [ ] Add guardrail event log:
  - timestamp
  - guardrail name
  - mode (pre/post)
  - decision (allow/block/modify)
  - reason
  - request metadata
  - latency added
- [ ] Add guardrail alerts:
  - block rate spike
  - guardrail error rate
  - guardrail latency degradation
  - new content pattern detected

### Guardrail Test Playground

- [ ] Add interactive test interface:
  - input text/prompt
  - select guardrails to test
  - see decision: allow/block/modify
  - see reason and matched rules
  - see latency per guardrail
  - iterate and refine guardrail logic
- [ ] Add batch testing:
  - upload CSV of test cases
  - run all guardrails
  - export results with pass/fail per case
- [ ] Add regression test sets:
  - save test cases per guardrail
  - run on guardrail update to catch regressions

### Gateway Integration

- [ ] Add guardrail execution hooks into model gateway:
  - pre-request: run pre_call guardrails before routing
  - post-response: run post_call guardrails before returning
  - modify: apply text/tool_call modifications inline
- [ ] Add guardrail bypass for trusted workspaces/API keys
- [ ] Add guardrail metrics to engineering dashboard
- [ ] Add guardrail cost attribution (latency overhead per request)

### Acceptance Criteria

- [ ] Customers can create custom guardrails without deploying code
- [ ] Built-in content filters work out of the box with zero external dependencies
- [ ] Partner guardrails can be connected through configuration
- [ ] Guardrail decisions are visible in request explorer and engineering dashboard
- [ ] Guardrail latency overhead is measurable and attributable
- [ ] Test playground allows iterative guardrail development

---

## Phase 15 - Traditional AI/ML Intelligence Layer

### Goal

Add traditional machine learning and statistical intelligence to RunLedger, transforming it from a reporting platform into a predictive AI operations advisor. Every model below uses classical ML/stats (no LLM dependency) so it runs locally, cheaply, and deterministically.

### Cost Anomaly Detection

- [ ] Add real-time anomaly detection for AI spend:
  - per-workspace cost anomaly (Z-score + rolling window)
  - per-user spend spike detection
  - per-model cost deviation
  - per-agent runaway loop detection
  - per-provider cost drift
- [ ] Detection methods:
  - Z-score with configurable sigma threshold (default 2.5σ)
  - Exponential Weighted Moving Average (EWMA) for trend-adjusted detection
  - Isolation Forest for multivariate anomalies (cost × tokens × latency)
  - Seasonal decomposition (STL) for time-of-day / day-of-week patterns
- [ ] Add anomaly severity levels:
  - `info` — unusual but within tolerance
  - `warning` — significant deviation, worth investigating
  - `critical` — likely incident, immediate attention needed
- [ ] Add anomaly cards in dashboard:
  - what changed (metric, dimension, magnitude)
  - when it started
  - likely cause (model change, traffic spike, new user, route change)
  - cost impact (dollars at risk)
  - recommended action
  - link to affected requests
- [ ] Add anomaly suppression:
  - mark false positive
  - suppress dimension for N hours/days
  - auto-learn from suppressions

### Usage And Latency Anomaly Detection

- [ ] Extend anomaly detection beyond cost:
  - latency P95 regression detection
  - error rate spike detection
  - cache hit rate drop detection
  - retry storm detection
  - token usage spike per request
  - provider availability degradation
  - model quality score regression
- [ ] Add per-model latency baseline tracking:
  - build rolling P50/P95/P99 baselines per model
  - alert when current window deviates from baseline
- [ ] Add correlated anomaly grouping:
  - if cost spike and latency spike happen together, group them
  - surface root cause: e.g., "provider X had a 3x latency increase causing retry storms"

### Cost And Token Forecasting

- [ ] Add time-series forecasting for AI spend:
  - forecast horizon: 7d, 30d, 90d
  - methods:
    - Linear regression with trend
    - Holt-Winters exponential smoothing (handles seasonality)
    - Prophet-style decomposition (trend + weekly + daily seasonality)
    - ARIMA for stationary series
  - confidence intervals (80% and 95%)
- [ ] Forecast dimensions:
  - total workspace cost
  - per-model cost
  - per-provider cost
  - per-team cost
  - per-intent cost
  - total token consumption
  - per-model token consumption
- [ ] Add forecast vs budget overlay:
  - projected spend vs budget limit
  - days until budget exhaustion
  - recommended budget adjustment
  - probability of budget breach
- [ ] Add forecast accuracy tracking:
  - compare past forecasts to actuals
  - MAPE (Mean Absolute Percentage Error)
  - improve model selection based on accuracy history
- [ ] Add forecast API:
  - `GET /analytics/forecast?metric=cost&dimension=model&horizon=30d`
  - returns: forecast points, confidence bands, accuracy score, method used

### Top-K Analysis Engine

- [ ] Add configurable Top-K analysis across all dimensions:
  - top K most expensive users
  - top K most expensive agents
  - top K most expensive models
  - top K most expensive intents
  - top K most expensive tools
  - top K highest latency requests
  - top K highest token usage requests
  - top K most error-prone routes
  - top K least-optimized workspaces
- [ ] Add Top-K with change detection:
  - new entrant to top K (wasn't there last period)
  - rank change (moved up/down N positions)
  - magnitude change (cost increased X%)
  - exit from top K (was there, now gone)
- [ ] Add Top-K alerting:
  - alert when a new user/agent enters top K spenders
  - alert when any top-K item increases by more than X%
- [ ] Add Top-K API:
  - `GET /analytics/top-k?dimension=user&metric=cost&k=10&compare=previous_period`

### Pattern Recognition

- [ ] Add usage pattern classification:
  - steady-state (consistent daily usage)
  - growing (week-over-week increase)
  - declining (week-over-week decrease)
  - spiky (high variance, irregular usage)
  - seasonal (predictable daily/weekly cycles)
  - one-shot (single burst, then nothing)
- [ ] Classify per workspace, user, agent, and model
- [ ] Use pattern type to improve forecast method selection
- [ ] Surface pattern insights:
  - "Workspace X has switched from steady-state to growing — forecast adjusted"
  - "Agent Y shows spiky pattern — consider rate limiting or budget cap"

### Request Complexity Scoring

- [ ] Add ML-based complexity scoring for incoming requests:
  - features: token count, tool count, intent, historical latency for similar requests
  - model: lightweight gradient boosting (XGBoost/LightGBM) trained on historical data
  - output: complexity tier (simple / medium / complex / reasoning)
  - use for: routing recommendations, cost estimation, SLA prediction
- [ ] Add complexity calibration:
  - auto-retrain on rolling 30d window
  - track prediction accuracy vs actual latency/cost
  - expose calibration metrics in engineering dashboard
- [ ] Add complexity-based routing suggestions:
  - "This request scored 0.2 complexity but was routed to GPT-4o — consider GPT-4o-mini"
  - integrate with optimization opportunities

### Cost Per Outcome Optimization

- [ ] Add outcome-weighted cost analysis:
  - cost per successful outcome by model
  - cost per successful outcome by route
  - cost per successful outcome by intent
  - identify: cheapest model that maintains quality threshold
- [ ] Add Pareto frontier visualization:
  - X axis: cost
  - Y axis: quality/success rate
  - plot each model/route combination
  - highlight Pareto-optimal configurations
- [ ] Add automated routing suggestions from Pareto analysis:
  - "For intent=summarization, Claude Haiku is Pareto-optimal (85% quality, 60% cheaper)"

### Intelligent Alert Thresholds

- [ ] Replace static alert thresholds with adaptive ones:
  - learn normal range per metric per workspace
  - adjust thresholds based on historical variance
  - reduce false positives for naturally variable workloads
  - tighten thresholds for stable workloads
- [ ] Add alert fatigue metrics:
  - alerts per day
  - acknowledged vs ignored ratio
  - time to acknowledge
  - auto-suppress low-value alerts
- [ ] Add alert correlation:
  - group related alerts (cost + latency + error rate all spiking)
  - surface single root cause instead of N separate alerts

### ML Infrastructure

- [ ] Add lightweight ML pipeline:
  - use scikit-learn, statsmodels, and optionally XGBoost/LightGBM
  - no GPU required
  - models stored as pickled artifacts in DB or S3
  - retraining via Celery scheduled tasks
  - per-workspace model isolation
- [ ] Add model registry:
  - model type (anomaly, forecast, complexity, etc.)
  - training date
  - training data window
  - accuracy metrics
  - workspace scope
  - active/inactive status
- [ ] Add ML feature store (lightweight):
  - pre-computed hourly/daily aggregates per dimension
  - materialized views or dedicated tables
  - used by all ML models for consistent feature computation
- [ ] Add ML observability:
  - prediction count per model
  - prediction latency
  - accuracy drift detection
  - retraining triggers

### Acceptance Criteria

- [ ] Anomaly detection runs automatically with no manual threshold configuration
- [ ] Cost forecasts are available for every workspace with accuracy tracking
- [ ] Top-K analysis surfaces unexpected changes with period-over-period comparison
- [ ] Pattern recognition improves forecast and routing suggestions
- [ ] Complexity scoring can feed into auto-router recommendations
- [ ] All ML models run locally without GPU or external API dependencies
- [ ] ML pipeline retrains automatically on a configurable schedule

---

## Phase 16 - Agentic Operations And Developer Experience

### Goal

Add agent lifecycle management, workflow orchestration visibility, developer playground tools, and operational utilities that match LiteLLM's Agentic and Developer Tools sections while deeply integrating with RunLedger's cost/governance platform.

### Agent Registry And Lifecycle

- [ ] Add agent registry:
  - agent name
  - agent type (autonomous, semi-autonomous, workflow, chat)
  - description
  - owner (user/team/workspace)
  - default model
  - default tools
  - budget envelope (max spend per run)
  - policy profile
  - status (active, paused, retired)
  - created/updated timestamps
- [ ] Add agent CRUD API:
  - `POST /agents` — register agent
  - `GET /agents` — list agents
  - `GET /agents/{id}` — get agent details
  - `PUT /agents/{id}` — update agent
  - `DELETE /agents/{id}` — retire agent
  - `GET /agents/{id}/runs` — list agent runs
  - `GET /agents/{id}/stats` — agent cost/performance summary
- [ ] Add agent dashboard page:
  - agent list with status, last run, total cost, run count
  - agent detail: cost trend, success rate, avg latency, tools used, models used
  - agent comparison: side-by-side cost/quality across agents

### Workflow Runs Visibility

- [ ] Add workflow run tracking:
  - workflow name
  - steps (ordered list of agent/model/tool invocations)
  - step status (pending, running, completed, failed, skipped)
  - step cost, latency, tokens
  - total workflow cost and duration
  - parent/child workflow relationships
- [ ] Add workflow run timeline visualization:
  - Gantt-style timeline showing step execution order and parallelism
  - step-level cost and latency annotations
  - click-to-drill into step detail
- [ ] Add workflow CRUD API:
  - `GET /workflows` — list workflow definitions
  - `GET /workflows/{id}/runs` — list runs for a workflow
  - `GET /workflows/{id}/runs/{run_id}` — run detail with steps
- [ ] Add workflow cost attribution:
  - total cost per workflow type
  - cost per step
  - optimization opportunities per workflow

### Agent Memory Management

- [ ] Add agent memory store:
  - key-value memory per agent per workspace
  - memory types: short-term (session), long-term (persistent), shared (cross-agent)
  - memory size limits per workspace/agent
  - memory retention policy
  - memory search (semantic or keyword)
- [ ] Add memory API:
  - `POST /agents/{id}/memory` — store memory
  - `GET /agents/{id}/memory` — retrieve memories
  - `DELETE /agents/{id}/memory/{key}` — delete memory
  - `POST /agents/{id}/memory/search` — search memory
- [ ] Add memory dashboard:
  - memory usage per agent
  - memory size trends
  - most accessed memories
  - memory cost (if using vector store)
- [ ] Add memory governance:
  - PII detection in stored memories
  - retention policy enforcement
  - memory audit log

### Vector Store Management

- [ ] Add vector store management UI:
  - list vector stores (Qdrant collections)
  - collection stats: document count, size, dimensions
  - search test interface
  - create/delete collections
  - upload documents with metadata
- [ ] Add vector store cost tracking:
  - storage cost per collection
  - query cost per search
  - embedding cost per document
- [ ] Add vector store health monitoring:
  - collection availability
  - query latency
  - index freshness

### API Playground

- [ ] Add interactive API playground:
  - select model and provider
  - compose prompt
  - set parameters (temperature, max tokens, top_p, etc.)
  - send request through RunLedger gateway
  - see response, cost, latency, tokens, route decision
  - compare responses across models side-by-side
  - save prompt/response pairs as test cases
- [ ] Add playground features:
  - conversation mode (multi-turn)
  - system prompt editor
  - tool/function calling test
  - structured output (JSON mode) test
  - image/vision input support
  - streaming response display
- [ ] Add playground history:
  - recent requests
  - cost per request
  - save favorites
  - share playground sessions

### Tag Management

- [ ] Add hierarchical tag system:
  - tag categories: team, project, environment, cost-center, custom
  - tag key-value pairs
  - tag inheritance (org -> workspace -> API key -> request)
  - tag-based filtering across all dashboards
  - tag-based cost attribution
- [ ] Add tag CRUD API:
  - `POST /tags` — create tag
  - `GET /tags` — list tags
  - `PUT /tags/{id}` — update tag
  - `DELETE /tags/{id}` — delete tag
- [ ] Add auto-tagging rules:
  - tag by API key
  - tag by model
  - tag by intent
  - tag by user
  - tag by request metadata pattern

### Search Tools Integration

- [ ] Add search tool registry:
  - register external search endpoints (web search, internal knowledge base, documentation)
  - search tool configuration: endpoint, auth, rate limits
  - search tool cost tracking
  - search result quality scoring
- [ ] Add search tool policies:
  - allow/deny search tools per workspace
  - rate limits per tool
  - cost limits per tool
  - content filtering on search results

### Tool Policies Engine

- [ ] Enhance existing tool filtering with policy engine:
  - allow/deny rules per tool per workspace
  - conditional rules (allow tool X only if budget > $Y)
  - time-based rules (allow tool X only during business hours)
  - approval-required rules (tool X needs admin approval)
  - cost-gated rules (tool X only if estimated cost < $Z)
- [ ] Add tool policy simulation:
  - show what would be blocked/allowed under proposed policy
  - impact analysis: how many requests affected
- [ ] Add tool usage analytics:
  - tool call frequency
  - tool cost attribution
  - tool success/failure rate
  - tool latency
  - unused tools

### Access Groups

- [ ] Add access groups (beyond individual user roles):
  - group name
  - group members
  - group permissions (workspace access, model access, tool access, budget access)
  - group-level budget limits
  - group-level guardrail profiles
- [ ] Add group CRUD API
- [ ] Add group-based dashboard filtering:
  - view cost by access group
  - view usage by access group
  - compare groups

### Response Cache Management

- [ ] Add dedicated response cache management page:
  - cache stats: hit rate, miss rate, size, entry count, eviction rate
  - cache configuration: TTL, max size, eviction policy
  - cache inspection: view cached entries, search by prompt
  - cache invalidation: clear all, clear by model, clear by pattern
  - cache cost savings attribution
- [ ] Add semantic cache tuning:
  - similarity threshold configuration
  - embedding model selection
  - cache warmup from historical requests
  - cache preview: "would this request hit cache?"

### Acceptance Criteria

- [ ] Customers can register, monitor, and govern agents from a single UI
- [ ] Workflow runs show step-by-step execution with cost/latency per step
- [ ] API playground allows model comparison without writing code
- [ ] Tag management enables flexible cost attribution beyond workspace boundaries
- [ ] Tool policies provide fine-grained control over agent tool usage
- [ ] Response cache is manageable and its savings are measurable
- [ ] All new features integrate with existing RunLedger cost tracking and RBAC

---

## Developer Brief In Plain English

Build an AI Operations Dashboard that helps customers understand how AI is being used, where money is going, why RunLedger made each routing decision, and how RunLedger is reducing cost.

Do not build a dashboard with random charts. Build screens that answer questions.

Every chart should answer one question:

- Where is my money going?
- Which models are expensive?
- Which teams use AI the most?
- Which agents generate the highest cost?
- How much money did RunLedger save?
- Why was this request routed to Claude instead of GPT?
- What should I optimize next?

If a chart does not answer a business or engineering question, do not build it.

The first page should be executive-friendly. The user should understand spend, savings, requests, latency, ROI, and top usage drivers in under 30 seconds.

The second major experience should be the AI Request Flow Sankey. This is the centerpiece. It should show:

```text
User Request -> Intent -> Skill -> Agent -> Model -> Tool -> Result
```

The engineering experience should allow a user to drill from the executive view all the way down to a single request trace.

RunLedger should become the system that answers:

- What happened?
- Why did it happen?
- What did it cost?
- How can it be optimized?

---

## Launch Readiness - Release, Docs, Market, And Demo Assets

### Goal

Prepare RunLedger for credible external release, GitHub discovery, investor conversations, competitive positioning, and polished demos.

### Release Cuts And Versioning

- [ ] Define release strategy:
  - alpha
  - beta
  - release candidate
  - stable
  - long-term support later
- [ ] Define semantic versioning policy:
  - `MAJOR.MINOR.PATCH`
  - breaking API changes bump major
  - new features bump minor
  - bug fixes bump patch
- [ ] Add release checklist:
  - migrations tested
  - API tests passing
  - web typecheck/build passing
  - Docker images rebuilt
  - seed/demo data validated
  - docs updated
  - changelog updated
  - known issues listed
- [ ] Add `CHANGELOG.md`.
- [ ] Add GitHub release notes template.
- [ ] Add version display in app footer/settings/about page.
- [ ] Add API version header or `/version` endpoint.
- [ ] Add image tagging convention:
  - `runledger-api:v0.x.y`
  - `runledger-web:v0.x.y`
  - `runledger-worker:v0.x.y`
  - `runledger-mcp:v0.x.y`
- [ ] Add release branch convention:
  - `release/v0.x`
  - `hotfix/v0.x.y`
- [ ] Add release smoke-test script.

### GitHub Documentation

- [ ] Rewrite root `README.md` for external GitHub audience.
- [ ] Add product screenshots and architecture diagrams.
- [ ] Add quickstart:
  - local Docker Compose
  - login credentials
  - first org/workspace
  - first API key
  - first Gateway request
  - first OTLP trace
  - first MCP connection
- [ ] Add docs for:
  - RBAC model
  - organizations
  - workspaces
  - users
  - API keys
  - Gateway
  - MCP
  - OTLP
  - integrations
  - backups and restore
  - email/SMTP
  - data capture
  - compliance
  - dashboards
  - simulations and labs
- [ ] Add `docs/architecture.md`.
- [ ] Add `docs/security.md`.
- [ ] Add `docs/roadmap.md`.
- [ ] Add `docs/contributing-local-dev.md`.
- [ ] Add `docs/demo-runbook.md`.
- [ ] Add GitHub issue templates:
  - bug report
  - feature request
  - integration request
  - documentation request
- [ ] Add GitHub PR template:
  - summary
  - tests
  - screenshots
  - migration notes
  - docs impact
- [ ] Add badges:
  - build
  - tests
  - license
  - Docker
  - docs

### Competitive Landscape Analysis

- [ ] Create `docs/competitive-landscape.md`.
- [ ] Compare RunLedger against:
  - LangSmith
  - Helicone
  - LiteLLM Enterprise
  - Portkey
  - Arize Phoenix
  - Langfuse
  - Datadog LLM Observability
  - New Relic AI Monitoring
  - Grafana/Tempo/OpenTelemetry DIY
  - Cloud provider usage dashboards
- [ ] Analyze categories:
  - LLM observability
  - FinOps
  - model gateway/control plane
  - prompt/version governance
  - agent/tool tracing
  - MCP governance
  - enterprise RBAC
  - compliance/data capture
  - optimization recommendations
  - backup/restore and operational readiness
- [ ] Identify RunLedger differentiators:
  - AI Operations Intelligence positioning
  - flow of intelligence from prompt to outcome
  - FinOps plus routing plus governance
  - MCP and agent control plane
  - platform/org/workspace RBAC
  - demo/lab-driven product experience
- [ ] Add positioning table:
  - competitor
  - strengths
  - gaps
  - RunLedger angle
  - risk level
- [ ] Add pricing/packaging notes where public information is available.
- [ ] Add "why now" market narrative.

### Investor Pitch Deck

- [ ] Create investor pitch deck.
- [ ] Suggested sections:
  - Title
  - Problem
  - Why now
  - Market
  - Product
  - Demo screenshots
  - Differentiation
  - Competitive landscape
  - Business model
  - Go-to-market
  - Traction or demo milestones
  - Roadmap
  - Team
  - Ask
- [ ] Core message:
  - Enterprises are adopting AI agents faster than they can govern, observe, and optimize them.
  - RunLedger becomes the AI Operations Intelligence layer across models, agents, tools, teams, and spend.
- [ ] Include visuals:
  - AI request flow Sankey
  - executive savings dashboard
  - integration hub
  - agent dependency graph
  - optimization simulator
- [ ] Add metrics to highlight:
  - monthly AI spend
  - savings
  - ROI
  - requests processed
  - cache hit rate
  - routing savings
  - token reduction
  - number of integrations
- [ ] Export formats:
  - PPTX
  - PDF
  - Markdown source

### Demo Presentation Deck

- [ ] Create feature demo deck.
- [ ] Suggested sections:
  - What RunLedger is
  - Product vision
  - Roles and access model
  - Organization/workspace setup
  - API keys and Gateway
  - MCP and agent integrations
  - OTLP and OpenInference ingestion
  - Alert Rules
  - Budgets and FinOps
  - Dashboards
  - Sankey request flow
  - Request explorer
  - Optimization recommendations
  - Email reports
  - Backup and restore
  - Compliance and data capture
  - Simulations/labs
  - LocalAIAgentStack integration demo
  - Roadmap
- [ ] Add demo script:
  - create org
  - create workspace
  - create API key
  - send first Gateway request
  - show request in Runs
  - show cost in dashboard
  - trigger alert
  - send email report
  - show MCP integration
  - show optimization recommendation
  - show backup/restore plan
- [ ] Add screenshots from local stack once visual rebrand is complete.
- [ ] Export formats:
  - PPTX
  - PDF
  - Markdown source

### Acceptance Criteria

- [ ] RunLedger has a clear versioning and release process.
- [ ] GitHub docs are strong enough for a new developer to run the product locally.
- [ ] Competitive analysis clearly explains where RunLedger wins and where it must improve.
- [ ] Investor deck tells a credible market/product/business story.
- [ ] Demo deck can be used to walk through the product in 10-15 minutes.
