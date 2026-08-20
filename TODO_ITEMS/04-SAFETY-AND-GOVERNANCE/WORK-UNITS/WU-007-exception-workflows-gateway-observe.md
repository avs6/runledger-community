# WU-007: Exception Workflows Gateway & Observe Integration

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - B (Exception Workflows)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Approvals, Alert rules
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Approvals | Gateway: Provider profiles | 04×02 | PARTIAL | STRONG |
| Safety: Approvals | Gateway: Model gateway | 04×02 | PARTIAL | STRONG |
| Safety: Approvals | Gateway: Guardrails | 04×02 | PARTIAL | STRONG |
| Safety: Alert rules | Gateway: Response cache | 04×02 | PARTIAL | STRONG |
| Safety: Approvals | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Approvals | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Approvals | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Approvals | Observe: Request explorer | 04×03 | PARTIAL | STRONG |
| Safety: Alert rules | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Alert rules | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Alert rules | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Alert rules | Observe: Request explorer | 04×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Approvals/Alert rules × Gateway/Observe cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Approvals/Alert rules
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Approvals/Alert rules
- `FEATURE-STATUS.md` — 04-B × 02/03 counts

## Scope

- **Backend**: Approvals should connect to gateway contexts: provider access approvals, model gateway route changes, guardrail override approvals. Alert rules should support cache performance conditions. Both should emit context into observe: approval outcomes visible in request investigation, alert firings visible in runs and monitoring.
- **UI**: Approvals should show gateway context for provider/model/guardrail-related requests. Alert rules should show cache performance conditions. Investigation surfaces should show approval outcomes and alert firings per request. Alerts should pivot to request flow and run detail for investigation.
- **Docs**: Document gateway-triggered approval and alert workflows.
- **Postman**: Add gateway context to approval and alert endpoints.
- **Scripts/Examples**: Add example of an alert-driven investigation pivot from alert rule into request flow.

## Acceptance Criteria

1. Approvals connect to provider, model, and guardrail exception contexts
2. Alert rules support cache and gateway performance conditions
3. Investigation surfaces show approval and alert context per request
4. Alert-to-investigation pivot works end to end
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
