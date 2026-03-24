"""
Feature gating for RunLedger OSS / Cloud / Enterprise editions.

Tiers (set via RUNLEDGER_MODE env var):
  oss        — self-hosted open-source; observability, basic analytics, local SDK
  cloud      — managed SaaS; adds reconciliation, chargeback, advanced routing,
               budgets with enforcement, outcome ledger, warehouse export, alerts
  enterprise — cloud + SSO/SCIM, advanced RBAC, audit/retention, BYOK/KMS

Gates raise HTTP 402 when the running mode is below the required tier.

Usage
-----
  from runledger_api.core.feature_gate import require_cloud, require_enterprise

  @router.post("/invoices/{id}/reconcile")
  async def reconcile(...):
      require_cloud("Invoice reconciliation")
      ...

  @router.get("/auth/sso/...")
  async def sso_authorize(...):
      require_enterprise("SSO / OIDC")
      ...
"""

from __future__ import annotations

_TIER_ORDER = {"oss": 0, "cloud": 1, "enterprise": 2}


def _current_tier() -> int:
    from runledger_api.core.config import settings  # noqa: PLC0415

    return _TIER_ORDER.get(settings.runledger_mode, 0)


def require_cloud(feature_name: str) -> None:
    """Raise HTTP 402 if running below Cloud tier (i.e. in OSS mode)."""
    if _current_tier() < _TIER_ORDER["cloud"]:
        from fastapi import HTTPException  # noqa: PLC0415

        raise HTTPException(
            status_code=402,
            detail=(
                f"{feature_name} requires RunLedger Cloud or Enterprise. "
                "Set RUNLEDGER_MODE=cloud to enable."
            ),
        )


def require_enterprise(feature_name: str) -> None:
    """Raise HTTP 402 if running below Enterprise tier."""
    if _current_tier() < _TIER_ORDER["enterprise"]:
        from fastapi import HTTPException  # noqa: PLC0415

        raise HTTPException(
            status_code=402,
            detail=(
                f"{feature_name} requires RunLedger Enterprise. "
                "Set RUNLEDGER_MODE=enterprise to enable."
            ),
        )
