# Gateway & Routing — Cohesion Matrix

Last updated: PENDING AUDIT

This file tracks how Gateway & Routing features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

Current row major feature under audit: `Gateway & Routing`

### 11.4 Gateway & Routing Cohesion Matrix

This section applies the same matrix structure to `Gateway & Routing` against the rest of the shipped feature surface.

Current row major feature under audit: `Gateway & Routing`

### 11.4a Gateway & Routing x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| Gateway & Routing | Provider profiles | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Friday, August 14, 2026 pass added backend budget posture, scoped budget links, and scoped budget creation from provider profiles, but richer billing and override cohesion is still open. |
| Gateway & Routing | Model gateway | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Friday, August 14, 2026 pass improved the Gateway-to-Budgets operator bridge, but deeper embedded budget context and downstream FinOps cohesion are still not strong enough to close the matrix. |
| Gateway & Routing | Guardrails | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Guardrails is only indirectly tied to FinOps today. |
| Gateway & Routing | Response cache | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Cache economics matter, but the product does not yet surface that relationship richly enough. |
| Gateway & Routing | Rate limits | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | Rate limits and quota controls are related to spend but still not modeled as one cohesive operator flow. |

### 11.4b Gateway & Routing x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| Gateway & Routing | Provider profiles | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | Provider profiles are already close to AI hub and workspace ownership, but can still connect more clearly to org-level access decisions. |
| Gateway & Routing | Model gateway | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Gateway control plane already intersects strongly with workspaces, API keys, and AI hub. |
| Gateway & Routing | Guardrails | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | Guardrails already connect meaningfully to access groups and should keep deepening there. |
| Gateway & Routing | Response cache | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Response cache is now intentionally a gateway-owned subfeature, not a separate access surface. |
| Gateway & Routing | Rate limits | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Rate limits already intersect strongly with API keys and should connect more clearly to scope ownership. |

### 11.4c Gateway & Routing x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-----------------|------------------|-----------------|------------------------|-------------|------------|---------|
| Gateway & Routing | Provider profiles | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | Provider profiles and model-usage surfaces already have a strong natural cohesion. |
| Gateway & Routing | Model gateway | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Gateway and Observe already form one of the strongest runtime-to-investigation stories in the suite. |
| Gateway & Routing | Guardrails | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | Guardrail impacts should become easier to follow in the request-analysis flow. |
| Gateway & Routing | Response cache | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | Cache behavior matters to performance and economics, but the observability story is still moderate. |
| Gateway & Routing | Rate limits | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | Rate-limit behavior should become easier to inspect alongside live request and monitoring data. |

### 11.4d Gateway & Routing x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| Gateway & Routing | Provider profiles | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | Provider access and deprecation controls should become more explicitly policy-aware. |
| Gateway & Routing | Model gateway | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Model gateway is already central to runtime governance and should remain so. |
| Gateway & Routing | Guardrails | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Guardrails is already one of the strongest bridges between runtime enforcement and governance surfaces. |
| Gateway & Routing | Response cache | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | Cache should remain subordinate to gateway policy and auditability rather than becoming an isolated feature. |
| Gateway & Routing | Rate limits | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Throttling and quota behaviors belong close to policy, alerting, and security posture. |

### 11.4e Gateway & Routing x Build & Improve / Platform / Self

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | All organizations | Platform settings | Plugins | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|-------------------|-------------------|---------|-------------------|---------------|------------|----------------|-------------|---------|
| Gateway & Routing | Provider profiles | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Provider profiles already tie together model operations well, but platform and improvement links can still get tighter. |
| Gateway & Routing | Model gateway | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Gateway is already central to execution and optimization, and should remain the canonical runtime control-plane owner. |
| Gateway & Routing | Guardrails | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Guardrails is internally cohesive and increasingly well tied to the broader runtime path. |
| Gateway & Routing | Response cache | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | Response cache now belongs inside gateway, and its strongest cohesion is with simulation and runtime optimization. |
| Gateway & Routing | Rate limits | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | Rate limits is now correctly collapsed into gateway, but its relationships to platform operations and optimization can still deepen. |

