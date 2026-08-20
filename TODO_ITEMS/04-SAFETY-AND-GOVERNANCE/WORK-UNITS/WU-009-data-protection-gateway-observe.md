# WU-009: Data Protection Gateway & Observe Integration

- **Status**: NOT_STARTED
- **Bundle**: 04-Safety - C (Data Protection)
- **Target**: 04-SAFETY-AND-GOVERNANCE/Data capture, Security, Tags
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Safety: Data capture | Gateway: Model gateway | 04×02 | PARTIAL | STRONG |
| Safety: Data capture | Gateway: Guardrails | 04×02 | PARTIAL | STRONG |
| Safety: Data capture | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Data capture | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Data capture | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Data capture | Observe: Request explorer | 04×03 | PARTIAL | STRONG |
| Safety: Data capture | Observe: Monitoring | 04×03 | PARTIAL | STRONG |
| Safety: Security | Gateway: Provider profiles | 04×02 | PARTIAL | STRONG |
| Safety: Security | Gateway: Guardrails | 04×02 | PARTIAL | STRONG |
| Safety: Security | Gateway: Response cache | 04×02 | PARTIAL | STRONG |
| Safety: Security | Gateway: Rate limits | 04×02 | PARTIAL | STRONG |
| Safety: Security | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Security | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Security | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Security | Observe: Request explorer | 04×03 | PARTIAL | STRONG |
| Safety: Tags | Gateway: Provider profiles | 04×02 | PARTIAL | STRONG |
| Safety: Tags | Gateway: Model gateway | 04×02 | PARTIAL | STRONG |
| Safety: Tags | Gateway: Guardrails | 04×02 | PARTIAL | STRONG |
| Safety: Tags | Observe: Runs list | 04×03 | PARTIAL | STRONG |
| Safety: Tags | Observe: Run detail | 04×03 | PARTIAL | STRONG |
| Safety: Tags | Observe: Request flow | 04×03 | PARTIAL | STRONG |
| Safety: Tags | Observe: Request explorer | 04×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — Data capture/Security/Tags × Gateway/Observe cells
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Data capture/Security/Tags
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Data capture/Security/Tags
- `FEATURE-STATUS.md` — 04-C × 02/03 counts

## Scope

- **Backend**: Data capture should connect to gateway: capture policy influence on model gateway routing, guardrail-data-capture correlation. Security should connect to provider profiles, guardrails, cache, and rate limits for security posture at the gateway layer. Tags should propagate through gateway routing (provider and guardrail tag context) and into observe (tag-based investigation filtering). All three should emit richer context into investigation surfaces.
- **UI**: Data capture should show gateway influence and investigation evidence. Security should show gateway security posture and investigation links. Tags should be a filter dimension on investigation surfaces and show gateway routing context. Monitoring should show data protection signals.
- **Docs**: Document data protection traceability through gateway and observe.
- **Postman**: Add gateway and observe context to data protection endpoints.
- **Scripts/Examples**: Add example tracing a security event through gateway and into request investigation.

## Acceptance Criteria

1. Data capture connects to model gateway and guardrails
2. Security shows gateway-layer posture (providers, cache, rate limits)
3. Tags propagate into investigation surfaces as filter dimensions
4. Investigation surfaces show data protection context
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
