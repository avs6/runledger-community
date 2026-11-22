"""Outbound-destination checks for user-configured URLs and brokers (SSRF, I-21).

Webhook, Slack and Kafka destinations are tenant-controlled. Before RunLedger
connects to one it must:

- use http(s) (URLs) and name a host;
- resolve only to public addresses — loopback, private (RFC 1918), link-local
  (including cloud metadata 169.254.169.254), CGNAT, multicast, reserved and
  unspecified addresses are refused — unless the host is on
  ``EGRESS_PRIVATE_ALLOWLIST`` or ``EGRESS_ALLOW_PRIVATE`` is set by the operator.

Checks run when a destination is saved and again right before sending, so a DNS
name that later resolves to an internal address is still refused.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from runledger_api.core.config import settings


class EgressBlocked(ValueError):
    """The destination is not allowed (message is safe to show to users)."""


def _allowlisted(host: str) -> bool:
    allowed = {h.strip().lower() for h in settings.egress_private_allowlist.split(",") if h.strip()}
    return host.lower() in allowed


def _blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"))
    )


def check_host(host: str, port: int | None = None) -> None:
    """Raise EgressBlocked unless ``host`` resolves only to allowed addresses."""
    if not host:
        raise EgressBlocked("Destination host is missing")
    if settings.egress_allow_private or _allowlisted(host):
        return
    try:
        infos = socket.getaddrinfo(host, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise EgressBlocked(f"Destination host '{host}' could not be resolved") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if _blocked_ip(ip):
            raise EgressBlocked(
                f"Destination '{host}' resolves to a private or internal address, which is not allowed"
            )


def check_url(url: str) -> None:
    """Validate an http(s) destination URL."""
    parts = urlsplit(url or "")
    if parts.scheme not in {"http", "https"}:
        raise EgressBlocked("Destination URL must use http or https")
    if not parts.hostname:
        raise EgressBlocked("Destination URL must include a host")
    check_host(parts.hostname, parts.port)


def check_bootstrap_servers(servers: str) -> None:
    """Validate a comma-separated ``host:port`` Kafka bootstrap list."""
    entries = [s.strip() for s in (servers or "").split(",") if s.strip()]
    if not entries:
        raise EgressBlocked("At least one bootstrap server is required")
    for entry in entries:
        host, _, port = entry.rpartition(":")
        if not host:
            host, port = entry, ""
        check_host(host.strip("[]"), int(port) if port.isdigit() else None)
