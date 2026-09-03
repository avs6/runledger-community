# WU-001: Platform lifecycle delivery and posture completion

- **Status**: COMPLETED
- **Bundle**: Platform & Utility - Platform Lifecycle Control Plane
- **Target**: 07-PLATFORM-AND-UTILITY/All organizations (`/organizations`)
- **Created**: 2026-08-15
- **Completed**: 2026-09-03

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| All organizations | Budgets | 07x05 | STRONG | STRONG |
| All organizations | Billing periods | 07x05 | STRONG | STRONG |
| All organizations | Chargeback | 07x05 | STRONG | STRONG |
| All organizations | Ledger | 07x05 | STRONG | STRONG |
| All organizations | Onboarding | 07x01 | STRONG | STRONG |
| All organizations | Workspaces | 07x01 | STRONG | STRONG |
| All organizations | API keys | 07x01 | STRONG | STRONG |
| All organizations | Platform settings | 07x07 | STRONG | STRONG |
| All organizations | Model gateway | 07x02 | STRONG | STRONG |
| All organizations | Guardrails | 07x04 | STRONG | STRONG |
| All organizations | Audit log | 07x04 | STRONG | STRONG |

## Paired Features (files to update)

- `07-PLATFORM-AND-UTILITY/GAP-MATRIX.md` - All organizations row
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` - All organizations cells
- `05-FINOPS/COHESION-MATRIX.md` - their view of All organizations lifecycle and FinOps summaries
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` - their view of lifecycle handoff into onboarding, workspaces, and API keys
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` - their view of platform-admin gateway posture summaries
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` - their view of audit and guardrail posture summaries
- `07-PLATFORM-AND-UTILITY/DELIVERY-STATUS.md` - platform lifecycle delivery completeness if support surfaces change

## Scope

- **Backend**: Add or normalize organization-level summary payloads for billing, lifecycle posture, gateway readiness, and governance posture without moving ownership out of the underlying feature families.
- **UI**: Strengthen `/organizations` as the platform-admin lifecycle hub with downstream posture cards, clearer lifecycle filters, and explicit handoff paths into org-owned setup surfaces.
- **Docs**: Document `/organizations` as the canonical platform lifecycle owner and explain the boundaries between org lifecycle, org settings, and platform settings.
- **Postman**: Add or refresh organization lifecycle and posture-summary coverage so platform-admin entry points are exercised as first-class API paths.
- **Scripts/Examples**: Add or refresh realistic platform-admin org lifecycle simulations, including create, suspend, reactivate, and posture review flows.

## Acceptance Criteria

1. `/organizations` remains the canonical platform lifecycle owner for create, update, suspend, reactivate, and delete flows.
2. Platform-admin users can see useful downstream posture summaries for FinOps, gateway, and governance without those surfaces being absorbed into `/organizations`.
3. Support surfaces for All organizations are materially improved across docs, Postman, and scripts/examples.
4. All listed cohesion cells updated to target state.
5. All paired feature files updated.
6. `FEATURE-STATUS.md` dashboard updated.

## Completion Notes

### What shipped

- **Backend**: New `GET /analytics/platform-lifecycle-posture` endpoint (platform admin only) via `PlatformLifecyclePosture` Pydantic model. Returns cross-org FinOps lifecycle (billing periods, active periods, chargeback rules, ledger snapshots), gateway readiness (routes, providers, guardrail rules), governance posture (audit events 7d, tool policies, alert rules), and org access context (workspaces, API keys, users).
- **UI**: Organizations page now shows 5 posture cards: Budget Control Platform Posture (existing emerald), FinOps Lifecycle (emerald), Gateway Readiness (violet), Governance & Audit (amber), and Org & Access Lifecycle (blue). Each card has drill-through links to owning surfaces.
- **Docs**: `docs/administration/organizations.mdx` expanded with Platform Posture Cards section documenting all 5 cards and Lifecycle Boundaries section clarifying what organizations owns vs. delegates.
- **Postman**: Platform Lifecycle Posture request added to the analytics folder.
- **Scripts**: `scripts/org_lifecycle_posture_smoke.py` validates endpoint structure.
- **Examples**: `examples/157_platform_lifecycle_posture.py` demonstrates the posture fetch.

### Cohesion cells

Most cells listed in WU-001 were already upgraded to STRONG by prior WUs (05-FINOPS WU-006/011/012/013, etc.) before this WU started. The remaining PARTIAL cell (All organizations × Audit log) is now STRONG because the organizations page surfaces audit event counts via the platform lifecycle posture endpoint with drill-through to the Audit Log page. All 11 listed cells are now STRONG.

### What remains partial

Monitoring, Telemetry, Evaluation studio, and Optimization simulator remain PARTIAL for All organizations — these are outside WU-001 scope and targeted by WU-005.
