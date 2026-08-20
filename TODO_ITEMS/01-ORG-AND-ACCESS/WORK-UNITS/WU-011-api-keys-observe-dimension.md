# WU-011: API Keys as Observe Investigation Dimension

- **Status**: NOT_STARTED
- **Bundle**: 01-Org & Access - B (Identity & Scope)
- **Target**: 01-ORG-AND-ACCESS/API keys (`/api-keys`)
- **Created**: 2026-08-14
- **Completed**:

## Cohesion Cells to Close

| Source Feature | Target Feature | Cell | Current | Target |
|----------------|----------------|------|---------|--------|
| Org: API keys | Observe: Workspace dashboard | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Analytics overview | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Runs list | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Run detail | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Request flow | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Request explorer | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Model usage | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Analytics economics | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Cost and savings | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Engineering | 01×03 | PARTIAL | STRONG |
| Org: API keys | Observe: Monitoring | 01×03 | PARTIAL | STRONG |

## Paired Features (files to update)

- `01-ORG-AND-ACCESS/COHESION-MATRIX.md` — API keys × Observe cells
- `03-OBSERVE/COHESION-MATRIX.md` — their view of API keys
- `01-ORG-AND-ACCESS/GAP-MATRIX.md` — API keys row
- `FEATURE-STATUS.md` — 01-B × 03 counts

## Scope

- **Backend**: API-key identity should become a first-class filter/dimension across Observe: runs, request flows, request explorer, model usage, analytics economics, cost and savings, engineering, and monitoring should all accept API-key filters and surface API-key attribution in results.
- **UI**: Observe investigation surfaces should expose API-key as a filter facet. API key detail page should link to its observability footprint (runs, model usage, cost).
- **Docs**: Document API-key-scoped investigation workflows in Observe.
- **Postman**: Add API-key filter to runs, request flow, model usage, and analytics endpoints.
- **Scripts/Examples**: Add example investigating traffic and cost by API key across Observe surfaces.

## Acceptance Criteria

1. Runs list, run detail, request flow, and request explorer accept API-key filter
2. Model usage and analytics economics show per-API-key breakdown
3. Cost and savings surface supports API-key-level attribution
4. Engineering and monitoring surfaces recognize API-key dimension
5. API key detail page links to its observability footprint
6. All listed cohesion cells updated to target state
7. All paired feature files updated
8. FEATURE-STATUS.md dashboard updated
