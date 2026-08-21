# WU-013: Org & Access Internal Cohesion Tightening

- **Status**: DONE
- **Bundle**: 01-Org & Access - A/B/C/D (cross-bundle)
- **Target**: 01-ORG-AND-ACCESS (internal family cohesion)
- **Created**: 2026-08-14
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Organization profile | Org: Org settings | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Org: Onboarding | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Org: Users | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Org: Access groups | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Org: API keys | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Org: Telemetry | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Org: MCP registry | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Org: AI hub | 01×01 | PARTIAL | STRONG |
| Org: Organization profile | Platform: Platform settings | 01×07 | PARTIAL | STRONG |
| Org: Onboarding | Platform: All organizations | 01×07 | PARTIAL | STRONG |
| Org: Onboarding | Platform: Platform settings | 01×07 | PARTIAL | STRONG |
| Org: Onboarding | Org: Users | 01×01 | PARTIAL | STRONG |
| Org: Onboarding | Org: Workspaces | 01×01 | PARTIAL | STRONG |
| Org: Onboarding | Org: Access groups | 01×01 | PARTIAL | STRONG |
| Org: Onboarding | Org: API keys | 01×01 | PARTIAL | STRONG |
| Org: Onboarding | Org: Telemetry | 01×01 | PARTIAL | STRONG |
| Org: Onboarding | Org: MCP registry | 01×01 | PARTIAL | STRONG |
| Org: Onboarding | Org: AI hub | 01×01 | PARTIAL | STRONG |
| Org: Users | Org: Workspaces | 01×01 | PARTIAL | STRONG |
| Org: Users | Org: Access groups | 01×01 | PARTIAL | STRONG |
| Org: Users | Org: API keys | 01×01 | PARTIAL | STRONG |
| Org: Users | Platform: All organizations | 01×07 | PARTIAL | STRONG |
| Org: Users | Platform: Platform settings | 01×07 | PARTIAL | STRONG |
| Org: Workspaces | Org: Access groups | 01×01 | PARTIAL | STRONG |
| Org: Workspaces | Org: API keys | 01×01 | PARTIAL | STRONG |
| Org: Workspaces | Org: Telemetry | 01×01 | PARTIAL | STRONG |
| Org: Workspaces | Org: MCP registry | 01×01 | PARTIAL | STRONG |
| Org: Workspaces | Org: AI hub | 01×01 | PARTIAL | STRONG |
| Org: Workspaces | Platform: All organizations | 01×07 | PARTIAL | STRONG |
| Org: Workspaces | Platform: Platform settings | 01×07 | PARTIAL | STRONG |
| Org: Access groups | Org: MCP registry | 01×01 | PARTIAL | STRONG |
| Org: Access groups | Platform: All organizations | 01×07 | PARTIAL | STRONG |
| Org: Access groups | Platform: Platform settings | 01×07 | PARTIAL | STRONG |
| Org: API keys | Org: AI hub | 01×01 | PARTIAL | STRONG |
| Org: API keys | Platform: All organizations | 01×07 | PARTIAL | STRONG |
| Org: API keys | Platform: Platform settings | 01×07 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — internal (self) cells and Platform cells
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of Org & Access
- `FEATURE-STATUS.md` — 01-A/B/C/D × 01 and 01 × 07 counts

## Scope

- **Backend**: Strengthen internal cross-linking: org profile should link cleanly to all identity/scope/setup surfaces, onboarding should guide into all org features, users should link to workspaces/groups/keys, workspaces should link to groups/keys/telemetry/MCP/AI hub. Platform surfaces should show org-level summaries.
- **UI**: Org profile should be the admin hub linking to all sub-features. Onboarding should guide into every org feature. Identity surfaces should cross-link each other. Platform admin should see per-org posture.
- **Docs**: Document the org family as one cohesive system with clear handoffs.
- **Postman**: Ensure cross-linking endpoints are discoverable.
- **Scripts/Examples**: Add example walking through the full org setup lifecycle.

## Acceptance Criteria

1. Org profile links clearly to every active sub-feature (users, workspaces, access groups, API keys, onboarding, MCP, AI hub, telemetry)
2. Onboarding guides setup across all org features
3. Identity surfaces (users/workspaces/groups/keys) cross-link each other
4. Platform admin surfaces show per-org posture
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
