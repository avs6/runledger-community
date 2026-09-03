# WU-003: Managed Assets × Cross-Feature Strengthening

- **Status**: COMPLETED
- **Bundle**: 06-Build & Improve - B (Managed Execution Assets)
- **Target**: 06-BUILD-AND-IMPROVE/Workflow detail
- **Created**: 2026-08-15
- **Completed**: 2026-09-02

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Build: Workflow detail | Org: Access groups | 06×01 | PARTIAL | STRONG |
| Build: Workflow detail | Org: API keys | 06×01 | PARTIAL | STRONG |
| Build: Workflow detail | Org: AI hub | 06×01 | PARTIAL | STRONG |
| Build: Workflow detail | Gateway: Provider profiles | 06×02 | PARTIAL | STRONG |
| Build: Workflow detail | Gateway: Guardrails | 06×02 | PARTIAL | STRONG |
| Build: Workflow detail | Gateway: Response cache | 06×02 | PARTIAL | STRONG |
| Build: Workflow detail | Gateway: Rate limits | 06×02 | PARTIAL | STRONG |
| Build: Workflow detail | Observe: Analytics overview | 06×03 | PARTIAL | STRONG |
| Build: Workflow detail | Observe: Request explorer | 06×03 | PARTIAL | STRONG |
| Build: Workflow detail | Observe: Model usage | 06×03 | PARTIAL | STRONG |
| Build: Workflow detail | Observe: Cost and savings | 06×03 | PARTIAL | STRONG |
| Build: Workflow detail | FinOps: Budgets | 06×05 | PARTIAL | STRONG |
| Build: Workflow detail | FinOps: Billing periods | 06×05 | PARTIAL | STRONG |

## Paired Features (files to update)

- `06-BUILD-AND-IMPROVE/COHESION-MATRIX.md` — Workflow detail × Org/Gateway/Observe/FinOps cells
- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — their view of Workflow detail
- `02-GATEWAY-AND-ROUTING/COHESION-MATRIX.md` — their view of Workflow detail
- `03-OBSERVE/COHESION-MATRIX.md` — their view of Workflow detail
- `05-FINOPS/COHESION-MATRIX.md` — their view of Workflow detail
- `FEATURE-STATUS.md` — 06-B × 01/02/03/05 counts

## Scope

- **Backend**: Workflow detail should consume access-group, API-key, and AI hub context for execution scope. Provider profiles, guardrails, cache, and rate-limit posture should be visible as workflow runtime context. Observe surfaces (analytics, request explorer, model usage, cost) should be linkable from workflow runs. Budget posture and billing period context should be available for workflow cost tracking.
- **UI**: Workflow detail should show access-group and API-key execution scope. Gateway runtime configuration should be visible. Observe drill-ins for analytics, requests, model usage, and cost should be accessible from workflow detail. Budget warnings and billing period cost context should be displayed.
- **Docs**: Document workflow cross-feature integration with org, gateway, observe, and FinOps.
- **Postman**: Add cross-feature context to workflow detail endpoints.
- **Scripts/Examples**: Add example viewing workflow detail with gateway config, observe drill-ins, and budget context.

## Acceptance Criteria

1. Workflow detail shows access-group, API-key, and AI hub execution scope
2. Gateway runtime configuration visible in workflow context
3. Observe drill-ins accessible from workflow detail
4. Budget and billing period context displayed for workflow cost tracking
5. All listed cohesion cells updated to target state
6. All paired feature files updated
7. FEATURE-STATUS.md dashboard updated

## Completion Notes (2026-09-02)

- Backend: Added `WorkflowDetailCrossFeaturePosture` schema and `GET /analytics/workflow-detail-cross-feature-posture` endpoint returning org context (workspace, access groups, API keys, hub models), gateway context (providers, routes, guardrails, cache, rate limits), observe context (runs, provider calls, models, cost), and FinOps context (budgets, billing periods, limit, spend).
- UI: Added four cross-feature posture cards to Workflow detail page: blue "Organization & Access Context" (workspace, access groups, API keys, hub models with Organization/Access Groups/API Keys/AI Hub drill-through), violet "Gateway & Routing Context" (providers, routes, guardrails, cache with Provider Profiles/Guardrails/Response Cache/Rate Limits drill-through), cyan "Observe & Analytics Context" (runs, calls, models, cost with Analytics Overview/Request Explorer/Model Usage/Cost & Savings drill-through), and emerald "FinOps & Budget Context" (budgets, billing periods, limit, spend with Budgets/Billing Periods drill-through).
- Docs: Added "Cross-Feature Context (Workflow Detail)" section to workflows.mdx with curl example.
- Postman: Added "Workflow Detail Cross-Feature Posture" entry.
- Examples: Added `132_workflow_detail_cross_feature_posture.py`.
- Audit: Updated 06-BUILD COHESION-MATRIX (Workflow detail × 13 cells P→S), 01-ORG, 02-GATEWAY, 03-OBSERVE, 05-FINOPS COHESION-MATRIXes paired view, GAP-MATRIX notes, and FEATURE-STATUS counts.
