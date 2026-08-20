# WU-021: MCP Registry Runtime Governance and Observe Refresh

- **Status**: NOT_STARTED
- **Bundle**: 01-Org & Access - Bundle C (Onboarding and Connected Setup)
- **Target**: 01-ORG-AND-ACCESS/MCP registry (`/mcp-registry`)
- **Created**: 2026-08-16
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: MCP registry | FinOps: Chargeback | 01x05 | PARTIAL | STRONG |
| Org: MCP registry | Gateway: Provider profiles | 01x02 | PARTIAL | STRONG |
| Org: MCP registry | Gateway: Model gateway | 01x02 | PARTIAL | STRONG |
| Org: MCP registry | Gateway: Guardrails | 01x02 | PARTIAL | STRONG |
| Org: MCP registry | Observe: Analytics overview | 01x03 | PARTIAL | STRONG |
| Org: MCP registry | Observe: Runs list | 01x03 | PARTIAL | STRONG |
| Org: MCP registry | Observe: Run detail | 01x03 | PARTIAL | STRONG |
| Org: MCP registry | Observe: Request flow | 01x03 | PARTIAL | STRONG |
| Org: MCP registry | Observe: Request explorer | 01x03 | PARTIAL | STRONG |
| Org: MCP registry | Safety: Approvals | 01x04 | PARTIAL | STRONG |
| Org: MCP registry | Safety: Security | 01x04 | PARTIAL | STRONG |
| Org: MCP registry | Safety: Audit log | 01x04 | PARTIAL | STRONG |
| Org: MCP registry | Safety: Governance pack | 01x04 | PARTIAL | STRONG |
| Org: MCP registry | Build: Agents list | 01x06 | PARTIAL | STRONG |
| Org: MCP registry | Build: Agent detail | 01x06 | PARTIAL | STRONG |
| Org: MCP registry | Build: Workflows list | 01x06 | PARTIAL | STRONG |
| Org: MCP registry | Build: Workflow detail | 01x06 | PARTIAL | STRONG |
| Org: MCP registry | Build: Evaluation studio | 01x06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — MCP registry row
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — MCP registry cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of MCP registry
- `03-OBSERVE/COHESION-MATRIX.md` — their view of MCP registry
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of MCP registry
- `05-FINOPS/COHESION-MATRIX.md` — their view of MCP registry
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of MCP registry
- `01-ORG-AND-ACCESS/DELIVERY-STATUS.md` — 2.6 if delivery changes

## Scope

- **Backend**: Strengthen MCP tool-call attribution, runtime evidence, approval hooks, and build-surface consumption.
- **UI**: Make MCP registry feel like a real runtime/build/governance surface rather than an isolated admin registry.
- **Docs**: Clarify MCP as part of runtime, governance, and builder workflows.
- **Postman**: Add missing MCP registry request coverage.
- **Scripts/Examples**: Expand MCP flows to include runtime execution, evidence, and build-tool use.

## Acceptance Criteria

1. MCP registry participates clearly in runtime execution, investigation, governance evidence, and build flows.
2. Operators can trace registered MCP capabilities into the surfaces that consume them.
3. All listed cohesion cells are updated to target state.
4. All paired feature files are updated.
5. FEATURE-STATUS.md dashboard is updated.
