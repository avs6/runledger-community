# WU-008: Guardrails Observe Traceability

- **Status**: NOT_STARTED
- **Bundle**: 02-Gateway & Routing - B (Runtime Protection)
- **Target**: 02-GATEWAY-AND-ROUTING/Guardrails (`/guardrails`)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Gateway: Guardrails | Observe: Runs list | 02×03 | PARTIAL | STRONG |
| Gateway: Guardrails | Observe: Run detail | 02×03 | PARTIAL | STRONG |
| Gateway: Guardrails | Observe: Request flow | 02×03 | PARTIAL | STRONG |
| Gateway: Guardrails | Observe: Request explorer | 02×03 | PARTIAL | STRONG |
| Gateway: Guardrails | Observe: Outcomes and ROI | 02×03 | PARTIAL | STRONG |
| Gateway: Guardrails | Observe: Engineering | 02×03 | PARTIAL | STRONG |
| Gateway: Guardrails | Observe: Monitoring | 02×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — Guardrails × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Guardrails
- `FEATURE-STATUS.md` — 02-B × 03 counts

## Scope

- **Backend**: Guardrail enforcement events should be traceable through Observe: runs and request flow should carry guardrail outcome metadata (blocked, modified, passed), request explorer should accept guardrail-outcome as a filter, monitoring should surface guardrail firing rates, outcomes/ROI should include guardrail-driven impact metrics.
- **UI**: Run detail and request flow should show guardrail outcome inline. Request explorer should filter by guardrail result. Monitoring should surface guardrail firing rates and trends. Engineering view should show guardrail latency impact.
- **Docs**: Document guardrail-to-observe traceability workflow.
- **Postman**: Add guardrail outcome metadata to run and request flow responses; add guardrail filter to request explorer.
- **Scripts/Examples**: Add example tracing a guardrail block through runs, request flow, and monitoring.

## Acceptance Criteria

1. Runs and request flow carry guardrail outcome metadata
2. Request explorer filters by guardrail result
3. Monitoring surfaces guardrail firing rates and trends
4. Engineering view shows guardrail latency contribution
5. Outcomes/ROI includes guardrail-driven impact metrics
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
