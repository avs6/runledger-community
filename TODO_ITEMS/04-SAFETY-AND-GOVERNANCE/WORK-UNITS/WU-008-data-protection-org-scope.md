# WU-008: Data Protection Org & Access Scope

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - C (Data Protection)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Data capture, Security, Tags
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Data capture | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Data capture | Org: Onboarding | 04×01 | PARTIAL | STRONG |
| Safety: Data capture | Org: Users | 04×01 | PARTIAL | STRONG |
| Safety: Data capture | Org: Workspaces | 04×01 | PARTIAL | STRONG |
| Safety: Data capture | Org: Access groups | 04×01 | PARTIAL | STRONG |
| Safety: Data capture | Org: API keys | 04×01 | PARTIAL | STRONG |
| Safety: Data capture | Org: MCP registry | 04×01 | PARTIAL | STRONG |
| Safety: Security | Org: Onboarding | 04×01 | PARTIAL | STRONG |
| Safety: Security | Org: Users | 04×01 | PARTIAL | STRONG |
| Safety: Security | Org: Access groups | 04×01 | PARTIAL | STRONG |
| Safety: Security | Org: API keys | 04×01 | PARTIAL | STRONG |
| Safety: Security | Org: MCP registry | 04×01 | PARTIAL | STRONG |
| Safety: Security | Org: AI hub | 04×01 | PARTIAL | STRONG |
| Safety: Tags | Org: Organization profile | 04×01 | PARTIAL | STRONG |
| Safety: Tags | Org: Onboarding | 04×01 | PARTIAL | STRONG |
| Safety: Tags | Org: Workspaces | 04×01 | PARTIAL | STRONG |
| Safety: Tags | Org: MCP registry | 04×01 | PARTIAL | STRONG |
| Safety: Tags | Org: AI hub | 04×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Data capture/Security/Tags × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Data capture/Security/Tags
- `FEATURE-STATUS.md` — 04-C × 01 counts

## Scope

- **Backend**: Data capture should carry richer org identity: user and access-group scope on capture overrides, API-key attribution on capture events, MCP registry capture context. Security should deepen access-group, API-key, and MCP/AI-hub scope awareness. Tags should show org-level and workspace-level taxonomy posture with MCP and AI hub classification.
- **UI**: Data capture overrides should show scope hierarchy (org, workspace, access group). Security should show access-group and API-key posture. Tags should show org-level posture and AI hub/MCP classification links. Onboarding should surface data protection posture status.
- **Docs**: Document scope-aware data protection workflows.
- **Postman**: Add org identity context to data protection endpoints.
- **Scripts/Examples**: Add example managing data capture, security, and tags across org scopes.

## Acceptance Criteria

1. Data capture overrides show full scope hierarchy
2. Security shows access-group and API-key posture
3. Tags show org and workspace taxonomy posture
4. AI hub and MCP registry show data protection classification
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
