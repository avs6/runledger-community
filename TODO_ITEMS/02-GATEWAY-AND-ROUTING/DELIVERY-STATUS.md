# Gateway & Routing — Delivery Status

Last updated: PENDING AUDIT

---

## Audited Overrides

### Section 4: Gateway & Runtime Controls

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 4.1 | Gateway routes | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `/gateway` now supports real route-management lifecycle depth in the shipped UI: routes, routing groups, policies, and pass-through endpoints all expose edit/update flows in addition to create/list/toggle/delete. The Rust runtime split remains reflected correctly across docs, Postman, examples, labs, and scripts; the remaining broader TypeScript issues observed during verification were pre-existing chart formatter errors outside the gateway surface. |
| 4.2 | Provider profiles | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | `/provider-profiles` is a finished workspace pricing surface with list/create/update/delete, YAML import, example download, sync/reprice actions, Postman coverage, a runnable example, and both manual-lab and automated simulation support. README coverage is still indirect rather than a dedicated product callout. |
| 4.3 | Routing policies | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 4.4 | Routing groups | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 4.5 | Fallback chains | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 4.6 | Deployment health | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 4.7 | Pass-through endpoints | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 4.8 | Runtime controls | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 4.9 | Rate limits | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `OK` | Rate limits are no longer treated as a standalone product surface. As of Friday, August 14, 2026, `/rate-limits` is only a compatibility redirect to `/gateway`; Gateway now owns the real runtime overview through `/gateway/rate-limits/overview`, route/pass-through throttles, and embedded quota-management panels for API-key tiers and per-model quotas, while Budget Tiers and Model Budgets remain the compatibility home for those same quota controls. |
| 4.10 | Benchmarking | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |

### Section 5: Optimization

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 5.1 | Exact cache | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Cache is now treated as part of Gateway rather than a separate product area. Exact cache behavior is reflected through gateway runtime execution, `/gateway` route controls, gateway stats, docs, Postman, examples, and scripts; `/response-cache` remains only as a compatibility redirect while cache profile lifecycle now lives directly inside the Gateway UI and backend CRUD. |
| 5.2 | Semantic cache | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Semantic cache ownership has been collapsed into Gateway. Persistent control now spans both route-level `semantic_cache_enabled` toggles and in-Gateway cache-profile lifecycle management with detail drill-in, while the surrounding docs/examples/scripts/Postman flow remains centered on Gateway rather than a standalone response-cache surface. |
| 5.3 | Context compiler | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 5.4 | Prompt compression | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 5.5 | Intelligent routing | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 5.6 | Tool filtering | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 5.7 | Optimization flywheel | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
