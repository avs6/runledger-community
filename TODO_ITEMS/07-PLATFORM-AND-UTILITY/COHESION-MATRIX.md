# Platform & Utility — Cohesion Matrix

Last updated: PENDING AUDIT

This file tracks how Platform & Utility features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

This section applies the same matrix structure to `Platform` and the currently minimal `Additional Admin / Utility Routes` surface.

Current row major feature under audit: `Platform / Utility`

### 11.8a Platform / Utility x FinOps / Organization & Access / Self

| Row Major Feature | Row Subfeature | Budgets | Billing periods | Chargeback | Ledger | Organization profile | Onboarding | Workspaces | API keys | All organizations | Platform settings | Plugins | Finding |
|-------------------|----------------|---------|-----------------|------------|--------|----------------------|------------|------------|----------|-------------------|-------------------|---------|---------|
| Platform / Utility | All organizations | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | All Organizations is the true platform-admin lifecycle owner and should remain the parent to org creation and suspension. |
| Platform / Utility | Platform settings | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Platform Settings is strategically important as a convergence surface, but is still an umbrella rather than one cohesive product area. |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | Plugins is now correctly collapsed under onboarding/discovery rather than preserved as a first-class admin plane. |

### 11.8b Platform / Utility x Gateway / Observe / Governance / Build

| Row Major Feature | Row Subfeature | Model gateway | Guardrails | Monitoring | Telemetry | Audit log | Governance pack | Evaluation studio | Optimization simulator | Finding |
|-------------------|----------------|---------------|------------|------------|-----------|-----------|-----------------|-------------------|------------------------|---------|
| Platform / Utility | All organizations | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Platform org management should summarize downstream posture, but not absorb each control plane. |
| Platform / Utility | Platform settings | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Platform Settings is already the clearest home for cross-cutting compliance and operational defaults. |
| Platform / Utility | Plugins | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | Plugins now belong in the guided onboarding and tool-connection story, not in a separate ops island. |
