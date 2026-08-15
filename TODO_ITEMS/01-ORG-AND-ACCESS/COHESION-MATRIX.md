# Organization & Access — Cohesion Matrix

Last updated: PENDING AUDIT

This file tracks how Organization & Access features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

Current row major feature under audit: `Organization & Access`

### 11.3 Organization & Access Cohesion Matrix

This section applies the same matrix structure to `Organization & Access` against the rest of the shipped feature surface.

Current row major feature under audit: `Organization & Access`

### 11.3a Organization & Access x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| Organization & Access | Organization profile | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Org profile should consume spend posture and budget posture, but it should not become a second FinOps control plane. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only; no separate long-term cohesion target. |
| Organization & Access | Onboarding | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Onboarding should eventually help operators discover budgets and billing setup, but it is not the operating surface itself. |
| Organization & Access | Users | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | User identity should connect more clearly to spend accountability and attribution. |
| Organization & Access | Workspaces | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Workspaces are already the strongest real join between Org & Access and FinOps. |
| Organization & Access | Access groups | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Access groups should become first-class financial scopes and currently are not. |
| Organization & Access | API keys | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | API keys already carry runtime identity but are not yet treated as first-class budget owners. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Telemetry should reinforce financial attribution by org scope, but the relationship is still indirect. |
| Organization & Access | MCP registry | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | MCP lifecycle is mostly orthogonal to FinOps today. |
| Organization & Access | AI hub | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | AI hub needs clearer ties to provider cost posture, model budgets, and downstream financial ownership. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3b Organization & Access x Gateway & Routing

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------|
| Organization & Access | Organization profile | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | The org console should summarize runtime posture without duplicating gateway control-plane ownership. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | Onboarding is the right discovery surface for connecting to gateway capabilities, but not for long-term management. |
| Organization & Access | Users | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | User identity and role posture should connect more clearly to runtime and provider access. |
| Organization & Access | Workspaces | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Workspaces are already the canonical runtime boundary and should remain so. |
| Organization & Access | Access groups | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | Access groups are becoming a meaningful governance and runtime scoping primitive, but the gateway path can deepen further. |
| Organization & Access | API keys | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | API keys already bridge deeply into gateway and quota controls, making this one of the strongest cross-feature relationships. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Telemetry has a meaningful relationship to runtime ownership, but not much direct configuration linkage. |
| Organization & Access | MCP registry | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | MCP should increasingly inherit org/workspace/access context more explicitly across live execution. |
| Organization & Access | AI hub | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | AI hub, provider profiles, and gateway ownership should read as one cohesive model-access story. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3c Organization & Access x Observe

| Row Major Feature | Row Subfeature | Workspace dashboard | Analytics overview | Runs list | Run detail | Sessions list | Session detail | Request flow | Request flow focus | Request explorer | Model usage | Analytics economics | Cost and savings | Billing summary | Outcomes and ROI | Analytics users | Analytics user detail | Engineering | Monitoring | Finding |
|-------------------|----------------|---------------------|--------------------|-----------|------------|---------------|----------------|--------------|--------------------|------------------|-------------|---------------------|------------------|-----------------|------------------|-----------------|------------------------|-------------|------------|---------|
| Organization & Access | Organization profile | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Org profile should summarize cross-workspace activity, but analytics remains the proper investigative owner. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | Onboarding should explain where operators go next, but not own the operational observability loop. |
| Organization & Access | Users | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | User analytics already provides the clearest observability counterpart to user management. |
| Organization & Access | Workspaces | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Observe is already heavily workspace-scoped, making this one of the strongest suite-level cohesion stories. |
| Organization & Access | Access groups | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Observability does not yet expose access-group scope strongly enough for investigation and chargeback-style use cases. |
| Organization & Access | API keys | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | API-key identity is present in places, but it is not yet a first-class investigation dimension across Observe. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | Telemetry is correctly inside Observe now, but should keep inheriting org/workspace scope more consistently. |
| Organization & Access | MCP registry | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | MCP activity should become easier to inspect through the broader observability layer over time. |
| Organization & Access | AI hub | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | AI hub and model-usage surfaces already form a natural cross-feature story. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3d Organization & Access x Safety & Governance

| Row Major Feature | Row Subfeature | MCP servers | Search tools | Tool registry | Tool policies | Policy dry run | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Finding |
|-------------------|----------------|-------------|--------------|---------------|---------------|----------------|-----------|--------------|----------|-------------|-----------|-----------------|------|---------|
| Organization & Access | Organization profile | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Org profile should summarize governance posture, but the governance features should keep their own control planes. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | Onboarding is the right place for discovery and setup guidance across governance features. |
| Organization & Access | Users | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | Users should connect more clearly to approval, security, and audit workflows. |
| Organization & Access | Workspaces | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Workspaces are already a core scope primitive for many governance features. |
| Organization & Access | Access groups | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | Access groups and tags/guardrails are moving toward a meaningful governance-scoping story that can deepen further. |
| Organization & Access | API keys | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | API keys should be better integrated into approvals, data capture, and runtime policy evidence. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Telemetry should increasingly participate in security, alerting, and evidence workflows. |
| Organization & Access | MCP registry | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | MCP registry already sits near the center of the tool-governance story. |
| Organization & Access | AI hub | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | AI hub needs clearer ties to approval and evidence flows around model access and deprecation. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3e Organization & Access x Build & Improve

| Row Major Feature | Row Subfeature | Playground | Prompts list | Prompt detail and versions | Agents list | Agent detail | Agent memory | Workflows list | Workflow detail | Workflow run detail | Datasets | Evaluation studio | Experiments | Replay lab | Replay experiment detail | Optimization opportunities | Optimization simulator | Model scorecards | Vector stores list | Vector store detail | Runbooks | Finding |
|-------------------|----------------|------------|--------------|----------------------------|-------------|--------------|--------------|----------------|-----------------|---------------------|----------|-------------------|-------------|------------|--------------------------|----------------------------|------------------------|------------------|--------------------|---------------------|----------|---------|
| Organization & Access | Organization profile | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Org scope should eventually shape build surfaces more consistently, but today the relationship is mostly indirect. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Onboarding is the natural front door into the build surfaces and should stay that way. |
| Organization & Access | Users | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | Builder identity and ownership should flow more clearly from users into build and experimentation areas. |
| Organization & Access | Workspaces | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Workspaces are already the clearest cohesion backbone for Build & Improve. |
| Organization & Access | Access groups | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | Access groups should show up much more explicitly as execution and experimentation scope in build surfaces. |
| Organization & Access | API keys | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | API-key identity matters in execution and evaluation, but the UI does not yet reflect that coherently. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Telemetry | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Telemetry should increasingly feed replay, experiments, and optimization. |
| Organization & Access | MCP registry | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | MCP should eventually feel more native inside the build workflow rather than adjacent to it. |
| Organization & Access | AI hub | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | AI hub is already naturally close to prompts, workflows, and model scorecards, but the full story can tighten more. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

### 11.3f Organization & Access x Platform / Utility / Self

| Row Major Feature | Row Subfeature | All organizations | Platform settings | Plugins | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|-------------------|-------------------|---------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| Organization & Access | Organization profile | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Organization profile is the core admin anchor, but it should remain a coordinator rather than absorbing every org feature directly. |
| Organization & Access | Org settings | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Legacy redirect only. |
| Organization & Access | Onboarding | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Onboarding should stay the guided entry point into the whole organization surface. |
| Organization & Access | Users | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Users is a strong managed entity, but should connect more visibly to workspaces, access groups, and keys as one identity story. |
| Organization & Access | Workspaces | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Workspaces are the most cohesive non-legacy feature inside this family. |
| Organization & Access | Access groups | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | Access groups are strategically important but still not as deeply threaded through the suite as workspaces. |
| Organization & Access | API keys | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | API keys are strong operationally, but the cross-feature story is still split between org and gateway surfaces. |
| Organization & Access | Integrations | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Collapsed legacy surface; coherence is now defined by Onboarding. |
| Organization & Access | Telemetry | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | Telemetry is intentionally adjacent rather than central in this family. |
| Organization & Access | MCP registry | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | MCP registry is cohesive, but its relationship to the rest of Org & Access can still be tightened. |
| Organization & Access | AI hub | `PENDING` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | AI hub is cohesive as a workspace model-catalog surface, but it still needs clearer bridges into the broader org-admin flow. |
| Organization & Access | Projects | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |
| Organization & Access | Team models | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | Retired legacy surface. |

