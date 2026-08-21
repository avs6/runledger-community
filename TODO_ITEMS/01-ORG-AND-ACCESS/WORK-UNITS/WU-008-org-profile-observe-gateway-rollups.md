# WU-008: Org Profile Observe & Gateway Posture Rollups

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - A (Org Foundation)
- **Target**: 01-ORG-AND-ACCESS/Organization profile (`/organization`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-20

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: Organization profile | Observe: Workspace dashboard | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Runs list | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Run detail | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Sessions list | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Session detail | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Request flow | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Request explorer | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Model usage | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Analytics economics | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Cost and savings | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Billing summary | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Outcomes and ROI | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Analytics users | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Analytics user detail | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Engineering | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Observe: Monitoring | 01×03 | PARTIAL | STRONG |
| Org: Organization profile | Gateway: Provider profiles | 01×02 | PARTIAL | STRONG |
| Org: Organization profile | Gateway: Model gateway | 01×02 | PARTIAL | STRONG |
| Org: Organization profile | Gateway: Guardrails | 01×02 | PARTIAL | STRONG |
| Org: Organization profile | Gateway: Rate limits | 01×02 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — Organization profile × Observe and Gateway cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Organization profile
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Organization profile
- `FEATURE-STATUS.md` — 01-A × 03 and 01-A × 02 counts

## Scope

- **Backend**: Add read-only org-level posture summary endpoints for runtime and observability: active provider count, gateway health, guardrail coverage, rate-limit posture, recent run volume, model usage trend, monitoring alert count. All summaries are read-only aggregates.
- **UI**: Org console should display runtime posture card (gateway/provider/guardrails/rate-limits) and observability posture card (run volume, model usage, monitoring alerts) with drill-through links. No editing in org console — read-only with navigation.
- **Docs**: Document org-level runtime and observability summaries.
- **Postman**: Add org posture summary requests for runtime and observability.
- **Scripts/Examples**: Add example reading org runtime and observability posture.

## Acceptance Criteria

1. Org console shows a read-only runtime posture card (providers, gateway, guardrails, rate limits)
2. Org console shows a read-only observability posture card (runs, model usage, monitoring)
3. Each summary element links to the owning Observe or Gateway surface
4. No duplicate control-plane editing created in org console
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated
