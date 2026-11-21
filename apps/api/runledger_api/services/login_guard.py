"""Brute-force protection for password and LDAP logins.

Failed attempts are counted in Redis per account (email/username) and per client
IP in a fixed window of ``login_failure_window_seconds`` that starts at the first
failure. Once either limit
is reached, further attempts get 429 until the window passes. A successful login
clears the account counter. Redis outages fail open (login still works) so an
infrastructure problem cannot lock every user out.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import HTTPException, status

from runledger_api.core.config import settings

log = structlog.get_logger()


def _account_key(account: str) -> str:
    return f"rl:login:fail:acct:{account.strip().lower()}"


def _ip_key(ip: str) -> str:
    return f"rl:login:fail:ip:{ip}"


async def assert_login_allowed(redis: Any, account: str, client_ip: str | None) -> None:
    try:
        acct_fails = int(await redis.get(_account_key(account)) or 0)
        ip_fails = int(await redis.get(_ip_key(client_ip)) or 0) if client_ip else 0
    except Exception:  # noqa: BLE001 — fail open on Redis errors
        log.warning("login_guard_redis_unavailable")
        return
    if (
        acct_fails >= settings.login_max_failures_per_account
        or ip_fails >= settings.login_max_failures_per_ip
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed sign-in attempts. Try again later.",
            headers={"Retry-After": str(settings.login_failure_window_seconds)},
        )


async def record_login_failure(redis: Any, account: str, client_ip: str | None) -> None:
    window = settings.login_failure_window_seconds
    try:
        for key in [_account_key(account)] + ([_ip_key(client_ip)] if client_ip else []):
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, window)
    except Exception:  # noqa: BLE001
        log.warning("login_guard_redis_unavailable")


async def clear_login_failures(redis: Any, account: str) -> None:
    try:
        await redis.delete(_account_key(account))
    except Exception:  # noqa: BLE001
        log.warning("login_guard_redis_unavailable")
