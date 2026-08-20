# WU-010: Monitoring & Ops Governance Integration

- **Status**: NOT_STARTED
- **Bundle**: 03-Observe - D (Ops & Monitoring)
- **Target**: 03-OBSERVE/Monitoring, Telemetry, Engineering
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Observe: Monitoring | Gateway: Provider profiles | 03×02 | PARTIAL | STRONG |
| Observe: Monitoring | Gateway: Guardrails | 03×02 | PARTIAL | STRONG |
| Observe: Monitoring | Gateway: Response cache | 03×02 | PARTIAL | STRONG |
| Observe: Monitoring | Gateway: Rate limits | 03×02 | PARTIAL | STRONG |
| Observe: Monitoring | Safety: Tool registry | 03×04 | PARTIAL | STRONG |
| Observe: Monitoring | Safety: Tool policies | 03×04 | PARTIAL | STRONG |
| Observe: Monitoring | Safety: Data capture | 03×04 | PARTIAL | STRONG |
| Observe: Monitoring | Safety: Audit log | 03×04 | PARTIAL | STRONG |
| Observe: Monitoring | Safety: Governance pack | 03×04 | PARTIAL | STRONG |
| Observe: Monitoring | Org: Organization profile | 03×01 | PARTIAL | STRONG |
| Observe: Monitoring | Org: Onboarding | 03×01 | PARTIAL | STRONG |
| Observe: Monitoring | Org: Workspaces | 03×01 | PARTIAL | STRONG |
| Observe: Monitoring | Org: MCP registry | 03×01 | PARTIAL | STRONG |
| Observe: Monitoring | Observe: Analytics overview | 03×03 | PARTIAL | STRONG |
| Observe: Monitoring | Observe: Runs list | 03×03 | PARTIAL | STRONG |
| Observe: Monitoring | Observe: Request flow | 03×03 | PARTIAL | STRONG |
| Observe: Monitoring | Observe: Request explorer | 03×03 | PARTIAL | STRONG |
| Observe: Telemetry | Gateway: Model gateway | 03×02 | PARTIAL | STRONG |
| Observe: Telemetry | Safety: Data capture | 03×04 | PARTIAL | STRONG |
| Observe: Telemetry | Safety: Security | 03×04 | PARTIAL | STRONG |
| Observe: Telemetry | Safety: Alert rules | 03×04 | PARTIAL | STRONG |
| Observe: Telemetry | Safety: Audit log | 03×04 | PARTIAL | STRONG |
| Observe: Telemetry | Safety: Governance pack | 03×04 | PARTIAL | STRONG |
| Observe: Telemetry | Org: Organization profile | 03×01 | PARTIAL | STRONG |
| Observe: Telemetry | Org: Onboarding | 03×01 | PARTIAL | STRONG |
| Observe: Telemetry | Org: Workspaces | 03×01 | PARTIAL | STRONG |
| Observe: Telemetry | Observe: Analytics overview | 03×03 | PARTIAL | STRONG |
| Observe: Telemetry | Observe: Runs list | 03×03 | PARTIAL | STRONG |
| Observe: Telemetry | Observe: Request flow | 03×03 | PARTIAL | STRONG |
| Observe: Telemetry | Observe: Request explorer | 03×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `03-OBSERVE/COHESION-MATRIX.md` — Monitoring/Telemetry × Gateway/Safety/Org/Self cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Monitoring/Telemetry
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of Monitoring/Telemetry
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Monitoring/Telemetry
- `FEATURE-STATUS.md` — 03-D × 01/02/03/04 counts

## Scope

- **Backend**: Monitoring should aggregate gateway runtime signals (provider health, guardrail firing rates, cache/throttle events), governance signals (tool policy outcomes, security events, audit activity), and org context (workspace health, MCP status). Telemetry should correlate with gateway events, security events, and alert rule firings. Both should link into investigation surfaces.
- **UI**: Monitoring should present unified operational signals from gateway, governance, and org with drill-through. Telemetry should show governance and gateway correlation. Both should link to analytics overview, runs, request flow, and request explorer for investigation.
- **Docs**: Document the monitoring triage workflow across gateway, governance, and org signals.
- **Postman**: Add cross-feature signal aggregation to monitoring and telemetry endpoints.
- **Scripts/Examples**: Add example triage workflow from monitoring through gateway and governance signals into investigation.

## Acceptance Criteria

1. Monitoring aggregates gateway, governance, and org operational signals
2. Telemetry correlates with gateway and governance events
3. Both link to investigation surfaces for drill-in
4. Workspace and org context visible in monitoring and telemetry
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
