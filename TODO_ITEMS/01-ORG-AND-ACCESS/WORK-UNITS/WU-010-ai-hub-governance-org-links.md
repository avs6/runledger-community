# WU-010: AI Hub Governance and Org-Admin Links

- **Status**: COMPLETED
- **Bundle**: 01-Org & Access - D (Capability Catalog)
- **Target**: 01-ORG-AND-ACCESS/AI hub (`/ai-hub`)
- **Created**: 2026-08-14
- **Completed**: 2026-08-21

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: AI hub | FinOps: Budget detail | 01×05 | STRONG | STRONG |
| Org: AI hub | FinOps: Budgets | 01×05 | STRONG | STRONG |
| Org: AI hub | FinOps: Billing periods | 01×05 | STRONG | STRONG |
| Org: AI hub | FinOps: Billing period detail | 01×05 | STRONG | STRONG |
| Org: AI hub | FinOps: Chargeback | 01×05 | STRONG | STRONG |
| Org: AI hub | Safety: Tool registry | 01×04 | STRONG | STRONG |
| Org: AI hub | Safety: Tool policies | 01×04 | STRONG | STRONG |
| Org: AI hub | Safety: Approvals | 01×04 | STRONG | STRONG |
| Org: AI hub | Safety: Security | 01×04 | STRONG | STRONG |
| Org: AI hub | Safety: Audit log | 01×04 | STRONG | STRONG |
| Org: AI hub | Safety: Governance pack | 01×04 | STRONG | STRONG |
| Org: AI hub | Safety: Tags | 01×04 | STRONG | STRONG |
| Org: AI hub | Platform: All organizations | 01×07 | STRONG | STRONG |
| Org: AI hub | Platform: Platform settings | 01×07 | STRONG | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — AI hub × FinOps/Safety/Platform cells
- `05-FINOPS/COHESION-MATRIX.md` — their view of AI hub
- `04-SAFETY-AND-GOVERNANCE/COHESION-MATRIX.md` — their view of AI hub
- `07-PLATFORM-AND-UTILITY/COHESION-MATRIX.md` — their view of AI hub
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — AI hub row
- `FEATURE-STATUS.md` — 01-D × 04/05/07 counts

## Scope

- **Backend**: AI hub now exposes model cost posture (GET /hub/models/{id}/cost-posture linked to budget detail and billing), model governance status (GET /hub/models/{id}/governance linked to approvals, audit log, governance pack, tool policies), and cross-org model summary (GET /hub/org-summary for platform admin).
- **UI**: AI hub now displays cross-feature navigation links to Budgets, Approvals, Audit Log, Governance Pack, Tags, Organization Console, and Platform Settings. Per-model posture panel shows cost posture (budget count, limit, spend) and governance status (approvals, audit events, tool policies) with drill-through links to budget detail, billing, chargeback, approvals, audit log, governance pack, and tool policies.
- **Docs**: Updated docs/administration/ai-hub.mdx with governance and financial integration patterns, new API endpoint documentation, and relationship sections for FinOps, Safety & Governance, and Platform admin surfaces.
- **Postman**: Added AI Hub folder with 10 requests covering full CRUD, sync, cost posture, governance status, and org summary endpoints.
- **Scripts/Examples**: Updated 42_ai_hub_catalog.py and exercise_ai_hub_catalog.py with cost posture and governance status checks.

## Acceptance Criteria

1. ✅ AI hub shows per-model cost posture with drill-through to budget detail
2. ✅ Model access requests integrate with the approvals workflow
3. ✅ Model policy actions appear in audit log and governance pack
4. ✅ Platform admin can view cross-org model capability summary
5. ✅ AI hub tags participate in the tags/governance scoping model
6. ✅ All listed cohesion cells updated to target state
7. ✅ All paired feature files updated
8. ✅ FEATURE-STATUS.md dashboard updated

## Completion Notes

- Backend: 3 new endpoints (cost-posture, governance, org-summary) added to hub.py router with corresponding Pydantic schemas.
- UI: AI hub page now has 8 cross-feature navigation links in the header and a per-model posture modal with cost and governance drill-through.
- Docs: ai-hub.mdx expanded from 59 to ~90 lines with governance, FinOps, and platform relationship sections.
- Postman: AI Hub folder added with 10 requests (was MISSING, now OK).
- Scripts: Both example and exercise scripts now verify cost posture and governance status endpoints.
- 14 cohesion cells closed to STRONG across FinOps (5), Safety & Governance (7), and Platform (2).
