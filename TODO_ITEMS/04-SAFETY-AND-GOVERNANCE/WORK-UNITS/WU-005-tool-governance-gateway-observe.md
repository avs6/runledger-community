# WU-005: Tool Governance Gateway & Observe Runtime Traceability

- **Status**: COMPLETED
- **Bundle**: 04-Safety - A (Tool Governance)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Tool registry, Tool policies
- **Created**: 2026-08-14
- **Completed**: 2026-08-27

**Note**: All 17 target cohesion cells (Tool registry/policies × Gateway & Observe features) were already STRONG from prior observe-side work units. WU-005 adds the violet Gateway & Observe Runtime posture card to both Tool Registry and Tool Policies pages via `GET /analytics/tool-governance-gateway-posture` providing bidirectional traceability from the safety governance side.

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Tool registry | Gateway: Provider profiles | 04×02 | PARTIAL | STRONG |
| Safety: Tool registry | Gateway: Guardrails | 04×02 | PARTIAL | STRONG |
| Safety: Tool registry | Gateway: Response cache | 04×02 | PARTIAL | STRONG |
| Safety: Tool registry | Gateway: Rate limits | 04×02 | PARTIAL | STRONG |
| Safety: Tool registry | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Tool registry | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Tool registry | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Tool registry | Observe: Request explorer | 04×03 | PARTIAL | STRONG |
| Safety: Tool registry | Observe: Monitoring | 04×03 | PARTIAL | STRONG |
| Safety: Tool policies | Gateway: Provider profiles | 04×02 | PARTIAL | STRONG |
| Safety: Tool policies | Gateway: Response cache | 04×02 | PARTIAL | STRONG |
| Safety: Tool policies | Gateway: Rate limits | 04×02 | PARTIAL | STRONG |
| Safety: Tool policies | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Tool policies | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Tool policies | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Tool policies | Observe: Request explorer | 04×03 | PARTIAL | STRONG |
| Safety: Tool policies | Observe: Monitoring | 04×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Tool registry/policies × Gateway/Observe cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Tool registry/policies
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Tool registry/policies
- `FEATURE-STATUS.md` — 04-A × 02/03 counts

## Scope

- **Backend**: Tool registry should link to provider profiles that serve registered tools and to guardrails that reference them. Tool policies should connect to cache and rate-limit behavior per tool. Both should emit richer tool-governance context into runtime telemetry for runs, request flow, and monitoring.
- **UI**: Tool registry should show which providers and guardrails reference each tool. Tool policies should show cache and rate-limit implications. Investigation surfaces should show tool policy outcomes per request. Monitoring should show tool governance signals.
- **Docs**: Document tool governance traceability through gateway and observe.
- **Postman**: Add gateway and observe context to tool governance endpoints.
- **Scripts/Examples**: Add example tracing a tool policy decision through gateway routing into request investigation.

## Acceptance Criteria

1. Tool registry shows provider and guardrail references
2. Tool policies show cache and rate-limit implications
3. Investigation surfaces show tool policy outcomes
4. Monitoring shows tool governance signals
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
