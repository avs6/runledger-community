# WU-007: Identity & Scope Visibility in Build & Improve

- **Status**: NOT_STARTED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/Access groups, API keys (`/access-groups`, `/api-keys`)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Access groups | Build: Agents list | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Agent detail | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Workflows list | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Workflow detail | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Workflow run detail | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Evaluation studio | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Experiments | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Replay lab | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Replay experiment detail | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Optimization opportunities | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Optimization simulator | 01×06 | PARTIAL | STRONG |
| Org: Access groups | Build: Playground | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Workflows list | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Workflow detail | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Workflow run detail | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Evaluation studio | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Experiments | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Replay lab | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Replay experiment detail | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Optimization opportunities | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Optimization simulator | 01×06 | PARTIAL | STRONG |
| Org: API keys | Build: Model scorecards | 01×06 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Access groups/API keys × Build cells
- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — their view of Access groups/API keys
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — Access groups, API keys rows
- `FEATURE-STATUS.md` — 01-B × 06 counts

## Scope

- **Backend**: Build surfaces (agents, workflows, evaluations, experiments, replay, optimization) should accept access-group and API-key as scope/filter dimensions. Execution results should carry API-key identity. Access-group membership should gate or filter builder-facing surfaces.
- **UI**: Build surfaces should expose access-group and API-key filters/facets. Access group and API key detail pages should show linked build activity.
- **Docs**: Document how access groups and API keys shape the build and experimentation workflow.
- **Postman**: Add access-group and API-key filters to agent, workflow, evaluation, and experiment endpoints.
- **Scripts/Examples**: Add example running a workflow scoped to an access group and viewing results by API key.

## Acceptance Criteria

1. Agents, workflows, evaluations, and experiments can filter by access group
2. Workflow runs and replay results carry API-key identity
3. Optimization surfaces recognize access-group and API-key scope
4. Playground recognizes access-group context
5. Identity detail pages link to their build activity footprint
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
