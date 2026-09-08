# Governance

Controls that make the runtime path safe, reviewable, and finance-aware.

## Gateway Guardrails

Use the gateway to enforce:

- Fallback routes
- Per-route cost caps
- Per-user rate limits
- PII redaction

Drive traffic through the configured alias and verify the gateway request log shows
the resulting decision.

## Tool Registry

Register a few tools and confirm the policy outcome changes:

- `search_kb` → allow
- `lookup_order` → audit
- `refund_customer` → block and enforce

## Approvals

Create a `budget_increase` request with a reason such as:

`Black Friday traffic - raise HomeLab AgentTest daily cap to $50`

Approve or deny it and verify the status transition.

## Auto-Approval Policies

Create a low-risk auto-approval rule for small budget increases and compare how
small versus large requests behave.

## Chargeback & Showback

Map feature tags to cost centers and verify the resulting finance view.

## Runbooks

Generate a runbook from an expensive or failed run and review the resulting operator
summary.

## Model Scorecards

Compare cost, latency, and quality across active models.

## Policy Dry Run

Simulate a routing or budget policy before enforcing it.

## Governance Audit Pack

Export the audit pack and confirm policies, approvals, budgets, and tool events are
included.

## Data Capture & PII

Set a global capture mode, add a scoped override for a specific API key or route,
edit that override, then delete it and confirm the global policy takes effect again.
Run the PII sandbox with a sample email and SSN to verify the redacted output.

## Enterprise Security

Create an OIDC provider, edit its audience or active flag, and save. Add an IP ACL
rule, simulate an allowed and denied address, then update the rule priority or CIDR.

## Tags & Auto-Tagging

Create a tag hierarchy such as `workflow=support`, `channel=chat`, `tenant=homelab`.
Add an auto-tagging rule that matches prompt content, simulate it against a sample
payload, edit the rule, and retire one tag to confirm the taxonomy and rule lifecycle.

---

Next: [Operations](./operations.md)
