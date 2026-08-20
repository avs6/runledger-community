# WU-012: Tool Registry Runtime FinOps Scope Refresh

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - A (Tool Governance Control Plane)
- **Target**: 04-SAFETY-AND-GOVERNANCE/tool-registry
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tool registry | FinOps: Budgets | 04x05 | PARTIAL | STRONG |
| Safety: Tool registry | FinOps: Budget detail | 04x05 | PARTIAL | STRONG |
| Safety: Tool registry | Org: Workspaces | 04x01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: API keys | 04x01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: MCP registry | 04x01 | PARTIAL | STRONG |
| Safety: Tool registry | Gateway: Model gateway | 04x02 | PARTIAL | STRONG |
| Safety: Tool registry | Gateway: Response cache | 04x02 | PARTIAL | STRONG |
| Safety: Tool registry | Gateway: Rate limits | 04x02 | PARTIAL | STRONG |
| Safety: Tool registry | Observe: Run detail | 04x03 | PARTIAL | STRONG |
| Safety: Tool registry | Observe: Request flow | 04x03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/GAP-MATRIX.md` - Tool registry row
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - Tool registry cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - workspace, API key, and MCP registry view
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - model gateway, cache, and rate-limit view
- `03-OBSERVE/COHESION-MATRIX.md` - run detail and request-analysis view
- `05-FINOPS/COHESION-MATRIX.md` - budget linkage view

## Scope

- **Backend**: Clarify how tool registry ownership propagates into runtime routing decisions, scoped access, and spend-sensitive tool enablement.
- **UI**: Show clearer registry linkage into workspace scope, API key posture, runtime controls, and downstream request evidence.
- **Docs**: Document Tool Registry as a cross-suite governance owner rather than an isolated admin list.
- **Postman**: Keep registry and linked-governance request flows aligned with real runtime and scope behavior.
- **Scripts/Examples**: Add a scenario that traces a registered tool from setup through runtime usage, cost impact, and evidence review.

## Acceptance Criteria

1. Tool Registry is re-audited against runtime, scope, and FinOps expectations
2. Registry relationships to workspaces, API keys, and MCP registry are explicit
3. Registry relationships to gateway controls and request evidence are explicit
4. All listed cohesion cells move to the target state
5. FEATURE-STATUS.md is updated
