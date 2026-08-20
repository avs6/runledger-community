# WU-005: Model Gateway & Guardrails Org Scope Tightening

- **Status**: NOT_STARTED
- **Bundle**: 02-Gateway & Routing - A/B (Provider & Routing, Runtime Protection)
- **Target**: 02-GATEWAY-AND-ROUTING/Model gateway, Guardrails (`/gateway`, `/guardrails`)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Model gateway | Org: Organization profile | 02×01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: Onboarding | 02×01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: Users | 02×01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: Access groups | 02×01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: Telemetry | 02×01 | PARTIAL | STRONG |
| Gateway: Model gateway | Org: MCP registry | 02×01 | PARTIAL | STRONG |
| Gateway: Guardrails | Org: Organization profile | 02×01 | PARTIAL | STRONG |
| Gateway: Guardrails | Org: Onboarding | 02×01 | PARTIAL | STRONG |
| Gateway: Guardrails | Org: Users | 02×01 | PARTIAL | STRONG |
| Gateway: Guardrails | Org: Workspaces | 02×01 | PARTIAL | STRONG |
| Gateway: Guardrails | Org: API keys | 02×01 | PARTIAL | STRONG |
| Gateway: Guardrails | Org: MCP registry | 02×01 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Model gateway and Guardrails × Org cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Model gateway and Guardrails
- `FEATURE-STATUS.md` — 02-A/B × 01 counts

## Scope

- **Backend**: Gateway and guardrails should more consistently inherit org/workspace/access-group/user context: gateway routes should expose org-level summaries, guardrails should show workspace and API-key scoping, both should link to telemetry and MCP registry context where runtime execution involves those surfaces.
- **UI**: Gateway and guardrails should show clearer org/workspace context. Onboarding should guide into gateway and guardrail setup. Org profile should summarize gateway and guardrail posture.
- **Docs**: Document how gateway and guardrails inherit org identity context.
- **Postman**: Add org/workspace/access-group context to gateway and guardrail endpoints.
- **Scripts/Examples**: Add example showing gateway and guardrail behavior scoped by workspace and access group.

## Acceptance Criteria

1. Gateway routes expose org-level summaries
2. Guardrails show workspace and API-key scoping
3. Onboarding guides into gateway and guardrail setup
4. Org profile summarizes gateway and guardrail posture
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
