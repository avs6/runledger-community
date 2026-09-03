# Platform & Utility — Delivery Status

Last updated: 2026-08-15

---

## Audited Overrides

### Section 8: Agentic & Admin Surfaces

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 8.1 | Agents | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | `N/A` | `N/A` | Agents now have real backend CRUD and solid support coverage, but the product surface is still read-heavy and does not own full create/update/retire management in-product. |
| 8.2 | Workflows | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | `N/A` | `N/A` | Workflow definitions and run-detail investigation are real, but the dashboard still under-owns authoring and lifecycle edits compared with the backend capability. |
| 8.3 | Vector stores | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | `N/A` | `N/A` | Vector store backend CRUD is real and the detail surface is useful, but the product still leans on API-first management rather than full in-product lifecycle control. |
| 8.4 | API playground | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `OK` | `N/A` | `N/A` | Playground has real session/request support and supporting assets, but the UI is still more of a viewer/demo shell than a full interactive gateway lab. |
| 8.5 | MCP registry | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 8.6 | Plugins | `OK` | `PARTIAL` | `OK` | `OK` | `OK` | `OK` | `PARTIAL` | `OK` | `N/A` | `N/A` | WU-003 completes collapsed ownership model. Backend: full CRUD plus seed_defaults and execution log. UI intentionally redirects to /onboarding?section=connections. Docs: `plugins.mdx` documents backend API, ownership model, and lifecycle. Postman: Plugins folder with 7 requests. Example 159 covers full lifecycle. Script smoke test validates structure. |
| 8.7 | Projects | `LEGACY` | `LEGACY` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `N/A` | `N/A` | The active Org & Access surface has been removed, the route now redirects to Workspaces, and the public backend compatibility router is no longer mounted. Remaining dependencies are now internal legacy cleanup instead of active product surface debt. |
| 8.8 | AI hub | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `N/A` | `N/A` | `/ai-hub` now behaves like a finished workspace model catalog with real CRUD, provider sync, access-request tracking, deprecation controls, docs/navigation coverage, Postman requests, a manual lab, an automated smoke script, and a runnable example. |
| 8.9 | Optimization opportunities | `PARTIAL` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `N/A` | `N/A` | The analytics endpoint and recommendation UI are real, but this remains an advisory surface rather than a closed optimization workflow. |

### Section 9: Operations & Integrations

| # | Feature | Backend | UI | Docs | README | Examples | Postman | Manual Lab | Auto Script | Infra | Supporting Infra | Notes |
|---|---------|---------|----|------|--------|----------|---------|------------|-------------|-------|------------------|-------|
| 9.1 | SMTP settings and email delivery | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Email preferences, status, and test/report flows are real under Platform Settings, but they still read more like one strong tab in a larger console than a fully separated owner surface. |
| 9.2 | Email delivery history and reports | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | History and log endpoints exist and are surfaced in Settings, but the support story is still bundled under the broader platform-settings umbrella rather than fully broken out. |
| 9.3 | Backup target config | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Backup config is a real operator flow inside Platform Settings, with live backend coverage and surrounding support assets, but it is still one sub-surface of the larger settings console. |
| 9.4 | Backup runs and snapshots | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | History, snapshot inventory, and status flows are real, but they are still delivered as part of the broader backup tab rather than a standalone finished product area. |
| 9.5 | Restore drill | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Restore drill is implemented and exposed in Platform Settings, but the surrounding docs/examples and ownership model still live as part of the larger backup-and-restore bundle. |
| 9.6 | Kafka export configs | `OK` | `OK` | `OK` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | `PARTIAL` | `OK` | CRUD is now exposed from Organization Console -> Destinations, with docs/Postman/script coverage updated. |
| 9.7 | Kafka delivery history, retry, DLQ | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.8 | Redpanda live streaming demo | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | |
| 9.9 | OTEL collector | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | `OK` | Collector docs, telemetry UI, ingest endpoints, labs, scripts, and compose profile are aligned. |
| 9.10 | Queue visibility | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Queue status is already exposed through Platform Settings ops views, but it is still a supporting operational slice rather than a fully owned dedicated product area. |
| 9.11 | Feature flags | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Feature flag status and policy evaluation are already surfaced in Settings, but they remain supporting platform posture tools more than a standalone destination. |
| 9.12 | Storage posture and infra policy | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `OK` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Storage and infra-policy visibility are real through Settings ops/storage views and docs, but still packaged as part of the broader platform settings console. |
| 9.13 | Local TLS and demo proxy | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Local TLS/demo proxy posture is documented and reflected in platform-status surfaces, but it still reads as a deployment support story rather than a fully productized control plane surface. |
| 9.14 | Deployment profiles | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Deployment profiles are real in compose/docs and reflected by the platform story, but they remain infrastructure-facing support material rather than a finished in-product managed surface. |
