"""One place for secrets at rest (review S-03, S-04, G-05, F-15, B-09, cd:M-03).

Every stored credential (auth-provider client secrets, LDAP bind passwords,
search-provider and pass-through ``auth_config`` values, notification webhook
URLs, evaluator API keys, Kafka/backup/GitHub tokens and ledger signing keys)
goes through this module.

Envelope format
---------------
``rlsec:v1:local:<kid>:<fernet-token>``
    Encrypted with a local Fernet master key. ``kid`` is the first 8 hex chars
    of SHA-256 over the key, so rotation status can be reported without the key.
``rlsec:v1:kms:<b64 wrapped data key>:<fernet-token>``
    Envelope encryption: a data key from AWS KMS (``SECRETS_KMS_KEY_ID``)
    encrypts the value; only the KMS-wrapped data key is stored next to it.

Keys
----
``SECRETS_MASTER_KEY``  comma-separated Fernet keys (or passphrases). The first
                        encrypts; all decrypt, so a new key can be prepended and
                        old values re-wrapped with ``rewrap()``.
``SECRETS_KMS_KEY_ID``  optional KMS key id/ARN; when set new values use KMS.
When neither is set a key derived from ``SECRET_KEY`` is used (development
only; production validation warns). That derived key is also the key the old
``enc::`` Kafka/backup tokens used, so those still decrypt.

Legacy formats still read (and re-encrypted by migration ``security_secrets_audit_rls``):
``enc::<fernet>`` (derived key), ``<64 hex>:<plain>`` (old HMAC-prefixed auth
secrets, plaintext in disguise), ledger keys encrypted with ``LEDGER_MASTER_KEY``,
and plain text.

Decryption failures raise :class:`SecretDecryptError`. Nothing ever falls back to
returning the ciphertext (cd:M-03).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import threading
import time
from collections.abc import Iterable, Mapping
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import JSON, TypeDecorator

PREFIX = "rlsec:v1:"
#: What the API returns instead of a stored secret. Sending it back on update
#: means "keep the current value".
SECRET_MASK = "••••••••"
_LEGACY_HMAC_RE = re.compile(r"^[0-9a-f]{64}:")

#: Keys inside JSON configs (auth_config, evaluator config) that hold secrets.
SECRET_CONFIG_KEYS = frozenset(
    {
        "token",
        "value",
        "password",
        "secret",
        "api_key",
        "apikey",
        "client_secret",
        "access_token",
        "refresh_token",
        "private_key",
        "bearer_token",
        "secret_access_key",
        "sasl_password",
        # header names (pass-through header_config)
        "authorization",
        "x-api-key",
        "api-key",
        "proxy-authorization",
    }
)


class SecretDecryptError(ValueError):
    """A stored secret could not be decrypted with any configured key."""


# ── Key material ──────────────────────────────────────────────────────────────


def _settings() -> Any:
    from runledger_api.core.config import settings  # noqa: PLC0415

    return settings


def _as_fernet_key(raw: str) -> bytes:
    """Accept a real Fernet key, or derive one from any passphrase."""
    raw = raw.strip()
    try:
        if len(base64.urlsafe_b64decode(raw.encode())) == 32:
            return raw.encode()
    except (binascii.Error, ValueError):
        pass
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())


def key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:8]


def _master_keys() -> list[bytes]:
    s = _settings()
    configured = getattr(s, "secrets_master_key", "") or os.getenv("SECRETS_MASTER_KEY", "")
    keys = [_as_fernet_key(k) for k in configured.split(",") if k.strip()]
    # The SECRET_KEY-derived key: the fallback primary in development and the key
    # legacy ``enc::`` values were written with.
    derived = base64.urlsafe_b64encode(hashlib.sha256(s.secret_key.encode()).digest())
    if derived not in keys:
        keys.append(derived)
    ledger = getattr(s, "ledger_master_key", "")
    if ledger:
        lk = _as_fernet_key(ledger)
        if lk not in keys:
            keys.append(lk)
    return keys


def primary_key_id() -> str:
    """Key id new values are written with ("kms" when KMS is configured)."""
    if _kms_key_id():
        return "kms"
    return key_id(_master_keys()[0])


def using_derived_key() -> bool:
    """True when no SECRETS_MASTER_KEY / KMS key is configured."""
    s = _settings()
    configured = getattr(s, "secrets_master_key", "") or os.getenv("SECRETS_MASTER_KEY", "")
    return not configured.strip() and not _kms_key_id()


# ── KMS envelope ──────────────────────────────────────────────────────────────


def _kms_key_id() -> str:
    s = _settings()
    return (getattr(s, "secrets_kms_key_id", "") or os.getenv("SECRETS_KMS_KEY_ID", "")).strip()


class _KmsCache:
    """Reuses one data key for a short window, and caches unwrapped data keys."""

    ttl_seconds = 300

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: tuple[float, bytes, bytes] | None = None  # (ts, plain, wrapped)
        self._unwrapped: dict[bytes, bytes] = {}

    def _client(self) -> Any:
        import boto3  # noqa: PLC0415

        return boto3.client("kms")

    def data_key(self) -> tuple[bytes, bytes]:
        with self._lock:
            now = time.monotonic()
            if self._current and now - self._current[0] < self.ttl_seconds:
                return self._current[1], self._current[2]
            resp = self._client().generate_data_key(KeyId=_kms_key_id(), KeySpec="AES_256")
            plain = base64.urlsafe_b64encode(resp["Plaintext"])
            wrapped = resp["CiphertextBlob"]
            self._current = (now, plain, wrapped)
            self._unwrapped[wrapped] = plain
            return plain, wrapped

    def unwrap(self, wrapped: bytes) -> bytes:
        with self._lock:
            if wrapped in self._unwrapped:
                return self._unwrapped[wrapped]
        resp = self._client().decrypt(CiphertextBlob=wrapped)
        plain = base64.urlsafe_b64encode(resp["Plaintext"])
        with self._lock:
            self._unwrapped[wrapped] = plain
        return plain


_kms = _KmsCache()


# ── Encrypt / decrypt ─────────────────────────────────────────────────────────


def is_encrypted(stored: str | None) -> bool:
    return bool(stored) and str(stored).startswith(PREFIX)


def encrypt(plain: str) -> str:
    """Encrypt ``plain`` with the primary key. Idempotent for already-sealed values."""
    if is_encrypted(plain):
        return plain
    if _kms_key_id():
        dek, wrapped = _kms.data_key()
        token = Fernet(dek).encrypt(plain.encode()).decode()
        return f"{PREFIX}kms:{base64.urlsafe_b64encode(wrapped).decode()}:{token}"
    key = _master_keys()[0]
    token = Fernet(key).encrypt(plain.encode()).decode()
    return f"{PREFIX}local:{key_id(key)}:{token}"


def stored_key_id(stored: str | None) -> str | None:
    """Key id a stored value was written with; ``None`` for legacy/plain values."""
    if not is_encrypted(stored):
        return None
    parts = str(stored)[len(PREFIX) :].split(":", 2)
    if parts[0] == "kms":
        return "kms"
    return parts[1] if len(parts) > 1 else None


def _try_keys(token: bytes, keys: Iterable[bytes]) -> str:
    for key in keys:
        try:
            return Fernet(key).decrypt(token).decode()
        except InvalidToken:  # noqa: PERF203
            continue
    raise SecretDecryptError("stored secret could not be decrypted with any configured key")


def decrypt(stored: str | None, *, legacy_hmac: bool = False) -> str | None:
    """Return the plaintext for a stored value. Raises :class:`SecretDecryptError`."""
    if stored is None or stored == "":
        return stored
    value = str(stored)
    if value.startswith(PREFIX):
        body = value[len(PREFIX) :]
        mode, _, rest = body.partition(":")
        if mode == "kms":
            wrapped_b64, _, token = rest.partition(":")
            try:
                dek = _kms.unwrap(base64.urlsafe_b64decode(wrapped_b64.encode()))
            except Exception as exc:
                raise SecretDecryptError("KMS could not unwrap the data key") from exc
            return _try_keys(token.encode(), [dek])
        if mode == "local":
            kid, _, token = rest.partition(":")
            keys = _master_keys()
            ordered = [k for k in keys if key_id(k) == kid] + [k for k in keys if key_id(k) != kid]
            return _try_keys(token.encode(), ordered)
        raise SecretDecryptError(f"unknown secret envelope mode {mode!r}")
    if value.startswith("enc::"):
        return _try_keys(value.removeprefix("enc::").encode(), _master_keys())
    if value.startswith("gAAAAA"):  # bare Fernet token (old ledger keys)
        return _try_keys(value.encode(), _master_keys())
    if legacy_hmac and _LEGACY_HMAC_RE.match(value):
        return value.split(":", 1)[1]
    return value


def rewrap(stored: str | None, *, legacy_hmac: bool = False) -> str | None:
    """Re-encrypt a stored value with the current primary key (key rotation)."""
    plain = decrypt(stored, legacy_hmac=legacy_hmac)
    if plain is None or plain == "":
        return plain
    if is_encrypted(stored) and stored_key_id(stored) == primary_key_id():
        return stored
    return encrypt(plain)


def fingerprint(plain: str | None) -> str | None:
    """Short keyed fingerprint so a UI can show "changed" without the value."""
    if not plain:
        return None
    import hmac  # noqa: PLC0415

    pepper = (_settings().api_key_pepper or _settings().secret_key).encode()
    return hmac.new(pepper, plain.encode(), hashlib.sha256).hexdigest()[:12]


# ── Secret references (env:// and secretref://) ───────────────────────────────


def is_secret_reference(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("secretref://") or lowered.startswith("env://")


def resolve(value: str | None) -> str | None:
    """Decrypt a stored value, or read an ``env://NAME`` reference."""
    plain = decrypt(value)
    if plain and is_secret_reference(plain):
        env_name = plain.split("://", 1)[1].strip()
        if not env_name:
            raise SecretDecryptError("secret reference is missing an environment variable name")
        resolved = os.getenv(env_name)
        if not resolved:
            raise SecretDecryptError(f"secret reference '{env_name}' is not set")
        return resolved
    return plain


# ── Masking (write-only API) ──────────────────────────────────────────────────


def mask(value: str | None) -> str | None:
    """What the API shows for a secret: the mask when set, ``None`` when empty."""
    return SECRET_MASK if value else None


def is_mask(value: Any) -> bool:
    return isinstance(value, str) and value.strip() == SECRET_MASK


def mask_url(url: str | None) -> str | None:
    """Show scheme and host of a webhook URL; the path and query carry the token."""
    if not url:
        return url
    from urllib.parse import urlsplit  # noqa: PLC0415

    try:
        parts = urlsplit(url)
    except ValueError:
        return SECRET_MASK
    if not parts.scheme or not parts.netloc:
        return SECRET_MASK
    host = parts.hostname or ""
    return f"{parts.scheme}://{host}/{SECRET_MASK}"


def is_secret_key(key: str) -> bool:
    return key.lower() in SECRET_CONFIG_KEYS


def mask_config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    """Copy of a JSON config with every secret value replaced by the mask."""
    out: dict[str, Any] = {}
    for k, v in (config or {}).items():
        if is_secret_key(k) and v not in (None, ""):
            out[k] = SECRET_MASK
        elif isinstance(v, Mapping):
            out[k] = mask_config(v)
        else:
            out[k] = v
    return out


def merge_config(
    incoming: Mapping[str, Any] | None, existing: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Apply an update: a masked (or omitted-but-masked) secret keeps the current value."""
    current = dict(existing or {})
    out: dict[str, Any] = {}
    for k, v in (incoming or {}).items():
        if is_secret_key(k) and is_mask(v):
            if k in current:
                out[k] = current[k]
            continue
        out[k] = v
    return out


def seal_config(config: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if config is None:
        return None
    out: dict[str, Any] = {}
    for k, v in config.items():
        if is_secret_key(k) and isinstance(v, str) and v and not is_mask(v):
            out[k] = encrypt(v)
        elif isinstance(v, Mapping):
            out[k] = seal_config(v)
        else:
            out[k] = v
    return out


def open_config(config: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if config is None:
        return None
    out: dict[str, Any] = {}
    for k, v in config.items():
        if is_secret_key(k) and isinstance(v, str):
            out[k] = decrypt(v)
        elif isinstance(v, Mapping):
            out[k] = open_config(v)
        else:
            out[k] = v
    return out


def config_key_ids(config: Mapping[str, Any] | None) -> list[str | None]:
    ids: list[str | None] = []
    for k, v in (config or {}).items():
        if is_secret_key(k) and isinstance(v, str) and v:
            ids.append(stored_key_id(v))
        elif isinstance(v, Mapping):
            ids.extend(config_key_ids(v))
    return ids


# ── SQLAlchemy column types ───────────────────────────────────────────────────


class EncryptedText(TypeDecorator[str]):
    """Text column encrypted at rest. Python sees plaintext; the DB sees ``rlsec:``."""

    impl = Text
    cache_ok = True

    def __init__(self, *args: Any, legacy_hmac: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.legacy_hmac = legacy_hmac

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is None or value == "":
            return value
        return encrypt(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> str | None:
        return decrypt(value, legacy_hmac=self.legacy_hmac)


class EncryptedSecretsJSON(TypeDecorator[dict[str, Any]]):
    """JSONB column whose secret keys (see SECRET_CONFIG_KEYS) are encrypted at rest."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if isinstance(value, str):
            value = json.loads(value)
        return seal_config(value) if isinstance(value, Mapping) else value

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        return open_config(value) if isinstance(value, Mapping) else value
