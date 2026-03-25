"""
Symmetric encryption helpers for secrets stored at rest.

Delegates to the configured KMS provider (see services/kms.py).
Default provider: Fernet (AES-128-CBC + HMAC-SHA256) keyed from SECRET_KEY.
Enterprise providers: AWS KMS, HashiCorp Vault Transit.

All stored secrets use provider-specific prefixes so plaintext legacy values
are handled transparently by decrypt_secret.

This module is the single source of truth for secret encryption across:
  - SSO client secrets (services/oidc.py)
  - Warehouse destination credentials (routers/warehouse.py)
  - Billing webhook secrets (services/billing_webhooks.py)
  - Kafka export SASL passwords (routers/kafka_export.py)
"""

from __future__ import annotations

from runledger_api.services.kms import get_kms_provider


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret for storage in the database."""
    return get_kms_provider().encrypt(plaintext)


def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypt a secret retrieved from the database.

    Handles all storage formats transparently:
      Local:   Fernet token, 'b64:<base64>' prefix, or plaintext legacy value
      AWS KMS: 'awskms:<b64-data-key>:<fernet-ciphertext>'
      Vault:   'vault:<vault:v1:...>'
    """
    return get_kms_provider().decrypt(ciphertext)
