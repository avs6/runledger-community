# Platform & Utility — Delivery Status

Last updated: PENDING AUDIT

---

## Audited Overrides

### Section 8: Agentic & Admin Surfaces

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 8.1 | Agents | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 8.2 | Workflows | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 8.3 | Vector stores | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 8.4 | API playground | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 8.5 | MCP registry | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 8.6 | Plugins | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | Plugin visibility is now treated as part of onboarding/setup discovery rather than a standalone integrations destination, but the underlying management surface is still partial. |
| 8.7 | Projects | `LEGACY` | `LEGACY` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `N/A` | `N/A` | The active Org & Access surface has been removed, the route now redirects to Workspaces, and the public backend compatibility router is no longer mounted. Remaining dependencies are now internal legacy cleanup instead of active product surface debt. |
| 8.8 | AI hub | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | `/ai-hub` now behaves like a finished workspace model catalog with real CRUD, provider sync, access-request tracking, deprecation controls, docs/navigation coverage, Postman requests, a manual lab, an automated smoke script, and a runnable example. |
| 8.9 | Optimization opportunities | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |

### Section 9: Operations & Integrations

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 9.1 | SMTP settings and email delivery | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.2 | Email delivery history and reports | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.3 | Backup target config | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.4 | Backup runs and snapshots | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.5 | Restore drill | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.6 | Kafka export configs | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | CRUD is now exposed from Organization Console -> Destinations, with docs/Postman/script coverage updated. |
| 9.7 | Kafka delivery history, retry, DLQ | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.8 | Redpanda live streaming demo | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.9 | OTEL collector | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collector docs, telemetry UI, ingest endpoints, labs, scripts, and compose profile are aligned. |
| 9.10 | Queue visibility | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.11 | Feature flags | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.12 | Storage posture and infra policy | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.13 | Local TLS and demo proxy | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.14 | Deployment profiles | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
