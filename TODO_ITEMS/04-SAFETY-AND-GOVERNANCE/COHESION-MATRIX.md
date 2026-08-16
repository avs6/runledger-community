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
| Safety & Governance | Tool registry | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tool Registry is already central to MCP and runtime policy, but financial and identity posture can deepen further. Onboarding is also a real guide-level relationship because operators should be oriented to where tool governance lives even if they do not configure it on day one. |
| Safety & Governance | Tool policies | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Tool Policies already align strongly with MCP and workspace control, and should deepen with richer scope awareness. Onboarding has a light but real relationship because setup guidance should explain where runtime policy is configured. |
| Safety & Governance | Approvals | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Approvals should connect much more strongly to budget overrides, model access, scope governance, and financially material exception handling. |
| Safety & Governance | Data capture | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Data Capture is well-scoped operationally, but still reads as a separate policy island in places. |
| Safety & Governance | Security | `N/A` | `N/A` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Security is already well-rooted in org/workspace scope and should remain one of the stronger governance blocks. Onboarding also has a real setup relationship because secure delivery and access posture should be introduced early. |
| Safety & Governance | Alert rules | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | `PARTIAL` | `N/A` | Alert Rules is already a good operations bridge and should connect more clearly to budget and policy conditions. |
| Safety & Governance | Audit log | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Audit Log is a strong evidence layer, but upstream surfaces should link into it more explicitly. |
| Safety & Governance | Governance pack | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `N/A` | Governance Pack is strongest as evidence closure and should keep consuming the rest of the suite cleanly. |
| Safety & Governance | Tags | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Tags are strategically important because they can become a shared scoping and attribution layer across the suite. |

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
