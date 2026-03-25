"""
BYOK / KMS abstraction for RunLedger.

Supports three providers controlled by KMS_PROVIDER env var:

  local     (default) — Fernet keyed from SECRET_KEY (existing behaviour)
  aws_kms             — AWS KMS envelope encryption via boto3
  vault               — HashiCorp Vault Transit secrets engine via HTTPS

All providers implement:
  encrypt(plaintext: str) -> str   — opaque ciphertext string, safe to store in DB
  decrypt(ciphertext: str) -> str  — recover plaintext from any stored format

Ciphertext prefixes used for routing on decrypt:
  (no prefix / Fernet token / b64:)  → local provider
  awskms:<b64-data-key>:<fernet-ct>  → aws_kms provider
  vault:<vault-ciphertext>           → vault provider
"""

from __future__ import annotations

import base64
import hashlib
from typing import Protocol

import structlog

log = structlog.get_logger()


# ── Provider protocol ─────────────────────────────────────────────────────────


class KmsProvider(Protocol):
    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...


# ── Local provider (existing Fernet behaviour) ────────────────────────────────


class LocalKmsProvider:
    """
    Fernet encryption keyed from SECRET_KEY.
    Backward-compatible with all legacy formats (b64:, plaintext, Fernet token).
    """

    def _fernet(self):  # type: ignore[return]
        from cryptography.fernet import Fernet  # noqa: PLC0415

        from runledger_api.core.config import settings  # noqa: PLC0415

        raw = hashlib.sha256(settings.secret_key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(raw))

    def encrypt(self, plaintext: str) -> str:
        try:
            return self._fernet().encrypt(plaintext.encode()).decode()
        except ImportError:
            encoded = base64.b64encode(plaintext.encode()).decode()
            return f"b64:{encoded}"

    def decrypt(self, ciphertext: str) -> str:
        if ciphertext.startswith("b64:"):
            return base64.b64decode(ciphertext[4:]).decode()
        if ciphertext.startswith("awskms:") or ciphertext.startswith("vault:"):
            raise ValueError(
                f"Ciphertext was encrypted with a different KMS provider "
                f"(prefix: {ciphertext.split(':')[0]}). "
                "Set KMS_PROVIDER to match the provider used when encrypting."
            )
        try:
            return self._fernet().decrypt(ciphertext.encode()).decode()
        except ImportError:
            try:
                return base64.b64decode(ciphertext).decode()
            except Exception:
                return ciphertext
        except Exception:
            return ciphertext


# ── AWS KMS provider ──────────────────────────────────────────────────────────


class AwsKmsProvider:
    """
    Envelope encryption using AWS KMS.

    Encrypt flow:
      1. Call GenerateDataKey to get a 256-bit data key (plaintext + encrypted copy).
      2. Encrypt the secret with the plaintext data key via Fernet.
      3. Store: "awskms:<b64(encrypted_data_key)>:<fernet_ciphertext>"

    Decrypt flow:
      1. Parse the stored string to extract encrypted data key + Fernet ciphertext.
      2. Call KMS Decrypt to recover the plaintext data key.
      3. Decrypt the Fernet ciphertext with the recovered data key.

    IAM permissions required:
      kms:GenerateDataKey
      kms:Decrypt
    """

    def __init__(self, key_id: str, region: str = "us-east-1") -> None:
        self._key_id = key_id
        self._region = region

    def _client(self):  # type: ignore[return]
        import boto3  # noqa: PLC0415

        return boto3.client("kms", region_name=self._region)

    def encrypt(self, plaintext: str) -> str:
        from cryptography.fernet import Fernet  # noqa: PLC0415

        resp = self._client().generate_data_key(KeyId=self._key_id, KeySpec="AES_256")
        dk_plain: bytes = resp["Plaintext"]
        dk_enc: bytes = resp["CiphertextBlob"]

        # Derive Fernet key from first 32 bytes of the data key
        f = Fernet(base64.urlsafe_b64encode(dk_plain[:32]))
        fernet_ct = f.encrypt(plaintext.encode()).decode()
        dk_b64 = base64.b64encode(dk_enc).decode()
        return f"awskms:{dk_b64}:{fernet_ct}"

    def decrypt(self, ciphertext: str) -> str:
        from cryptography.fernet import Fernet  # noqa: PLC0415

        if not ciphertext.startswith("awskms:"):
            # Delegate legacy formats to LocalKmsProvider
            return LocalKmsProvider().decrypt(ciphertext)

        _, dk_b64, fernet_ct = ciphertext.split(":", 2)
        dk_enc = base64.b64decode(dk_b64)

        resp = self._client().decrypt(CiphertextBlob=dk_enc)
        dk_plain: bytes = resp["Plaintext"]

        f = Fernet(base64.urlsafe_b64encode(dk_plain[:32]))
        return f.decrypt(fernet_ct.encode()).decode()


# ── HashiCorp Vault Transit provider ─────────────────────────────────────────


class VaultTransitProvider:
    """
    HashiCorp Vault Transit secrets engine.

    Encrypt flow:
      POST /v1/transit/encrypt/{key}  with base64(plaintext)
      Returns vault:v1:XXXX...  ciphertext — stored as "vault:<vault_ciphertext>"

    Decrypt flow:
      POST /v1/transit/decrypt/{key}  with vault:v1:XXXX...
      Returns base64(plaintext)

    Required Vault policy:
      path "transit/encrypt/<key>"  { capabilities = ["update"] }
      path "transit/decrypt/<key>"  { capabilities = ["update"] }
    """

    def __init__(self, addr: str, token: str, key: str = "runledger") -> None:
        self._addr = addr.rstrip("/")
        self._token = token
        self._key = key

    def _headers(self) -> dict[str, str]:
        return {"X-Vault-Token": self._token, "Content-Type": "application/json"}

    def encrypt(self, plaintext: str) -> str:
        import httpx  # noqa: PLC0415

        b64 = base64.b64encode(plaintext.encode()).decode()
        resp = httpx.post(
            f"{self._addr}/v1/transit/encrypt/{self._key}",
            headers=self._headers(),
            json={"plaintext": b64},
            timeout=10.0,
        )
        resp.raise_for_status()
        vault_ct: str = resp.json()["data"]["ciphertext"]  # vault:v1:XXXX
        return f"vault:{vault_ct}"

    def decrypt(self, ciphertext: str) -> str:
        import httpx  # noqa: PLC0415

        if not ciphertext.startswith("vault:"):
            return LocalKmsProvider().decrypt(ciphertext)

        vault_ct = ciphertext.removeprefix("vault:")
        resp = httpx.post(
            f"{self._addr}/v1/transit/decrypt/{self._key}",
            headers=self._headers(),
            json={"ciphertext": vault_ct},
            timeout=10.0,
        )
        resp.raise_for_status()
        b64: str = resp.json()["data"]["plaintext"]
        return base64.b64decode(b64).decode()


# ── Factory ───────────────────────────────────────────────────────────────────

_provider_cache: KmsProvider | None = None


def get_kms_provider() -> KmsProvider:
    """
    Return the configured KMS provider (cached for the process lifetime).

    Controlled by KMS_PROVIDER env var:
      local     → LocalKmsProvider  (default)
      aws_kms   → AwsKmsProvider    (requires AWS_KMS_KEY_ID)
      vault     → VaultTransitProvider (requires VAULT_ADDR, VAULT_TOKEN)
    """
    global _provider_cache
    if _provider_cache is not None:
        return _provider_cache

    from runledger_api.core.config import settings  # noqa: PLC0415

    provider = settings.kms_provider.lower()

    if provider == "aws_kms":
        if not settings.aws_kms_key_id:
            raise RuntimeError("KMS_PROVIDER=aws_kms requires AWS_KMS_KEY_ID to be set")
        log.info("kms_provider_init", provider="aws_kms", key_id=settings.aws_kms_key_id)
        _provider_cache = AwsKmsProvider(
            key_id=settings.aws_kms_key_id,
            region=settings.aws_kms_region,
        )

    elif provider == "vault":
        if not settings.vault_addr or not settings.vault_token:
            raise RuntimeError("KMS_PROVIDER=vault requires VAULT_ADDR and VAULT_TOKEN to be set")
        log.info(
            "kms_provider_init",
            provider="vault",
            addr=settings.vault_addr,
            key=settings.vault_transit_key,
        )
        _provider_cache = VaultTransitProvider(
            addr=settings.vault_addr,
            token=settings.vault_token,
            key=settings.vault_transit_key,
        )

    else:
        if provider != "local":
            log.warning("unknown_kms_provider", provider=provider, fallback="local")
        _provider_cache = LocalKmsProvider()

    return _provider_cache


def reset_kms_provider_cache() -> None:
    """Clear the cached provider — used in tests only."""
    global _provider_cache
    _provider_cache = None
