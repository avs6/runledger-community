"""Feature gating helper for RunLedger OSS vs Cloud."""

from __future__ import annotations


def require_cloud(feature_name: str) -> None:
    """Raise HTTP 402 if not running in cloud mode.

    Call this at the top of endpoints that are paywalled in Phase 14.
    """
    from runledger_api.core.config import settings  # noqa: PLC0415

    if settings.runledger_mode != "cloud":
        from fastapi import HTTPException  # noqa: PLC0415

        raise HTTPException(
            status_code=402,
            detail=f"{feature_name} requires RunLedger Cloud.",
        )
