# Safety & Governance — Cohesion Matrix

Last updated: PENDING AUDIT

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
| Safety & Governance | Tool registry | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Tool Registry is already central to MCP and runtime policy, but financial and identity posture can deepen further. |
| Safety & Governance | Tool policies | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Tool Policies already align strongly with MCP and workspace control, and should deepen with richer scope awareness. |
| Safety & Governance | Approvals | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Approvals should connect much more strongly to budget overrides, model access, and scope governance. |
| Safety & Governance | Data capture | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Data Capture is well-scoped operationally, but still reads as a separate policy island in places. |
| Safety & Governance | Security | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Security is already well-rooted in org/workspace scope and should remain one of the stronger governance blocks. |
| Safety & Governance | Alert rules | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | Alert Rules is already a good operations bridge and should connect more clearly to budget and policy conditions. |
| Safety & Governance | Audit log | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Audit Log is a strong evidence layer, but upstream surfaces should link into it more explicitly. |
| Safety & Governance | Governance pack | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | Governance Pack is strongest as evidence closure and should keep consuming the rest of the suite cleanly. |
| Safety & Governance | Tags | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | Tags are strategically important because they can become a shared scoping and attribution layer across the suite. |

### 11.6b Safety & Governance x Gateway & Routing / Observe / Self

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Runs list | Run detail | Request flow | Request explorer | Monitoring | Tool registry | Tool policies | Approvals | Security | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|-----------|------------|--------------|------------------|------------|---------------|---------------|-----------|----------|-----------|-----------------|------|---------|
| Safety & Governance | Tool registry | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Tool Registry is already a major runtime-governance anchor and should stay tightly coupled to gateway control. |
| Safety & Governance | Tool policies | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Tool Policies is already one of the strongest cross-feature governance surfaces. |
| Safety & Governance | Approvals | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Approvals is operationally real, but it still needs stronger suite-wide adoption as a first-class exception path. |
| Safety & Governance | Data capture | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Data capture should continue converging with runtime and evidence flows rather than staying privacy-only. |
| Safety & Governance | Security | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Security is already a strong operational and runtime bridge, especially with monitoring and gateway posture. |
| Safety & Governance | Alert rules | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Alert Rules already tie runtime and monitoring together and should keep growing as the action layer. |
| Safety & Governance | Audit log | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Audit Log is one of the clearest evidence backbones in the suite. |
| Safety & Governance | Governance pack | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Governance Pack is strongest when it is clearly downstream of evidence and policy surfaces rather than competing with them. |
| Safety & Governance | Tags | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | Tags is a cross-cutting primitive and should continue to grow as a shared classification layer. |

