# WU-004: Tool Governance Org & Access Scope

- **Status**: COMPLETED
- **Bundle**: 04-Safety - A (Tool Governance)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Tool registry, Tool policies
- **Created**: 2026-08-14
- **Completed**: 2026-08-26

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tool registry | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: Onboarding | 04×01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: Users | 04×01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: Workspaces | 04×01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: Access groups | 04×01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: API keys | 04×01 | PARTIAL | STRONG |
| Safety: Tool registry | Org: AI hub | 04×01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: Onboarding | 04×01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: Users | 04×01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: Workspaces | 04×01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: Access groups | 04×01 | PARTIAL | STRONG |
| Safety: Tool policies | Org: API keys | 04×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Tool registry/policies × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Tool registry/policies
- `FEATURE-STATUS.md` — 04-A × 01 counts

## Scope

- **Backend**: Tool registry and tool policies should carry richer org identity context: workspace-aware registry entries, access-group-scoped policy resolution, API-key attribution on tool invocations, user attribution on policy changes. Org profile should show tool governance posture. AI hub should show tool policy applicability.
- **UI**: Tool registry should show workspace scope and access-group context. Tool policies should show scope resolution (org, workspace, access group). Policy changes should show user attribution. AI hub should link to applicable tool policies.
- **Docs**: Document scope-aware tool governance workflows.
- **Postman**: Add org identity context to tool registry and policy endpoints.
- **Scripts/Examples**: Add example managing tool policies across workspace and access-group scopes.

## Acceptance Criteria

1. Tool registry entries show workspace and access-group context
2. Tool policies show scope resolution hierarchy
3. Policy changes carry user attribution
4. AI hub links to applicable tool policies
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
