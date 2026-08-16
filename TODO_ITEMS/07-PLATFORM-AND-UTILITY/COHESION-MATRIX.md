# Platform & Utility — Cohesion Matrix

Last updated: 2026-08-15

This file tracks how Platform & Utility features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

This section applies the same matrix structure to `Platform` and the currently minimal `Additional Admin / Utility Routes` surface.

Current row major feature under audit: `Platform / Utility`

### 11.8a Platform / Utility x FinOps / Organization & Access / Self

| Row Major Feature | Row Subfeature | Budgets | Billing periods | Chargeback | Ledger | Organization profile | Onboarding | Workspaces | API keys | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|---------|-----------------|------------|--------|----------------------|------------|------------|----------|-------------------|-------------------|---------|---------|
| Platform / Utility | All organizations | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | All organizations is the platform-admin counterpart to org profile (STRONG). Creates default workspace on org creation (STRONG to Workspaces). Shares require_platform_admin context with Platform settings (STRONG). Orgs scope budgets, billing, chargeback, and ledger but no direct management from this page (PARTIAL). API keys and onboarding are org-scoped but managed elsewhere (PARTIAL). |
| Platform / Utility | Platform settings | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `N/A` | Compliance tab manages ledger closures and snapshots directly (STRONG to Ledger). Shares require_platform_admin/require_org_admin context with All organizations (STRONG). Webhook defaults include budget.breach events (PARTIAL to Budgets). Retention/capture policy affects billing and chargeback data (PARTIAL). API keys, onboarding-status, org profile, and workspaces are settings sub-endpoints but managed on their own pages (PARTIAL). |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | UI redirects to /onboarding?section=connections (STRONG to Onboarding). Backend plugin management is used programmatically by MCP governance, and the plugins route still has a real self-relationship even though the UI surface is collapsed. |

### 11.8b Platform / Utility x Gateway / Observe / Governance / Build

| Row Major Feature | Row Subfeature | Model gateway | Guardrails | Monitoring | Telemetry | Audit log | Governance pack | Evaluation studio | Optimization simulator | Finding |
|-------------------|----------------|---------------|------------|------------|-----------|-----------|-----------------|-------------------|------------------------|---------|
| Platform / Utility | All organizations | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | Orgs contain workspaces with gateway routes, guardrails, telemetry, and downstream evaluation/optimization posture, but no direct management from this page (PARTIAL). Org console has /org/audit-log endpoint (PARTIAL to Audit log). Governance is org-scoped (PARTIAL). |
| Platform / Utility | Platform settings | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | Retention, compliance, and backup are governance pack components (STRONG). Capture policy interacts with guardrail data (PARTIAL). Ops status/queues are monitoring primitives (PARTIAL). Backup/retention operations should produce audit events (PARTIAL). Onboarding-status checks telemetry setup (PARTIAL). Platform defaults and compliance posture still have a real but indirect relationship to the gateway runtime. |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | Collapsed redirect — backend plugin governance is consumed by MCP tool calls and the UI route effectively feeds the onboarding/tool-connection story, so Evaluation Studio at least has a light adjacent relationship. |
