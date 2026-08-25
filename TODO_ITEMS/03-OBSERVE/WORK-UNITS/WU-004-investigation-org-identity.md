# WU-004: Investigation Org Identity & Scope Strengthening

- **Status**: COMPLETED
- **Bundle**: 03-Observe - B (Investigation)
- **Target**: 03-OBSERVE/Runs, Run detail, Request flow, Request explorer, Sessions
- **Created**: 2026-08-14
- **Completed**: 2026-08-24

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Runs list | Org: Organization profile | 03×01 | PARTIAL | STRONG |
| Observe: Runs list | Org: Users | 03×01 | PARTIAL | STRONG |
| Observe: Runs list | Org: API keys | 03×01 | PARTIAL | STRONG |
| Observe: Runs list | Org: Telemetry | 03×01 | PARTIAL | STRONG |
| Observe: Runs list | Org: MCP registry | 03×01 | PARTIAL | STRONG |
| Observe: Run detail | Org: Organization profile | 03×01 | PARTIAL | STRONG |
| Observe: Run detail | Org: Users | 03×01 | PARTIAL | STRONG |
| Observe: Run detail | Org: API keys | 03×01 | PARTIAL | STRONG |
| Observe: Run detail | Org: Telemetry | 03×01 | PARTIAL | STRONG |
| Observe: Run detail | Org: MCP registry | 03×01 | PARTIAL | STRONG |
| Observe: Request flow | Org: Organization profile | 03×01 | PARTIAL | STRONG |
| Observe: Request flow | Org: Users | 03×01 | PARTIAL | STRONG |
| Observe: Request flow | Org: API keys | 03×01 | PARTIAL | STRONG |
| Observe: Request flow | Org: Telemetry | 03×01 | PARTIAL | STRONG |
| Observe: Request flow | Org: MCP registry | 03×01 | PARTIAL | STRONG |
| Observe: Request explorer | Org: Organization profile | 03×01 | PARTIAL | STRONG |
| Observe: Request explorer | Org: Users | 03×01 | PARTIAL | STRONG |
| Observe: Request explorer | Org: API keys | 03×01 | PARTIAL | STRONG |
| Observe: Request explorer | Org: Telemetry | 03×01 | PARTIAL | STRONG |
| Observe: Request explorer | Org: MCP registry | 03×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Investigation × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Investigation features
- `FEATURE-STATUS.md` — 03-B × 01 counts

## Scope

- **Backend**: Investigation surfaces should carry richer org identity context: user identity on runs, API-key identity on requests, org profile context for cross-workspace investigation, telemetry and MCP registry correlation for runtime events.
- **UI**: Runs and request detail should show user and API-key provenance. Request flow and explorer should filter by user and API key. Investigation surfaces should link to org profile for cross-workspace views. MCP and telemetry context should be visible on relevant runs.
- **Docs**: Document identity-aware investigation workflows.
- **Postman**: Add user, API-key, and org context to investigation endpoints.
- **Scripts/Examples**: Add example investigating runs by user and API key with org context.

## Acceptance Criteria

1. Runs and run detail show user and API-key provenance
2. Request flow and explorer filter by user and API key
3. Cross-workspace investigation links to org profile
4. MCP and telemetry context visible on relevant runs
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
