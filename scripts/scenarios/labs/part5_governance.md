# Part 5 - Governance and Control

*Prerequisite: Part 1 completed.*

This section covers the controls that make the runtime path safe, reviewable, and
finance-aware.

## 5.1 - Gateway guardrails

Use the gateway to enforce:

- fallback routes
- per-route cost caps
- per-user rate limits
- PII redaction

Drive traffic through the configured alias and verify the gateway request log shows
the resulting decision.

## 5.2 - Tool registry

Register a few tools and confirm the policy outcome changes:

- `search_kb` -> allow
- `lookup_order` -> audit
- `refund_customer` -> block and enforce

## 5.3 - Approvals

Create a `budget_increase` request with a reason such as:

`Black Friday traffic - raise HomeLab AgentTest daily cap to $50`

Approve or deny it and verify the status transition.

## 5.4 - Auto-approval policies

Create a low-risk auto-approval rule for small budget increases and compare how
small versus large requests behave.

## 5.5 - Chargeback and showback

Map feature tags to cost centers and verify the resulting finance view.

## 5.6 - Runbooks

Generate a runbook from an expensive or failed run and review the resulting operator
summary.

## 5.7 - Model scorecards

Compare cost, latency, and quality across active models.

## 5.8 - Policy dry run

Simulate a routing or budget policy before enforcing it.

## 5.9 - Governance audit pack

Export the audit pack and confirm policies, approvals, budgets, and tool events are
included.

## 5.10 - Data capture policy studio

Set a global capture mode, add a scoped override for a specific API key or route,
edit that override in place, then delete it and confirm the global policy takes
effect again. Run the PII sandbox with a sample email and SSN to verify the
redacted output.

## 5.11 - Enterprise security

Create an OIDC provider, edit its audience or active flag, and save it in place.
Add an IP ACL rule, simulate an allowed and denied address, then update the rule
priority or CIDR to confirm the security console is managing the real backend
contract rather than a decorative form.

## 5.12 - Tags and auto-tagging

Create a small tag hierarchy such as `workflow=support`, `channel=chat`, and
`tenant=homelab`. Then add an auto-tagging rule that matches prompt content,
simulate it against a sample payload, edit the rule, and finally retire one tag to
confirm the taxonomy lifecycle and rule lifecycle are both working end to end.

Next: [Part 6 - Operations](./part6_operations.md)
