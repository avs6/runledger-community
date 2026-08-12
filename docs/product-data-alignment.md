# RunLedger Product And Data Alignment

This document is the Phase 0 contract for RunLedger dashboards, analytics APIs, and demo data. It defines the product questions, scopes, dimensions, metrics, and chart intent before new UI or backend work is added.

RunLedger should not become a collection of charts. Every surface should answer a clear business or engineering question.

## Product Promise

RunLedger is an AI Operations Intelligence platform.

It helps customers answer:

- Where is AI money going?
- Why is it being spent?
- Which requests, agents, models, tools, teams, and routes drive cost?
- What did RunLedger optimize?
- What should we optimize next?

The product should connect usage, cost, routing, business impact, and savings into one explainable flow.

## Dashboard Scopes

| Scope | Primary user | Primary job | Data boundary | Typical route |
|---|---|---|---|---|
| Platform | Platform Admin | Operate the full RunLedger installation across organizations | All organizations and workspaces | `/dashboard` global/platform views, `/organizations`, platform Settings |
| Organization | Org Admin | Understand and manage one organization's AI estate across workspaces | One organization and all its workspaces | `/organization`, `/organization/dashboard`, `/request-flow?scope=org` |
| Workspace | Workspace Admin | Manage and optimize one team's traffic, budgets, runs, and keys | One workspace | `/dashboard`, `/runs`, `/request-flow?scope=workspace` |
| Member | Member/read-only | Inspect runs, sessions, analytics, prompts, and monitoring without changing controls | Assigned workspaces only | read-only workspace views |

Scope rules:

- Platform scope requires `is_platform_admin=true`.
- Org scope requires Platform Admin or tenant role `org_admin` / `org_manager`.
- Workspace scope requires access to the active workspace through the current session/API key.
- Member views must hide create, edit, delete, and control-plane actions unless `canWrite` is true.
- Cross-scope aggregate APIs must not return prompt or response payloads by default.

## Core Dimensions

These dimensions should be used consistently across APIs, filters, charts, exports, seeded scenarios, and integration metadata.

| Dimension | Meaning | Source examples | Filter key |
|---|---|---|---|
| Organization | Customer/account boundary | tenant | `tenant_id` |
| Workspace | Team/application boundary inside an org | workspace, API key | `workspace_id` |
| Team | Internal department or cost owner | metadata `team`, `department`, `cost_center` | `team` |
| Application | Product/service emitting traffic | application table, metadata `application`, `service.name` | `application` |
| User | End user, service user, or agent user | `end_user_id` | `end_user_id` |
| Agent | Runtime or agent client executing work | metadata `agent_name`, `agent_client`, agent span | `agent` |
| Skill | Reusable procedure or skill injected into a task | metadata `skill`, `skill_name`, `runledger.skill` | `skill` |
| Intent | Task category or feature | `feature_tag`, metadata `intent`, `task.intent` | `feature_tag` |
| Model | Provider model used | provider call model, Gateway `model_used` | `model` |
| Provider | OpenAI, Anthropic, Google, Ollama, etc. | provider call provider, model inference | `provider` |
| Tool | Tool/MCP/function called by an agent | tool call, tool span | `tool` |
| Route | Gateway alias or routing path | Gateway route alias, `model_requested` | `route` |
| Outcome | Business or quality result | outcome events, status fallback | `outcome_type`, `success` |
| Time range | Analysis window | run start, provider call time, event time | `from`, `to`, preset |
| Cost center | Billing owner | metadata `cost_center`, team mapping | `cost_center` |

## Core Metrics

| Metric | Definition | Primary use |
|---|---|---|
| Requests | Count of runs or Gateway requests, depending on surface | Volume, flow thickness, adoption |
| Input tokens | Prompt/context tokens sent to model | Context growth, cache opportunity |
| Output tokens | Generated tokens returned from model | Reasoning/workload intensity |
| Total tokens | Input plus output tokens | Utilization trend |
| Cost | Priced USD cost from provider calls/runs | FinOps, chargeback |
| Savings | Estimated avoided cost from cache, routing, compression, local models, etc. | ROI and optimization proof |
| Latency | Run duration or provider/Gateway latency | Performance and UX |
| Error rate | Failed requests divided by total requests | Reliability |
| Retry rate | Retry count divided by total requests | Waste and stability |
| Cache hit rate | Cache hits divided by eligible requests | Optimization health |
| Rejected requests | Requests blocked by policy, budget, PII, or route health | Governance impact |
| Token reduction | Tokens avoided by compression/compiler/cache | Efficiency |
| Cost reduction | Cost avoided versus baseline/projected spend | Executive ROI |
| Quality score | Human/evaluator score, normalized 0 to 1 when possible | Quality guardrail |
| Outcome rate | Successful outcomes divided by total outcomes | Business impact |

Metric rules:

- Dashboards should show the unit and denominator for every rate.
- Cost and savings must always state whether they are actual, estimated, projected, or simulated.
- Latency should prefer provider/Gateway latency for routing charts and run duration for request lifecycle charts.
- If a metric is unavailable, show an explicit empty state instead of silently treating missing data as zero.

## Optimization Categories

| Category | What it means | Evidence to show |
|---|---|---|
| Prompt compression | Prompt/context reduced before model call | Tokens before/after, cost saved, quality guardrail |
| Cache hits | Exact or semantic cache returned an answer | Cache hit count, avoided model call, latency saved |
| Smart model routing | Request moved to cheaper/faster/better model based on policy | Requested model, selected model, decision reason |
| Local model routing | Work routed to Ollama/vLLM/self-hosted model | Provider/model, local cost basis, latency/quality |
| Duplicate request detection | Repeated or equivalent work avoided | Duplicate count, avoided cost |
| Tool optimization | Tool catalog/output reduced or filtered | Tools before/after, relevant tools kept, tokens saved |
| Reasoning avoidance | Expensive reasoning model avoided for simple work | Intent, selected tier, quality result |
| Provider fallback | Request succeeded after provider/route failure | Failed provider, fallback provider, final status |
| Batch/retry reduction | Fewer retries or batched calls reduced waste | Retry count, error reduction, cost saved |

## Chart-To-Question Map

Every planned chart should map to one clear question.

| Screen / chart | Product question | Scope | Primary dimensions | Primary metrics |
|---|---|---|---|---|
| Executive Summary KPI row | Are we spending less while serving more useful AI traffic? | Platform, Org, Workspace | org, workspace, time range | spend, savings, ROI, requests, latency, cache hit rate |
| Stacked Resource Usage Timeline | What models and traffic types make up usage over time? | Platform, Org, Workspace | model, provider, cache/rejected status, time | input tokens, output tokens, requests, cost |
| AI Request Flow Sankey | Where did every request go? | Platform, Org, Workspace | intent, skill, agent, model, tool, route, outcome | requests, cost, tokens, savings |
| Intent Distribution | What work are people asking AI to do? | Org, Workspace | user, team, intent, model | requests, cost, outcome rate |
| Model Usage | Which models are used, and what do they cost/perform like? | Platform, Org, Workspace | model, provider, route | requests, tokens, cost, latency, quality |
| Cost Breakdown | Where is every dollar attributable? | Platform, Org, Workspace | team, application, user, agent, model | cost, cost per request |
| Savings Attribution | Why did RunLedger save money? | Platform, Org, Workspace | optimization category, route, model | savings, token reduction, cost reduction |
| Optimization Opportunities | What should we improve next? | Org, Workspace | team, intent, route, model, agent | projected savings, confidence, quality risk |
| Monthly Trend | Are spend and efficiency improving month over month? | Platform, Org, Workspace | time range, model, optimization category | projected spend, actual spend, optimized spend |
| ROI Table | Which teams or workflows produce business value? | Org, Workspace | team, workflow, outcome | spend, saved, value, ROI |
| Request Explorer | Why did this exact request cost what it did? | Workspace, selected run | run, span, model, tool, route | prompt metadata, tokens, cost, latency, outcome |
| Agent Dependency Graph | Which agents/tools depend on each other? | Workspace | agent, tool, span, route | latency, error rate, cost per tool |
| Prompt Quality Funnel | Where does quality degrade? | Workspace | prompt, intent, model, outcome | valid/routed/cached/answered/accepted/thumbs-up |
| Cost Heatmap | Which teams burn tokens at which times? | Org, Workspace | team, weekday/hour, model | cost, tokens, request count |
| Cost Waterfall | What reduced original spend to final spend? | Platform, Org | optimization category | original spend, deltas, final spend |

## Analytics API Contract Guidelines

Dashboard APIs should follow these rules:

- Accept standard filters where applicable: `scope`, `tenant_id`, `workspace_id`, `from`, `to`, `team`, `application`, `end_user_id`, `agent`, `skill`, `feature_tag`, `model`, `provider`, `tool`, `route`, `outcome_type`, `success`, `cost_center`.
- Return the applied scope and generated timestamp in aggregate responses.
- Return `total` and `sampled` counts when a response is limited or sampled.
- Avoid payload data in aggregate APIs. Payloads belong in request-level views and remain governed by data capture settings.
- Include stable drilldown keys so a chart can link to Request Explorer, Runs, Sessions, or Analytics.
- Use strings for decimal money values in API responses to avoid floating point drift.
- Keep missing data explicit with labels like `Unknown`, `Uncaptured`, `Direct SDK / OTLP`, or `No tool called`.

Existing aligned contracts:

- `GET /runs/flow` returns safe request-flow records for Workspace, Org, and Platform Sankey views.
- `GET /runs` returns workspace-scoped run lists and supports common run filters.
- `GET /runs/{run_id}` returns request-level detail and payloads only when capture policy allows it.
- `GET /org/dashboard` returns org-level dashboard aggregates.

## Dashboard Acceptance Checklist

Before adding a new dashboard or chart, confirm:

- The chart answers one product question from this document.
- The chart has a defined scope and role boundary.
- The chart uses standard dimensions and metrics.
- The chart has a drilldown path.
- The chart has an honest empty state.
- The chart labels estimated/projected/simulated values clearly.
- The backend API avoids payload leakage for aggregate views.

## Phase 0 Completion Definition

Phase 0 is complete when:

- Dashboard scopes are defined.
- Core product questions are documented.
- Standard dimensions are documented.
- Standard metrics are documented.
- Standard optimization categories are documented.
- Every planned chart maps to a product question.
- Scope rules for Platform Admin, Org Admin, Workspace Admin, and Member are explicit.
- API contract guidance exists for future dashboard work.
