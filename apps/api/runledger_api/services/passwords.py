"""Password policy, hashing and one-time token helpers.

bcrypt is CPU-bound, so hashing and verification run in a worker thread to keep
the event loop responsive. Verification against an unknown account still runs a
bcrypt check against a dummy hash so response time does not reveal whether an
email address is registered.
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import string

import bcrypt
from fastapi import HTTPException, status

from runledger_api.core.config import settings

# Precomputed hash of a random value, used to equalise timing for unknown users.
_DUMMY_HASH = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt()).decode()

_COMMON_PASSWORDS = {
    "password",
    "password123",
    "changeme",
    "changeme123",
    "changeme123!",
    "letmein",
    "qwerty",
    "welcome",
    "admin",
    "runledger",
    "123456789012",
}


def password_policy_errors(password: str) -> list[str]:
    """Return the policy rules the password fails (empty list = acceptable)."""
    errors: list[str] = []
    if len(password) < settings.password_min_length:
        errors.append(f"must be at least {settings.password_min_length} characters")
    if not any(c.isalpha() for c in password):
        errors.append("must contain a letter")
    if not any(c.isdigit() for c in password):
        errors.append("must contain a digit")
    if password.strip().lower() in _COMMON_PASSWORDS:
        errors.append("is too common")
    return errors


def validate_password_policy(password: str) -> None:
    """Raise 422 when the password does not meet the policy."""
    errors = password_policy_errors(password)
    if errors:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Password " + ", ".join(errors),
        )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


def _check(password: str, password_hash: str | None) -> bool:
    target = password_hash or _DUMMY_HASH
    try:
        ok = bcrypt.checkpw(password.encode(), target.encode())
    except ValueError:
        return False
    return ok and password_hash is not None


async def verify_password(password: str, password_hash: str | None) -> bool:
    """Constant-work password check; always runs bcrypt, even with no hash."""
    return await asyncio.to_thread(_check, password, password_hash)


def generate_temporary_password() -> str:
    """A random password that satisfies the policy (shown to the admin once)."""
    alphabet = string.ascii_letters + string.digits
    length = max(settings.password_min_length, 16)
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if not password_policy_errors(candidate):
            return candidate


def new_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hex). Store only the hash; email the raw token."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
