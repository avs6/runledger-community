"""
Tests for the license-based feature gate system.

Covers:
- License parsing and HMAC verification
- Community / enterprise / grace-period / expired states
- require_enterprise() and require_feature() gate functions
- SaaS mode bypass
- Legacy RUNLEDGER_MODE=enterprise synthetic license
- Structured HTTP 402 error body
- License issuance round-trip
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

# ── Fixtures & helpers ────────────────────────────────────────────────────────

_SIGNING_KEY = "test-signing-key-32bytes-for-tests"


def _issue(
    org: str = "Test Corp",
    edition: str = "enterprise",
    features: list[str] | None = None,
    seats: int = 0,
    expires_offset_days: int | None = 365,
) -> str:
    from datetime import timedelta

    from runledger_api.core.license import _ALL_FEATURES, _today, issue_license

    if features is None:
        features = sorted(_ALL_FEATURES)

    expires = (
        _today() + timedelta(days=expires_offset_days) if expires_offset_days is not None else None
    )
    return issue_license(
        org=org,
        edition=edition,
        features=features,
        seats=seats,
        expires=expires,
        signing_key=_SIGNING_KEY,
    )


# ── License parsing ────────────────────────────────────────────────────────────


def test_parse_license_roundtrip() -> None:
    from runledger_api.core.license import parse_license

    key = _issue(features=["sso", "warehouse"], expires_offset_days=365)
    lic = parse_license(key, _SIGNING_KEY)
    assert lic.status == "valid"
    assert lic.org == "Test Corp"
    assert lic.edition == "enterprise"
    assert "sso" in lic.features
    assert "warehouse" in lic.features
    assert lic.days_until_expiry is not None and lic.days_until_expiry > 0


def test_perpetual_license_never_expires() -> None:
    from runledger_api.core.license import parse_license

    key = _issue(expires_offset_days=None)
    lic = parse_license(key, _SIGNING_KEY)
    assert lic.status == "valid"
    assert lic.days_until_expiry is None
    assert not lic.is_hard_expired()


def test_tampered_signature_raises_error() -> None:
    from runledger_api.core.license import LicenseError, parse_license

    key = _issue()
    tampered = key[:-4] + "XXXX"
    with pytest.raises(LicenseError, match="signature invalid"):
        parse_license(tampered, _SIGNING_KEY)


def test_wrong_signing_key_raises_error() -> None:
    from runledger_api.core.license import LicenseError, parse_license

    key = _issue()
    with pytest.raises(LicenseError, match="signature invalid"):
        parse_license(key, "wrong-signing-key")


def test_malformed_key_raises_error() -> None:
    from runledger_api.core.license import LicenseError, parse_license

    with pytest.raises(LicenseError, match="Malformed"):
        parse_license("rl_lic_notavalidkey", _SIGNING_KEY)


def test_grace_period_status() -> None:
    from runledger_api.core.license import parse_license

    key = _issue(expires_offset_days=-7)  # expired 7 days ago
    lic = parse_license(key, _SIGNING_KEY)
    assert lic.status == "grace_period"
    assert lic.days_until_expiry == -7
    assert not lic.is_hard_expired()


def test_hard_expired_status() -> None:
    from runledger_api.core.license import parse_license

    key = _issue(expires_offset_days=-20)  # 20 days past expiry
    lic = parse_license(key, _SIGNING_KEY)
    assert lic.status == "expired"
    assert lic.is_hard_expired()


# ── Feature gate — community ────────────────────────────────────────────────────


def test_community_license_blocks_enterprise_feature(
    oss_license: object,
) -> None:
    from runledger_api.core.feature_gate import require_enterprise

    with pytest.raises(HTTPException) as exc_info:
        require_enterprise("Test Feature")
    assert exc_info.value.status_code == 402
    detail = exc_info.value.detail
    assert detail["code"] == "feature_not_licensed"
    assert detail["current_edition"] == "community"


def test_community_license_blocks_require_feature(
    oss_license: object,
) -> None:
    from runledger_api.core.feature_gate import require_feature

    with pytest.raises(HTTPException) as exc_info:
        require_feature("sso", "SSO / OIDC")
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["feature"] == "sso"


# ── Feature gate — enterprise valid ───────────────────────────────────────────


def test_enterprise_license_with_flag_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    from runledger_api.core import license as _lic
    from runledger_api.core.feature_gate import require_feature

    monkeypatch.setattr(
        _lic,
        "_license_cache",
        _lic._make_test_license(edition="enterprise", features=frozenset(["sso", "warehouse"])),
    )
    # Should not raise
    require_feature("sso", "SSO / OIDC")
    require_feature("warehouse", "Warehouse export")


def test_enterprise_license_missing_flag_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    from runledger_api.core import license as _lic
    from runledger_api.core.feature_gate import require_feature

    monkeypatch.setattr(
        _lic,
        "_license_cache",
        _lic._make_test_license(edition="enterprise", features=frozenset(["sso"])),
    )
    with pytest.raises(HTTPException) as exc_info:
        require_feature("warehouse", "Warehouse export")
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["feature"] == "warehouse"
    assert exc_info.value.detail["current_edition"] == "enterprise"


# ── Feature gate — expired ─────────────────────────────────────────────────────


def test_expired_license_hard_blocks(expired_license: object) -> None:
    from runledger_api.core.feature_gate import require_enterprise

    with pytest.raises(HTTPException) as exc_info:
        require_enterprise("Invoice reconciliation")
    assert exc_info.value.status_code == 402
    assert "expired" in exc_info.value.detail["message"].lower()


def test_grace_period_allows_with_warning(grace_period_license: object) -> None:
    """Grace period: require_enterprise passes (no exception raised)."""
    from runledger_api.core.feature_gate import require_enterprise

    # Should NOT raise — grace period licenses are allowed through
    require_enterprise("Invoice reconciliation")


# ── Feature gate — SaaS bypass ─────────────────────────────────────────────────


def test_saas_mode_bypasses_all_gates(monkeypatch: pytest.MonkeyPatch, oss_license: object) -> None:
    from runledger_api.core import config as _cfg
    from runledger_api.core.feature_gate import require_enterprise, require_feature

    monkeypatch.setattr(_cfg.settings, "runledger_mode", "saas")
    # Even with a community license, SaaS mode bypasses gates
    require_enterprise("Any Feature")
    require_feature("sso", "SSO / OIDC")


# ── Legacy enterprise mode ────────────────────────────────────────────────────


def test_legacy_enterprise_mode_has_all_features() -> None:
    from runledger_api.core.license import _ALL_FEATURES, _legacy_enterprise_license

    lic = _legacy_enterprise_license()
    assert lic.edition == "enterprise"
    assert lic.status == "valid"
    assert lic.features == _ALL_FEATURES


# ── Structured 402 error body ─────────────────────────────────────────────────


def test_structured_402_error_body(oss_license: object) -> None:
    from runledger_api.core.feature_gate import require_feature

    with pytest.raises(HTTPException) as exc_info:
        require_feature("sso", "SSO / OIDC")

    detail = exc_info.value.detail
    assert detail["code"] == "feature_not_licensed"
    assert detail["feature"] == "sso"
    assert detail["display_name"] == "SSO / OIDC"
    assert "message" in detail
    assert "upgrade_url" in detail
    assert detail["upgrade_url"] == "https://runledger.io/pricing"


# ── get_license_info ──────────────────────────────────────────────────────────


def test_get_license_info_shape() -> None:
    from runledger_api.core.feature_gate import get_license_info

    info = get_license_info()
    assert "edition" in info
    assert "status" in info
    assert "org" in info
    assert "features" in info
    assert "expires" in info
