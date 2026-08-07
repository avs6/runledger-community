# Guided Demo Scenarios

Use these guided scenarios after running either `Full Simulator` or `Quick Seed`.
They are designed to tell a clean before/after story without requiring live customer
data or external model credentials.

Recommended setup on Friday, August 7, 2026:

1. Use `Reset Demo Data` from the dashboard, or run `python -m scripts.demo_mode reset`.
2. Use `Seed Demo Data` with the `Full Simulator` profile for the richest story.
3. Open the dashboard in this order:
   - `Dashboard`
   - `Request Flow`
   - `Cost & Savings`
   - `Optimization Opportunities`
   - `Gateway`
   - `Approvals`
   - `MCP`

## Scenario 1: Cache Optimization

Goal: show a latency and cost win from repeated traffic.

- Story setup: start on `Gateway` and filter requests to the `semantic-cache` or `exact-cache` feature tags.
- Before: point out uncached requests with higher model cost and latency.
- After: show cached requests with lower cost, faster completion, and a cache-related savings category.
- Best proof pages:
  - `Gateway -> Requests`
  - `Cost & Savings`
  - `Optimization Opportunities`
- What to say: "RunLedger is not only logging traffic. It is actively removing repeated spend."

## Scenario 2: Model-Routing Savings

Goal: show that cheap requests stay cheap while complex requests escalate safely.

- Story setup: open `Request Flow` or `Engineering` and isolate runs from routing-heavy traffic.
- Before: show the mixed request set and explain that not every prompt needs the frontier model.
- After: open `Gateway` or `Cost & Savings` and highlight cheaper routed runs plus realized savings.
- Best proof pages:
  - `Request Flow`
  - `Cost & Savings`
  - `Gateway`
- What to say: "Routing is policy-driven, measurable, and reversible. Finance sees savings, engineering sees the exact request path."

## Scenario 3: Prompt Compression

Goal: show token reduction without changing the application.

- Story setup: open `Optimization Opportunities` and the `compiled-chat` or compression-oriented traffic.
- Before: explain that long prompts inflate token cost and latency.
- After: show compression or compiler savings in the run/request detail and savings surfaces.
- Best proof pages:
  - `Optimization Opportunities`
  - `Request Explorer`
  - `Cost & Savings`
- What to say: "Prompt optimization is treated like an observable optimization event, not magic."

## Scenario 4: Local-Model Summarization

Goal: show a practical local-first workflow with priced Ollama traffic.

- Story setup: focus on summarization-oriented runs from seeded support, finance, or ops traffic.
- Before: explain that many summary tasks do not need a hosted frontier model.
- After: show local-model usage in the model mix and cost trend while still preserving outcomes.
- Best proof pages:
  - `Model Usage`
  - `Cost & Savings`
  - `Runs`
- What to say: "RunLedger prices local inference too, so teams can see the real economics of on-prem AI."

## Scenario 5: Bad-Route Latency And Cost Spike

Goal: show the dashboard as an investigation tool, not just a scorecard.

- Story setup: use one of the noisier seeded routes or route aliases with higher latency and error mix.
- Before: open the top-level dashboard and point out spend, latency, or error changes.
- After: pivot into `Request Flow`, `Request Explorer`, and `Gateway` to identify the route or model causing the spike.
- Best proof pages:
  - `Dashboard`
  - `Request Flow`
  - `Request Explorer`
  - `Gateway`
- What to say: "You can move from executive symptom to request-level cause in a few clicks."

## Scenario 6: Budget Alert Stops A Runaway Agent Loop

Goal: show that budgets are active controls, not passive reporting.

- Story setup: open `Budgets`, `Alert Rules`, and `Approvals`.
- Before: explain the risk of autonomous agents creating unbounded spend.
- After: show seeded budget thresholds, alert firings, and approval workflows connected to budget pressure.
- Best proof pages:
  - `Budgets`
  - `Alert Rules`
  - `Approvals`
  - `Runbooks`
- What to say: "RunLedger can force human involvement before agent spend turns into an incident."

## Scenario 7: MCP Tool Filtering

Goal: show that tool catalogs can be narrowed to the minimum relevant set.

- Story setup: open `MCP`, `MCP Registry`, and `Optimization Opportunities`.
- Before: explain that large tool catalogs increase tokens, risk, and agent confusion.
- After: show seeded MCP permissions, tool filtering examples, and governance around blocked or allowed tools.
- Best proof pages:
  - `MCP`
  - `MCP Server Registry`
  - `Approvals`
  - `Optimization Opportunities`
- What to say: "The same control plane that watches model cost can also govern and slim down tool use."

## Suggested Demo Sequence

Use this order when you only have 10 to 15 minutes:

1. Scenario 5 for the hook: an executive symptom and a technical root-cause drilldown.
2. Scenario 2 to prove measurable model-routing savings.
3. Scenario 1 or 3 to prove optimization beyond routing.
4. Scenario 6 to show governance and budget controls.
5. Scenario 7 to show MCP and tool-governance differentiation.

## Reset And Replay

- `Full Simulator` already resets before seeding.
- `Quick Seed` now also resets before seeding.
- Manual labs remain intentionally separate. Use them when you want operator training instead of a polished narrative.
- If a demo goes sideways, reset and reseed rather than trying to repair state manually.
