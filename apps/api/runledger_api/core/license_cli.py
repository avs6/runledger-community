"""
RunLedger License CLI — issue and verify signed license keys.

Usage (vendor environment only — requires RUNLEDGER_LICENSE_SIGNING_KEY):

  # Issue a new enterprise license key
  python -m runledger_api.core.license_cli issue \\
    --org "Acme Corp" \\
    --edition enterprise \\
    --features sso,scim,warehouse,routing_policies,invoice_reconciliation,\\
               chargeback_rules,cost_centers,pricing_contracts,pricing_credits \\
    --seats 50 \\
    --expires 2028-01-15

  # Issue a perpetual license (no expiry)
  python -m runledger_api.core.license_cli issue \\
    --org "Acme Corp" --edition enterprise --features all --seats 0

  # Verify / decode a key (useful for debugging customer issues)
  python -m runledger_api.core.license_cli verify \\
    --key rl_lic_eyJ...

  # List all known feature flags
  python -m runledger_api.core.license_cli features

The signing key is read from the RUNLEDGER_LICENSE_SIGNING_KEY environment variable
or supplied via --signing-key.  Customers never need this key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from runledger_api.core.license import (
    _ALL_FEATURES,
    LicenseError,
    _b64url_decode,
    issue_license,
    parse_license,
)


def _signing_key(args: argparse.Namespace) -> str:
    key = getattr(args, "signing_key", None) or os.environ.get("RUNLEDGER_LICENSE_SIGNING_KEY", "")
    if not key:
        print(
            "ERROR: Signing key not set.\n"
            "  Set RUNLEDGER_LICENSE_SIGNING_KEY in the vendor environment, or pass --signing-key.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def cmd_issue(args: argparse.Namespace) -> None:
    signing_key = _signing_key(args)

    # Resolve feature list
    if "all" in args.features:
        features = sorted(_ALL_FEATURES)
    else:
        features = [f.strip() for f in args.features.split(",") if f.strip()]
        unknown = set(features) - _ALL_FEATURES
        if unknown:
            print(f"WARNING: Unknown feature flags (will still be encoded): {sorted(unknown)}")

    # Parse expiry
    expires: date | None = None
    if args.expires:
        try:
            expires = date.fromisoformat(args.expires)
        except ValueError:
            print(f"ERROR: Invalid date format '{args.expires}'. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
        if expires <= date.today():
            print(f"ERROR: Expiry date {expires} is in the past.", file=sys.stderr)
            sys.exit(1)

    key = issue_license(
        org=args.org,
        edition=args.edition,
        features=features,
        seats=args.seats,
        expires=expires,
        signing_key=signing_key,
    )

    print()
    print("=" * 60)
    print("  RunLedger License Key")
    print("=" * 60)
    print(f"  Org:      {args.org}")
    print(f"  Edition:  {args.edition}")
    print(f"  Seats:    {'Unlimited' if args.seats == 0 else args.seats}")
    print(f"  Expires:  {expires.isoformat() if expires else 'Perpetual (never)'}")
    print(f"  Features: {', '.join(sorted(features)) or '(none)'}")
    print()
    print("  License Key:")
    print(f"  {key}")
    print()
    print("  Add to customer .env:")
    print(f"  RUNLEDGER_LICENSE_KEY={key}")
    print("=" * 60)
    print()


def cmd_verify(args: argparse.Namespace) -> None:
    signing_key = _signing_key(args)
    key = args.key.strip()

    # Decode payload without signature check first (for debugging)
    try:
        token = key.removeprefix("rl_lic_")
        parts = token.rsplit(".", 1)
        if len(parts) == 2:
            payload_bytes = _b64url_decode(parts[0])
            raw = json.loads(payload_bytes)
            print("\n  Raw payload (before signature check):")
            print("  " + json.dumps(raw, indent=2).replace("\n", "\n  "))
            print()
    except Exception as exc:
        print(f"  (Could not decode payload: {exc})")

    # Now verify
    try:
        lic = parse_license(key, signing_key)
        print("  ✓ Signature VALID")
        print(f"  Status:   {lic.status}")
        print(f"  Org:      {lic.org}")
        print(f"  Edition:  {lic.edition}")
        print(f"  Seats:    {'Unlimited' if lic.payload.seats == 0 else lic.payload.seats}")
        expires = lic.payload.expires
        print(f"  Expires:  {expires.isoformat() if expires else 'Perpetual'}")
        if lic.days_until_expiry is not None:
            if lic.days_until_expiry >= 0:
                print(f"  Days remaining: {lic.days_until_expiry}")
            else:
                print(f"  Days past expiry: {-lic.days_until_expiry}")
        print(f"  Features: {', '.join(sorted(lic.features)) or '(none)'}")
    except LicenseError as exc:
        print(f"  ✗ INVALID: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_features(_args: argparse.Namespace) -> None:
    print("\n  Known feature flags:")
    for flag in sorted(_ALL_FEATURES):
        print(f"    {flag}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m runledger_api.core.license_cli",
        description="RunLedger license key management (vendor use only)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # issue
    p_issue = sub.add_parser("issue", help="Issue a new signed license key")
    p_issue.add_argument("--org", required=True, help="Customer organisation name")
    p_issue.add_argument(
        "--edition",
        choices=["community", "enterprise"],
        default="enterprise",
        help="License edition (default: enterprise)",
    )
    p_issue.add_argument(
        "--features",
        default="all",
        help="Comma-separated feature flags or 'all' (default: all)",
    )
    p_issue.add_argument(
        "--seats",
        type=int,
        default=0,
        help="Number of licensed seats; 0 = unlimited (default: 0)",
    )
    p_issue.add_argument(
        "--expires",
        default=None,
        help="Expiry date as YYYY-MM-DD; omit for perpetual",
    )
    p_issue.add_argument(
        "--signing-key",
        default=None,
        help="Override RUNLEDGER_LICENSE_SIGNING_KEY env var",
    )
    p_issue.set_defaults(func=cmd_issue)

    # verify
    p_verify = sub.add_parser("verify", help="Decode and verify a license key")
    p_verify.add_argument("--key", required=True, help="License key string (rl_lic_...)")
    p_verify.add_argument(
        "--signing-key",
        default=None,
        help="Override RUNLEDGER_LICENSE_SIGNING_KEY env var",
    )
    p_verify.set_defaults(func=cmd_verify)

    # features
    p_features = sub.add_parser("features", help="List all known feature flags")
    p_features.set_defaults(func=cmd_features)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
