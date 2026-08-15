# Observe — Cohesion Matrix

Last updated: PENDING AUDIT

This file tracks how Observe features relate to all other major feature families. Each cell is `STRONG`, `PARTIAL`, `GAP`, or `N/A`.

When a cohesion cell changes, update BOTH this file AND the paired feature's COHESION-MATRIX.md.

---

Current row major feature under audit: `Observe`

### 11.5 Observe Cohesion Matrix

This section applies the same matrix structure to `Observe` against the rest of the shipped feature surface.

Current row major feature under audit: `Observe`

### 11.5a Observe x FinOps

| Row Major Feature | Row Subfeature | Budgets | Budget detail | Budget overrides | Budget notifications | Billing periods | Billing period detail | Chargeback | Ledger | Finding |
|-------------------|----------------|---------|---------------|------------------|----------------------|-----------------|-----------------------|------------|--------|---------|
| Observe | Analytics overview | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Analytics overview consumes economics context well, but it is still not anchored cleanly to the FinOps control plane. |
| Observe | Runs list | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Runs should become easier to explain through budget, quota, and allocation context. |
| Observe | Run detail | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Run detail has the raw data to support FinOps explanations, but the product bridges are still thin. |
| Observe | Request flow | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Request Flow is a natural place to visualize financial and quota impacts, but that linkage is still immature. |
| Observe | Request explorer | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Request Explorer should be one of the strongest surfaces for cost attribution and budget debugging. |
| Observe | Model usage | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Model Usage already shares a strong natural relationship with provider cost, but budget and billing bridges can deepen. |
| Observe | Analytics economics | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Observe is already strongest where it overlaps with economics and billing, which is a good base for deeper FinOps cohesion. |
| Observe | Cost and savings | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Cost and Savings is already a natural FinOps companion and should keep tightening to the budget control plane. |
| Observe | Outcomes and ROI | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Outcomes and ROI should become a clearer top-layer consumer of spend and chargeback data. |
| Observe | Monitoring | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | Monitoring should increasingly show the operational consequences of spend controls and thresholds. |

### 11.5b Observe x Organization & Access

| Row Major Feature | Row Subfeature | Organization profile | Org settings | Onboarding | Users | Workspaces | Access groups | API keys | Integrations | Telemetry | MCP registry | AI hub | Projects | Team models | Finding |
|-------------------|----------------|----------------------|--------------|------------|-------|------------|---------------|----------|--------------|-----------|--------------|--------|----------|-------------|---------|
| Observe | Analytics overview | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | Observe already inherits workspace and org scope well, but access-group and API-key scope need strengthening. |
| Observe | Runs list | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Runs are strongly workspace-native, but weaker for access-group and key-centric investigation. |
| Observe | Run detail | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Run detail should increasingly expose identity and scope provenance more explicitly. |
| Observe | Request flow | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Request Flow is one of the best candidates for deeper scope-aware observability. |
| Observe | Request explorer | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Request Explorer should become a stronger bridge to access groups and API-key identity. |
| Observe | Model usage | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | Model Usage and AI Hub already form a strong model-intelligence pair. |
| Observe | Analytics users | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | User analytics is the clearest existing Observe bridge to the user-management surface. |
| Observe | Telemetry | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | Telemetry is already correctly placed in Observe, with scope inheritance still improving. |
| Observe | Monitoring | `PENDING` | `N/A` | `PENDING` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | Monitoring and telemetry together should become the clearest operational reflection of scope posture. |
| Observe | Model scorecards | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `N/A` | `N/A` | Scorecards already align well with AI Hub and workspace model ownership. |

### 11.5c Observe x Gateway & Routing / Safety & Governance / Self

| Row Major Feature | Row Subfeature | Provider profiles | Model gateway | Guardrails | Response cache | Rate limits | Tool registry | Tool policies | Approvals | Data capture | Security | Alert rules | Audit log | Governance pack | Tags | Analytics overview | Runs list | Request flow | Request explorer | Monitoring | Finding |
|-------------------|----------------|-------------------|---------------|------------|----------------|-------------|---------------|---------------|-----------|--------------|----------|-------------|-----------|-----------------|------|--------------------|-----------|--------------|------------------|------------|---------|
| Observe | Analytics overview | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Analytics overview is the suite’s observability front door, but it should connect more explicitly to runtime governance and gateway posture. |
| Observe | Runs list | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Runs are already one of the strongest bridge entities between runtime, governance, and investigation. |
| Observe | Run detail | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Run detail should remain a core correlation surface across the suite. |
| Observe | Request flow | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Request Flow is one of the strongest runtime-to-observability bridges and should keep deepening. |
| Observe | Request explorer | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Request Explorer already sits near the center of investigative cohesion. |
| Observe | Model usage | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | Model Usage and provider profiles are one of the clearest cross-feature joins in the product. |
| Observe | Monitoring | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Monitoring is already a strong operational hub and should continue converging runtime and governance signals. |
| Observe | Telemetry | `N/A` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Telemetry is now correctly treated as observability rather than integration setup. |
| Observe | Analytics economics | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Analytics economics is internally cohesive, but should remain an overview bridge rather than a competing deep-dive owner. |
| Observe | Cost and savings | `PENDING` | `PENDING` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | `PENDING` | Cost and Savings is already cohesive with the economics layer and should stay clearly positioned there. |

