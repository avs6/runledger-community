# WU-008: Overview Cross-Feature Posture Cards

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - A (Overview & Entry)
- **Target**: 03-OBSERVE/Analytics overview
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Analytics overview | Org: Onboarding | 03×01 | PARTIAL | STRONG |
| Observe: Analytics overview | Org: Users | 03×01 | PARTIAL | STRONG |
| Observe: Analytics overview | Org: API keys | 03×01 | PARTIAL | STRONG |
| Observe: Analytics overview | Org: Telemetry | 03×01 | PARTIAL | STRONG |
| Observe: Analytics overview | Org: MCP registry | 03×01 | PARTIAL | STRONG |
| Observe: Analytics overview | Org: AI hub | 03×01 | PARTIAL | STRONG |
| Observe: Analytics overview | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Analytics overview | Gateway: Model gateway | 03×02 | PARTIAL | STRONG |
| Observe: Analytics overview | Gateway: Guardrails | 03×02 | PARTIAL | STRONG |
| Observe: Analytics overview | Safety: Security | 03×04 | PARTIAL | STRONG |
| Observe: Analytics overview | Safety: Alert rules | 03×04 | PARTIAL | STRONG |
| Observe: Analytics overview | Safety: Audit log | 03×04 | PARTIAL | STRONG |
| Observe: Analytics overview | Safety: Governance pack | 03×04 | PARTIAL | STRONG |
| Observe: Analytics overview | Safety: Tags | 03×04 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Analytics overview × Org/Gateway/Safety cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Analytics overview
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Analytics overview
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Analytics overview
- `FEATURE-STATUS.md` — 03-A × 01/02/04 counts

## Scope

- **Backend**: Analytics overview should consume cross-feature posture summaries: gateway health (active providers, route coverage, guardrail status), governance posture (recent security events, alert rule firings, audit activity), org identity context (user count, API key count, telemetry health, MCP registry status, AI hub model count). All read-only aggregates.
- **UI**: Analytics overview should display posture cards for gateway, governance, and org context with drill-through links. No editing — summary with navigation only.
- **Docs**: Document the analytics overview as the cross-feature posture entry point.
- **Postman**: Add cross-feature posture summary endpoints for analytics overview.
- **Scripts/Examples**: Add example reading cross-feature posture from analytics overview.

## Acceptance Criteria

1. Analytics overview shows gateway posture card (providers, routes, guardrails)
2. Analytics overview shows governance posture card (security, alerts, audit)
3. Analytics overview shows org context (users, keys, telemetry, MCP, AI hub)
4. Each posture card links to the owning surface
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
