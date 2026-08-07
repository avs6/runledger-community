# Demo Script

This is the default RunLedger Community demo script for a 10 to 15 minute product walkthrough.

Baseline context: Friday, August 7, 2026, release `v1alpha1`.

## Goal

Show that RunLedger is not just telemetry storage. It is a self-hosted control plane for AI cost, policy, routing, and operational insight.

## Pre-demo prep

- Use `Reset Demo Data`
- Use `Seed Demo Data` with `Full Simulator`
- Wait until the demo task is marked `completed`
- Keep these pages ready:
  - `Dashboard`
  - `Request Flow`
  - `Cost & Savings`
  - `Optimization Opportunities`
  - `Gateway`
  - `Approvals`
  - `MCP`

Supporting materials:

- [Demo runbook](./demo-runbook.md)
- [Demo asset bundle](./demo-asset-bundle.md)
- [Guided demo scenarios](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/guided_demo_scenarios.md)

## Opening

Say:

"RunLedger is the self-hosted AI operations control plane. It helps teams understand what their AI systems are doing, what they cost, whether the activity was allowed, whether it worked, and what to optimize next."

## Step 1: Open with the executive view

Open `Dashboard`.

Say:

"We start at the top with the operating picture: spend, requests, performance, and signs of optimization across the environment."

Show:

- spend and request activity
- visible optimization or savings indicators
- enough seeded data to feel like a real multi-team environment

## Step 2: Move from symptom to cause

Open `Request Flow`, then `Request Explorer` if needed.

Say:

"When something spikes, the next question is why. RunLedger lets us move from the high-level symptom to the exact request path, route, model, tool, and outcome."

Show:

- a route or feature with visible cost or latency pressure
- request-level evidence for how traffic flowed

## Step 3: Prove optimization

Open `Cost & Savings`, then `Optimization Opportunities`.

Say:

"This is where the product becomes more than observability. Savings are attached to actual optimization behavior such as caching, routing, and prompt changes."

Show:

- savings categories
- realized savings trend
- one recommendation with a clear tradeoff story

## Step 4: Show the runtime control plane

Open `Gateway`.

Say:

"If the AI layer is changing quickly, teams need a central place to adjust routing, runtime policy, and optimization behavior without redeploying every app."

Show:

- route aliases
- cache or routing evidence
- runtime controls or per-route policy surfaces

## Step 5: Show governance

Open `Approvals`, then `MCP` if time allows.

Say:

"AI cost and AI risk eventually become governance questions. RunLedger keeps budgets, approvals, and tool controls in the same product as the telemetry and routing decisions."

Show:

- approved and denied actions
- MCP or tool-governance surfaces
- evidence that this is a control plane, not just a dashboard

## Close

Say:

"The key idea is that RunLedger unifies observability, optimization, and governance for AI workloads in one self-hosted system."

## Optional alternate closes

- Executive close: "This gives finance and platform teams a shared system of record for AI spend and AI control."
- Engineering close: "You can go from a chart to the exact request path without leaving the product."
- Platform close: "You can tune routes, budgets, and approvals centrally while keeping teams isolated."

## If something looks sparse

- fall back to `Runs`, `Gateway`, or `Approvals`
- reseed instead of troubleshooting state manually
- use the screenshot set in [demo-asset-bundle.md](./demo-asset-bundle.md) for async sharing if live pages are not ideal
