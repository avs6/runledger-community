"""
Symmetric encryption helpers for secrets stored at rest.

Uses Fernet (AES-128-CBC + HMAC-SHA256) via the cryptography library when
available, falling back to base64 encoding for environments without it.

All stored secrets use the same envelope so plaintext legacy values are handled
transparently by decrypt_secret via the 'b64:' prefix check.

This module is the single source of truth for secret encryption across:
  - SSO client secrets (services/oidc.py)
  - Warehouse destination credentials (routers/warehouse.py)
  - Billing webhook secrets (services/billing_webhooks.py)
"""

from __future__ import annotations

import base64
import hashlib


def _fernet_key() -> bytes:
    """Derive a URL-safe base64-encoded 32-byte Fernet key from SECRET_KEY."""
    from runledger_api.core.config import settings  # noqa: PLC0415

    raw = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret for storage in the database."""
    try:
        from cryptography.fernet import Fernet  # noqa: PLC0415

        f = Fernet(_fernet_key())
        return f.encrypt(plaintext.encode()).decode()
    except ImportError:
        encoded = base64.b64encode(plaintext.encode()).decode()
        return f"b64:{encoded}"


def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypt a secret retrieved from the database.

    Handles three storage formats transparently:
      1. Fernet-encrypted token (produced by encrypt_secret with cryptography installed)
      2. 'b64:<base64>' prefix (graceful fallback when cryptography is absent)
      3. Plaintext — returned as-is for legacy values written before encryption was added
    """
    if ciphertext.startswith("b64:"):
        return base64.b64decode(ciphertext[4:]).decode()
    try:
        from cryptography.fernet import Fernet  # noqa: PLC0415

        f = Fernet(_fernet_key())
        return f.decrypt(ciphertext.encode()).decode()
    except ImportError:
        # cryptography not installed — value is either b64 or plaintext
        try:
            return base64.b64decode(ciphertext).decode()
        except Exception:
            return ciphertext
    except Exception:
        # Not a valid Fernet token — treat as unencrypted legacy value
        return ciphertext
