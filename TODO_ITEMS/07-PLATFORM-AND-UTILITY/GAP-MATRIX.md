# Platform & Utility — GAP Matrix

Last updated: PENDING AUDIT

## Legend

| Status | Meaning |
|--------|---------|
| `PENDING` | Not yet audited |
| `OK` | Verified working |
| `PARTIAL` | Present but partial, buggy, or unclear |
| `MISSING` | Missing, broken, or disconnected |
| `LEGACY` | Legacy/transitional surface; do not expand |

---

## Platform Features

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| All organizations | `/organizations` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Keep separate. | P7 | `PENDING` | `1.2`, `1.7` | Platform-admin lifecycle hub is real with create/list/update/delete plus suspend/reactivate controls. Not fully complete because support coverage is uneven outside the core UI/API. |
| Platform settings | `/settings` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Make this the single home for `Ledger`, `Retention`, `Backup`, and ops/compliance surfaces. | P7 | `PENDING` | `1.7`, `7.7`, `9.3`, `9.4`, `9.5`, `9.11`, `9.12`, `9.13`, `9.14` | This is an umbrella console for compliance, retention, backups, and ops posture. Some subareas like retention are strong CRUD, but the route as a whole is not one cohesive managed entity with a single completion bar. |

---

## Additional Admin / Utility Routes

| Feature | Route | Backend | UI | Actions | Docs | Postman | Scripts/Examples | Complete | Cohesion | Merge / Collapse | Fix Order | Fix Status | Delivery Audit Crosswalk | Notes |
|---------|-------|---------|----|---------|------|---------|------------------|----------|----------|------------------|-----------|------------|--------------------|-------|
| Plugins | `/plugins` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Collapse into `Onboarding`; do not keep a redirect-only top-level route. | P1 | `PENDING` | `8.6` | Backend has full plugin CRUD plus execution logs, but `/plugins` is now only a compatibility redirect into Onboarding. Setup/discovery belongs there; any future dedicated plugin management should be reintroduced intentionally rather than preserved as a ghost route. |
