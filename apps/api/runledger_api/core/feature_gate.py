"""
Feature gating for RunLedger Community / Enterprise / SaaS editions.

Gates are enforced via a cryptographically-signed license key
(RUNLEDGER_LICENSE_KEY) rather than a plain environment variable string.
The license key is validated fully offline — no phone-home required.

Editions
--------
  Community   — no license key; OSS feature set
  Enterprise  — valid signed RUNLEDGER_LICENSE_KEY with named feature flags
  SaaS        — RUNLEDGER_MODE=saas; license check bypassed, Stripe handles it
  Legacy      — RUNLEDGER_MODE=enterprise; synthetic unlimited license (transition)

Named feature flags
-------------------
  invoice_reconciliation   chargeback_rules    cost_centers
  routing_policies         pricing_contracts   pricing_credits
  sso                      sso_config          warehouse
  audit_log                byok                scim

Usage
-----
  from runledger_api.core.feature_gate import require_feature, get_license_info

  @router.post("/warehouse/destinations")
  async def create_destination(...):
      require_feature("warehouse", "Warehouse export")
      ...

  @router.get("/auth/sso/authorize/{id}")
  async def sso_authorize(...):
      require_feature("sso", "SSO / OIDC")
      ...
"""

from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger()


def _is_saas() -> bool:
    from runledger_api.core.config import settings  # noqa: PLC0415

    return settings.runledger_mode == "saas"


def _check_license(flag: str, display_name: str) -> None:
    """
    Core gate logic shared by require_enterprise and require_feature.

    flag         — machine-readable feature flag (e.g. "sso") or the display name
                   when called from require_enterprise directly
    display_name — human-readable name shown in error messages
    """
    if _is_saas():
        return

    from runledger_api.core.license import get_license  # noqa: PLC0415

    lic = get_license()

    if lic.status == "community":
        _raise_402(
            feature=flag,
            display_name=display_name,
            current_edition="community",
            message=(
                f"{display_name} requires a RunLedger Enterprise license. "
                "Set RUNLEDGER_LICENSE_KEY in your environment."
            ),
        )

    if lic.is_hard_expired():
        _raise_402(
            feature=flag,
            display_name=display_name,
            current_edition="enterprise",
            message=(
                f"{display_name} requires an active Enterprise license. "
                f"Your license expired on {lic.payload.expires} "
                f"(grace period ended). Renew at https://runledger.io/pricing"
            ),
        )

    if lic.status == "grace_period":
        days_left = (lic.days_until_expiry or 0) + 14  # days remaining in grace
        log.warning(
            "license_grace_period_access",
            feature=flag,
            days_remaining_in_grace=days_left,
        )


def require_community(feature_name: str) -> None:
    """
    No-op gate — documents that a feature is available in the Community edition.
    Calling this has no runtime effect; it exists for self-documenting code.
    """


def require_enterprise(feature_name: str) -> None:
    """
    Raise HTTP 402 if no valid enterprise license is active.

    Bypassed entirely when RUNLEDGER_MODE=saas (Stripe handles quota/access).
    Grace-period licenses pass but log a WARNING.
    Hard-expired licenses (>14 days past expiry) raise HTTP 402.
    """
    _check_license(flag=feature_name, display_name=feature_name)


def require_feature(flag: str, display_name: str) -> None:
    """
    Raise HTTP 402 if the specific feature flag is not included in the license.

    More fine-grained than require_enterprise — checks the named flag explicitly
    so customers can have partial enterprise licenses (e.g. enterprise without
    warehouse if not contracted for it).
    """
    # Run all base checks (community, expired, grace) with the flag name so the
    # error detail always carries the machine-readable flag, not the display name.
    _check_license(flag=flag, display_name=display_name)

    if _is_saas():
        return

    from runledger_api.core.license import get_license  # noqa: PLC0415

    lic = get_license()
    if not lic.has_feature(flag):
        _raise_402(
            feature=flag,
            display_name=display_name,
            current_edition=lic.edition,
            message=(
                f"{display_name} requires an Enterprise license with the "
                f"'{flag}' feature enabled. Contact sales to add it to your license."
            ),
        )


def get_license_info() -> dict[str, Any]:
    """
    Return a safe info dict for /health/ready and admin endpoints.
    Never exposes the raw license token or signing key.
    """
    from runledger_api.core.license import get_license_info as _info  # noqa: PLC0415

    return _info()


def _raise_402(
    feature: str,
    display_name: str,
    current_edition: str,
    message: str,
) -> None:
    from fastapi import HTTPException  # noqa: PLC0415

    raise HTTPException(
        status_code=402,
        detail={
            "code": "feature_not_licensed",
            "feature": feature,
            "display_name": display_name,
            "message": message,
            "current_edition": current_edition,
            "upgrade_url": "https://runledger.io/pricing",
        },
    )
