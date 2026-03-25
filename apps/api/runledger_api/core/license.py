"""
RunLedger License — parse, validate, and cache signed license keys.

License key format
------------------
  rl_lic_<base64url(payload_json)>.<base64url(hmac_sha256(payload_bytes, signing_key))>

The signing key is held only by the RunLedger vendor and set as
RUNLEDGER_LICENSE_SIGNING_KEY in the vendor's environment.  Customers only
ever see the signed opaque token (RUNLEDGER_LICENSE_KEY).  Validation is
fully offline — no phone-home required.

Editions
--------
  community  — default when no license key is present (OSS feature set)
  enterprise — requires a valid signed license key with named feature flags

Grace period
------------
  Days 1-14 after expiry: gates pass, startup WARNING logged.
  Day 15+: gates hard-block with HTTP 402.

Usage
-----
  from runledger_api.core.license import get_license, require_valid_enterprise

  lic = get_license()
  if lic.has_feature("sso"):
      ...
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Literal

import structlog

log = structlog.get_logger()

_GRACE_DAYS = 14
_PREFIX = "rl_lic_"
_ALL_FEATURES = frozenset(
    [
        "invoice_reconciliation",
        "chargeback_rules",
        "cost_centers",
        "routing_policies",
        "pricing_contracts",
        "pricing_credits",
        "sso",
        "sso_config",
        "warehouse",
        "audit_log",
        "byok",
        "scim",
    ]
)

LicenseStatus = Literal["valid", "grace_period", "expired", "community"]


# ── Data types ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class LicensePayload:
    lid: str
    org: str
    edition: str  # "community" | "enterprise"
    features: frozenset[str]
    seats: int  # 0 = unlimited
    issued: date
    expires: date | None  # None = perpetual
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedLicense:
    payload: LicensePayload
    status: LicenseStatus
    days_until_expiry: int | None  # negative = days past expiry

    def has_feature(self, flag: str) -> bool:
        """Return True if this license includes the named feature flag."""
        return flag in self.payload.features

    def is_enterprise(self) -> bool:
        return self.payload.edition == "enterprise"

    def is_hard_expired(self) -> bool:
        """True when the license is past the grace period (more than _GRACE_DAYS past expiry)."""
        return self.status == "expired"

    @property
    def org(self) -> str:
        return self.payload.org

    @property
    def edition(self) -> str:
        return self.payload.edition

    @property
    def features(self) -> frozenset[str]:
        return self.payload.features


# ── Parse / verify ─────────────────────────────────────────────────────────────


class LicenseError(ValueError):
    """Raised when a license key is malformed, has a bad signature, or is missing."""


def _b64url_decode(s: str) -> bytes:
    """Decode URL-safe base64 without padding."""
    # Add padding as required by the standard decoder
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _b64url_encode(b: bytes) -> str:
    """Encode bytes to URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _today() -> date:
    return datetime.now(UTC).date()


def _compute_status(expires: date | None) -> tuple[LicenseStatus, int | None]:
    if expires is None:
        return "valid", None
    today = _today()
    delta = (expires - today).days  # positive = days remaining, negative = days past
    if delta >= 0:
        return "valid", delta
    if delta >= -_GRACE_DAYS:
        return "grace_period", delta
    return "expired", delta


def parse_license(key: str, signing_key: str) -> ParsedLicense:
    """
    Parse and cryptographically verify a license key string.

    Raises LicenseError on any validation failure (bad format, bad signature,
    missing required fields).  Returns a ParsedLicense with computed status.
    """
    if not signing_key:
        raise LicenseError("License signing key not configured (RUNLEDGER_LICENSE_SIGNING_KEY)")

    token = key.removeprefix(_PREFIX)
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        raise LicenseError("Malformed license key: expected <payload>.<signature>")

    encoded_payload, encoded_sig = parts

    try:
        payload_bytes = _b64url_decode(encoded_payload)
        sig_bytes = _b64url_decode(encoded_sig)
    except Exception as exc:
        raise LicenseError(f"License key base64 decode error: {exc}") from exc

    expected = hmac.new(signing_key.encode(), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig_bytes):
        raise LicenseError("License key signature invalid")

    try:
        data: dict[str, Any] = json.loads(payload_bytes)
    except json.JSONDecodeError as exc:
        raise LicenseError(f"License payload JSON error: {exc}") from exc

    required = ("lid", "org", "edition", "features", "seats", "issued")
    missing = [f for f in required if f not in data]
    if missing:
        raise LicenseError(f"License payload missing fields: {missing}")

    if data["edition"] not in ("community", "enterprise"):
        raise LicenseError(f"Unknown license edition: {data['edition']!r}")

    try:
        issued = date.fromisoformat(data["issued"])
        expires = date.fromisoformat(data["expires"]) if data.get("expires") else None
    except ValueError as exc:
        raise LicenseError(f"License date parse error: {exc}") from exc

    features = frozenset(data["features"])
    status, days = _compute_status(expires)

    payload = LicensePayload(
        lid=data["lid"],
        org=data["org"],
        edition=data["edition"],
        features=features,
        seats=int(data["seats"]),
        issued=issued,
        expires=expires,
        meta=data.get("meta", {}),
    )
    return ParsedLicense(payload=payload, status=status, days_until_expiry=days)


# ── Well-known license objects ──────────────────────────────────────────────────


def _community_license() -> ParsedLicense:
    payload = LicensePayload(
        lid="community",
        org="Self-hosted Community",
        edition="community",
        features=frozenset(),
        seats=0,
        issued=date(2024, 1, 1),
        expires=None,
    )
    return ParsedLicense(payload=payload, status="community", days_until_expiry=None)


def _legacy_enterprise_license() -> ParsedLicense:
    """
    Synthetic unlimited enterprise license for RUNLEDGER_MODE=enterprise.
    Used during the transition period and in tests.
    """
    payload = LicensePayload(
        lid="legacy-enterprise",
        org="Self-hosted (legacy mode)",
        edition="enterprise",
        features=_ALL_FEATURES,
        seats=0,
        issued=date(2024, 1, 1),
        expires=None,
    )
    return ParsedLicense(payload=payload, status="valid", days_until_expiry=None)


def _make_test_license(
    edition: str = "enterprise",
    features: frozenset[str] | None = None,
    expires_offset_days: int | None = None,
    seats: int = 0,
) -> ParsedLicense:
    """
    Build a synthetic ParsedLicense for use in tests only.
    expires_offset_days: positive = expires in N days, negative = expired N days ago, None = perpetual
    """
    expires: date | None = None
    if expires_offset_days is not None:
        from datetime import timedelta  # noqa: PLC0415

        expires = _today() + timedelta(days=expires_offset_days)

    status, days = _compute_status(expires)
    if edition == "community":
        status = "community"

    payload = LicensePayload(
        lid=f"test-{uuid.uuid4().hex[:8]}",
        org="Test Org",
        edition=edition,
        features=features if features is not None else _ALL_FEATURES,
        seats=seats,
        issued=_today(),
        expires=expires,
    )
    return ParsedLicense(payload=payload, status=status, days_until_expiry=days)


# ── Module-level cache ─────────────────────────────────────────────────────────

_license_cache: ParsedLicense | None = None
_license_lock = threading.Lock()


def get_license() -> ParsedLicense:
    """
    Return the current parsed license, loading it on first call.
    Thread-safe; parses once at startup and caches indefinitely.
    """
    global _license_cache  # noqa: PLW0603
    if _license_cache is not None:
        return _license_cache
    with _license_lock:
        if _license_cache is not None:
            return _license_cache
        _license_cache = _load_license()
        return _license_cache


def reset_license_cache() -> None:
    """Clear the module-level cache. Used in tests only."""
    global _license_cache  # noqa: PLW0603
    _license_cache = None


def _load_license() -> ParsedLicense:
    from runledger_api.core.config import settings  # noqa: PLC0415

    # Legacy compatibility: RUNLEDGER_MODE=enterprise → synthetic unlimited license
    if settings.runledger_mode == "enterprise":
        log.info(
            "license_mode_legacy_enterprise",
            msg="RUNLEDGER_MODE=enterprise detected — using synthetic unlimited license. "
            "Migrate to RUNLEDGER_LICENSE_KEY for production use.",
        )
        return _legacy_enterprise_license()

    key = settings.runledger_license_key
    if not key:
        log.info(
            "license_community", msg="No RUNLEDGER_LICENSE_KEY set — running in community edition"
        )
        return _community_license()

    signing_key = settings.runledger_license_signing_key
    try:
        lic = parse_license(key, signing_key)
    except LicenseError as exc:
        log.error("license_parse_failed", error=str(exc))
        # Fail open to community rather than crashing the process —
        # the gate functions will block enterprise features.
        return _community_license()

    if lic.status == "grace_period":
        log.warning(
            "license_grace_period",
            org=lic.org,
            days_past_expiry=-(lic.days_until_expiry or 0),
            days_remaining_in_grace=_GRACE_DAYS + (lic.days_until_expiry or 0),
        )
    elif lic.status == "expired":
        log.error(
            "license_hard_expired",
            org=lic.org,
            days_past_expiry=-(lic.days_until_expiry or 0),
        )
    else:
        log.info(
            "license_loaded",
            org=lic.org,
            edition=lic.edition,
            features=sorted(lic.features),
            seats=lic.payload.seats,
            expires=lic.payload.expires.isoformat() if lic.payload.expires else "perpetual",
        )

    return lic


def get_license_info() -> dict[str, Any]:
    """
    Return a safe info dict for /health/ready and admin endpoints.
    Never exposes the signing key or raw license token.
    """
    lic = get_license()
    info: dict[str, Any] = {
        "edition": lic.edition,
        "status": lic.status,
        "org": lic.org,
        "seats": lic.payload.seats,
        "features": sorted(lic.features),
        "expires": lic.payload.expires.isoformat() if lic.payload.expires else "perpetual",
        "days_until_expiry": lic.days_until_expiry,
    }
    return info


# ── License issuance (vendor only) ─────────────────────────────────────────────


def issue_license(
    org: str,
    edition: str,
    features: list[str],
    seats: int,
    expires: date | None,
    signing_key: str,
    lid: str | None = None,
) -> str:
    """
    Issue a signed license key string.  Requires the vendor signing key.
    Returns the full rl_lic_... token.
    """
    if not signing_key:
        raise LicenseError("Signing key is required to issue a license")
    if edition not in ("community", "enterprise"):
        raise LicenseError(f"Invalid edition: {edition!r}")

    payload_data: dict[str, Any] = {
        "lid": lid or f"lic_{uuid.uuid4().hex}",
        "org": org,
        "edition": edition,
        "features": sorted(features),
        "seats": seats,
        "issued": _today().isoformat(),
        "expires": expires.isoformat() if expires else None,
        "meta": {},
    }
    payload_bytes = json.dumps(payload_data, separators=(",", ":")).encode()
    sig = hmac.new(signing_key.encode(), payload_bytes, hashlib.sha256).digest()

    return f"{_PREFIX}{_b64url_encode(payload_bytes)}.{_b64url_encode(sig)}"
