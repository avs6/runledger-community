# Safety & Governance â€” Cohesion Matrix

Last updated: 2026-08-15

This file tracks how Safety & Governance features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

Current row major feature under audit: `Safety & Governance`

### 11.6 Safety & Governance Cohesion Matrix

This section applies the same matrix structure to `Safety & Governance` against the rest of the shipped feature surface.

Current row major feature under audit: `Safety & Governance`

### 11.6a Safety & Governance x FinOps / Organization & Access

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Chargeback | Ledger | Organization profile | Onboarding | Users | Workspaces | Access groups | API keys | MCP registry | AI hub | Finding |
|-------------------|----------------|---------|---------------|------------|--------|----------------------|------------|-------|------------|---------------|----------|--------------|--------|---------|
| Safety & Governance | Tool registry | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Onboarding now includes has_search_tool readiness check with set-up-now link to Tools page. |
| Safety & Governance | Tool policies | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | Onboarding now includes has_tool_policy readiness check with set-up-now link to Tool Policies page. Policy dry run is implicitly covered by having an active policy. |
| Safety & Governance | Approvals | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | Onboarding now includes has_approval_config readiness check with set-up-now link to Approvals page. |
| Safety & Governance | Data capture | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | Onboarding now includes has_data_capture readiness check with set-up-now link to Data Capture page. |
| Safety & Governance | Security | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | Onboarding now includes has_security_config readiness check with set-up-now link to Security page. |
| Safety & Governance | Alert rules | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | API key detail now links to governance. Alert rules support API-key-scoped budget alerts. |
| Safety & Governance | Audit log | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | Audit log now filters by actor_user_id, access_group_id, and api_key_prefix. Identity detail pages link to filtered audit views. Export also supports identity filters. |
| Safety & Governance | Governance pack | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | Governance pack now accepts user_id, access_group_id, api_key_id to scope all evidence sections. Identity detail pages link to scoped governance pack. |
| Safety & Governance | Tags | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Onboarding now includes has_tag readiness check with set-up-now link to Tags page. |

### 11.6b Safety & Governance x Gateway & Routing / Observe / Self

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Runs list | Run detail | Request flow | Request explorer | Monitoring | Tool registry | Tool policies | Approvals | Security | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|-----------|------------|--------------|------------------|------------|---------------|---------------|-----------|----------|-----------|-----------------|------|---------|
| Safety & Governance | Tool registry | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails is one of the strongest governance-side companions to Tool Registry because runtime tool execution can be filtered and blocked alongside broader guardrail enforcement. |
| Safety & Governance | Tool policies | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tool Policies and Guardrails intersect directly in runtime governance because tool calls flow through shared enforcement and evidence paths. |
| Safety & Governance | Approvals | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails does not depend on formal approval workflows, but approval-style review is a plausible escalation path for some high-risk runtime policies. |
| Safety & Governance | Data capture | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Guardrails records rich runtime event metadata and violations evidence, making Data Capture a real but still not fully unified relationship. |
| Safety & Governance | Security | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails is one of the strongest security-adjacent runtime controls because it actively blocks, modifies, and monitors unsafe traffic. |
| Safety & Governance | Alert rules | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails has a direct alert workflow with evaluation and acknowledgement, making Alert Rules one of its strongest governance relationships. |
| Safety & Governance | Audit log | `PARTIAL` | `PARTIAL` | `STRONG` | `GAP` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails emits real audit events for rule, filter, and partner mutations and also preserves runtime event evidence, making Audit Log one of its strongest governance relationships. |
| Safety & Governance | Governance pack | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails is clearly governance-relevant, but Governance Pack still does not appear to consume guardrail posture as richly as the dedicated Guardrails surface does. |
| Safety & Governance | Tags | `STRONG` | `PARTIAL` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Guardrails does not currently expose first-class tag behavior the way other governance primitives do, so Tags is not a meaningful direct relationship here. |
