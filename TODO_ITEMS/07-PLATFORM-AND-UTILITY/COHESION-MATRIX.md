# Platform & Utility — Cohesion Matrix

Last updated: 2026-09-03 (07-PLATFORM WU-001)

This file tracks how Platform & Utility features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

This section applies the same matrix structure to `Platform` and the currently minimal `Additional Admin / Utility Routes` surface.

Current row major feature under audit: `Platform / Utility`

### 11.8a Platform / Utility x FinOps / Organization & Access / Self

| Row Major Feature | Row Subfeature | Budgets | Billing periods | Chargeback | Ledger | Organization profile | Onboarding | Workspaces | API keys | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|---------|-----------------|------------|--------|----------------------|------------|------------|----------|-------------------|-------------------|---------|---------|
| Platform / Utility | All organizations | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `STRONG` | `N/A` | WU-013 added Ledger Cross-Feature Posture endpoint with platform context (organizations). Ledger P→S. Prior WU-011 strengthens Billing periods: cross-org billing period rollups now surface in the platform posture view alongside budget totals. Billing periods P→S. WU-012 strengthens Chargeback: cross-org chargeback rule coverage is now visible in the same posture rollup. Chargeback P→S. Prior: 05-FINOPS WU-006 adds Budget Control Platform Posture card (emerald) to All Organizations via `GET /analytics/budget-control-platform-posture` with cross-org budget totals, per-org breakdowns, override context, and 30d spend. Budgets P→S. Prior: Creates default workspace on org creation (STRONG to Workspaces). Shares require_platform_admin context with Platform settings (STRONG). |
| Platform / Utility | Platform settings | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `STRONG` | `PARTIAL` | `N/A` | WU-011 strengthens Billing periods: platform-wide billing period administration now surfaces directly in the platform posture view. Billing periods P→S. WU-012 strengthens Chargeback: platform admins can now see cross-org chargeback rule coverage in the same posture rollup. Chargeback P→S. Prior: 05-FINOPS WU-006 adds Budget Control Platform Posture card (emerald) to Platform Settings via `GET /analytics/budget-control-platform-posture` with cross-org budget totals, per-org breakdowns, override context, and 30d spend. Budgets P→S. Prior: Compliance tab manages ledger closures and snapshots directly (STRONG to Ledger). Webhook defaults include budget.breach events. |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | `N/A` | `N/A` | `N/A` | `N/A` | `STRONG` | UI redirects to /onboarding?section=connections (STRONG to Onboarding). Backend plugin management is used programmatically by MCP governance, and the plugins route still has a real self-relationship even though the UI surface is collapsed. |

### 11.8b Platform / Utility x Gateway / Observe / Governance / Build

| Row Major Feature | Row Subfeature | Model gateway | Guardrails | Monitoring | Telemetry | Audit log | Governance pack | Evaluation studio | Optimization simulator | Finding |
|-------------------|----------------|---------------|------------|------------|-----------|-----------|-----------------|-------------------|------------------------|---------|
| Platform / Utility | All organizations | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | WU-001 adds platform lifecycle posture endpoint (`GET /analytics/platform-lifecycle-posture`) with governance context including audit_events_30d, tool_policies, and alert_rules. Organizations page now shows Governance & Audit posture card (amber) with Audit Log drill-through. Audit log P→S. Prior: Gateway page links to All Organizations. Provider Profiles and Guardrails pages link to All Organizations. Model gateway, provider profiles, and guardrails are now fully platform-visible (STRONG). |
| Platform / Utility | Platform settings | `STRONG` | `STRONG` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `STRONG` | `N/A` | `N/A` | GET /analytics/gateway-internal-posture returns provider count, guardrails, cache, and throttle context with platform visibility. Gateway page Gateway Family Internal Cohesion card links to Platform Settings. Provider Profiles and Guardrails pages link to Platform Settings. Model gateway, provider profiles, and guardrails are now fully platform-visible (STRONG). Retention, compliance, and backup are governance pack components (STRONG). |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PARTIAL` | `N/A` | Collapsed redirect — backend plugin governance is consumed by MCP tool calls and the UI route effectively feeds the onboarding/tool-connection story, so Evaluation Studio at least has a light adjacent relationship. |
