# WU-006: Exception Workflows Org & Access Scope

- **Status**: COMPLETED
- **Bundle**: 04-Safety - B (Exception Workflows)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Approvals, Alert rules
- **Created**: 2026-08-14
- **Completed**: 2026-08-27

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Approvals | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Approvals | Org: Onboarding | 04×01 | PARTIAL | STRONG |
| Safety: Approvals | Org: Users | 04×01 | PARTIAL | STRONG |
| Safety: Approvals | Org: Workspaces | 04×01 | PARTIAL | STRONG |
| Safety: Approvals | Org: Access groups | 04×01 | PARTIAL | STRONG |
| Safety: Approvals | Org: API keys | 04×01 | PARTIAL | STRONG |
| Safety: Approvals | Org: MCP registry | 04×01 | PARTIAL | STRONG |
| Safety: Approvals | Org: AI hub | 04×01 | PARTIAL | STRONG |
| Safety: Alert rules | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Alert rules | Org: Onboarding | 04×01 | PARTIAL | STRONG |
| Safety: Alert rules | Org: Workspaces | 04×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Approvals/Alert rules × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Approvals/Alert rules
- `FEATURE-STATUS.md` — 04-B × 01 counts

## Scope

- **Backend**: Approvals should carry richer org identity context: user and access-group scope on approval requests, workspace-scoped approval policies, API-key context for automated approvals, MCP registry and AI hub as approval-triggering domains. Alert rules should express org identity: org-level and workspace-level alert scoping.
- **UI**: Approvals queue should show requester identity (user, access group, API key) with links. Approval policies should show workspace scope. Alert rules should show workspace and org scope. AI hub and MCP registry should link to relevant approval paths.
- **Docs**: Document scope-aware approval and alert workflows.
- **Postman**: Add org identity context to approval and alert rule endpoints.
- **Scripts/Examples**: Add example creating workspace-scoped approval policies and org-level alert rules.

## Acceptance Criteria

1. Approvals show user, access-group, and API-key identity context
2. Approval policies support workspace scoping
3. Alert rules express org and workspace scope
4. AI hub and MCP registry link to approval paths
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
