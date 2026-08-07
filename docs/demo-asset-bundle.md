# Demo Asset Bundle

This page collects the reusable artifacts for demos, screenshots, and storytelling.

Use it as the single entrypoint when you need to prepare a local walkthrough, internal review, or prospect-facing product tour.

Current bundle baseline: Friday, August 7, 2026, aligned to release `v1alpha1`.

## What's in the bundle

- [Demo runbook](./demo-runbook.md)
- [Demo script](./demo-script.md)
- [Demo visual regression](./demo-visual-regression.md)
- [Guided demo scenarios](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/guided_demo_scenarios.md)
- [Sales engineering walkthrough](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/sales_engineering_walkthrough.md)

## Core screenshots

These screenshots already exist in the docs bundle and are the recommended storytelling set.

| Asset | File | Best use |
|---|---|---|
| Dashboard overview | `/images/dashboard.png` | Executive opening, KPI density, "AI control room" framing |
| Run explorer | `/images/runs.png` | Request-level drilldown and engineering depth |
| Analytics | `/images/analytics.png` | Spend trends, top drivers, and finance storytelling |
| Gateway | `/images/gateway.png` | Routing, cache, and runtime controls |
| Outcomes | `/images/outcomes.png` | ROI and business-impact proof |
| Evaluations | `/images/evaluation.png` | Quality and regression management |
| Prompts | `/images/prompts.png` | Prompt registry and release governance |
| Approvals | `/images/approvals.png` | Human control and governance |
| Users/RBAC | `/images/users.png` | Multi-tenant administration and scoped access |
| Organization | `/images/organization.png` | Org/workspace setup context |
| Settings | `/images/settings.png` | Platform controls, retention, compliance, email |

## Screenshot gallery

<Frame caption="Dashboard — the recommended opening screenshot for product and investor storytelling.">
  <img src="/images/dashboard.png" alt="RunLedger dashboard overview" />
</Frame>

<Frame caption="Gateway — the control-plane view for routes, request decisions, and runtime policy.">
  <img src="/images/gateway.png" alt="RunLedger gateway page" />
</Frame>

<Frame caption="Approvals — a clean governance screenshot for budget, tool, and policy review workflows.">
  <img src="/images/approvals.png" alt="RunLedger approvals page" />
</Frame>

<Frame caption="Analytics — spend, trends, and optimization storytelling for finance and operations audiences.">
  <img src="/images/analytics.png" alt="RunLedger analytics page" />
</Frame>

## Recommended package for a 10 to 15 minute demo

Use this set together:

1. `dashboard.png`
2. `gateway.png`
3. `analytics.png`
4. `outcomes.png`
5. `approvals.png`

Pair those visuals with:

- [Demo script](./demo-script.md)
- [Demo runbook](./demo-runbook.md)
- [Sales engineering walkthrough](C:/Users/Abi/Desktop/github/runledger-community/scripts/scenarios/labs/sales_engineering_walkthrough.md)

## Replay guidance

To keep screenshots and talking points aligned:

1. Reset demo data.
2. Seed `Full Simulator`.
3. Wait for seeded analytics and control-plane data to settle.
4. Capture only the fixtures in [demo-visual-regression.md](./demo-visual-regression.md) when refreshing assets.

## Notes

- These assets are designed for local replayable demos without live customer data.
- If a page changes materially, update this bundle and the visual regression fixture manifest in the same change.
