# Sales Engineering Walkthrough

This is the fastest polished RunLedger story for prospects, partners, or internal
stakeholders who want to understand the product in one pass.

Target duration: 12 to 20 minutes.

Recommended date context for any recorded or shared demo: Friday, August 7, 2026.

## Audience

- Economic buyer: wants visibility, savings, and governance.
- Platform owner: wants routing, policy, and integration control.
- Engineering lead: wants request-level debugging and replayable evidence.

## Demo Promise

By the end of the walkthrough, the audience should believe three things:

1. RunLedger sees every important AI request surface.
2. RunLedger can actively reduce spend and risk.
3. RunLedger still gives engineers enough depth to debug decisions and outcomes.

## Pre-Demo Checklist

- Run `Seed Demo Data` with the `Full Simulator` profile.
- Wait for the status to show `completed`.
- Keep these tabs ready:
  - `Dashboard`
  - `Request Flow`
  - `Cost & Savings`
  - `Optimization Opportunities`
  - `Gateway`
  - `Approvals`
  - `MCP`
  - `Runbooks`
- Keep [guided_demo_scenarios.md](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/guided_demo_scenarios.md) open for recovery prompts.

## Demo Arc

### 1. Start With The Business Problem

Open `Dashboard`.

Talk track:
"Most teams can tell you they are using AI. Far fewer can tell you which requests drove spend, what was optimized, and where they need controls. RunLedger is the control room for that layer."

Show:

- top-level spend and request metrics
- signs of optimization or savings
- enough activity to feel like a real enterprise footprint

### 2. Move From Symptom To Cause

Open `Request Flow`, then `Request Explorer`.

Talk track:
"If finance or reliability sees a spike, the next question is always why. Here we move from aggregate trend to the exact request path, model, route, tool, and outcome."

Show:

- one route or feature with visible cost or latency pressure
- the run-level trail through prompt, route, model, tool, and outcome

### 3. Prove Optimization, Not Just Observability

Open `Cost & Savings`, then `Optimization Opportunities`.

Talk track:
"This is where RunLedger stops being a dashboard and starts being an optimization system. Savings are not guessed. They are attached to actual routing, cache, and prompt decisions."

Show:

- savings categories
- realized savings over time
- a recommendation tied to cost and quality tradeoffs

### 4. Show The Gateway Control Plane

Open `Gateway`.

Talk track:
"Operations teams need one place to enforce routing, fallbacks, and optimization policy without redeploying every app."

Show:

- a few route aliases
- request or routing decisions
- evidence of cache, compiler, or routing behavior

### 5. Show Governance And Human Control

Open `Approvals`, then `Runbooks`.

Talk track:
"AI spend and tool access eventually require policy. RunLedger keeps the control in-product, with approval records and runbooks instead of side-channel spreadsheets."

Show:

- approved and denied requests
- any budget or tool-oriented approval examples
- runbook evidence for operator workflows

### 6. Finish With MCP And Tool Governance

Open `MCP` or `MCP Server Registry`.

Talk track:
"The same system that understands model spend can also govern agent tools and MCP servers. That matters as teams move from chatbots to agents."

Show:

- MCP server registration
- workspace permissions
- tool filtering or policy surfaces

## Suggested Closes

Pick one depending on the audience:

- Executive close: "You can show ROI and risk posture without asking engineering to build a custom reporting layer."
- Platform close: "You can change routing, budgets, and approvals centrally while keeping each team isolated."
- Engineering close: "You still get request-level evidence when something goes wrong."

## Recovery Paths

If a page looks sparse or a metric is taking time to populate:

- fall back to `Runs` or `Request Explorer`
- use the seeded `Approvals`, `MCP`, or `Gateway` pages, which populate immediately
- reseed instead of troubleshooting ad hoc state during the demo

## Post-Demo Follow-Up Assets

Pair this walkthrough with:

- [demo-runbook.md](C:/Users/Abi/Desktop/github/runledger-community/docs/demo-runbook.md)
- [guided_demo_scenarios.md](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/guided_demo_scenarios.md)
- [demo-visual-regression.md](C:/Users/Abi/Desktop/github/runledger-community/docs/demo-visual-regression.md)
