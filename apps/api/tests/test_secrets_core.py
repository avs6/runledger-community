"""Unit tests for stream W1-A: core/secrets, log redaction, audit chain, approvals SoD."""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet
from runledger_api.core import secrets
from runledger_api.core.config import settings

# ── core/secrets ──────────────────────────────────────────────────────────────


def test_encrypt_round_trip_and_envelope_format() -> None:
    stored = secrets.encrypt("hunter2")
    assert stored.startswith("rlsec:v1:local:")
    assert "hunter2" not in stored
    assert secrets.decrypt(stored) == "hunter2"
    assert secrets.encrypt(stored) == stored  # idempotent
    assert secrets.stored_key_id(stored) == secrets.primary_key_id()


def test_legacy_formats_still_decrypt() -> None:
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    legacy_enc = "enc::" + Fernet(derived).encrypt(b"kafka-pw").decode()
    assert secrets.decrypt(legacy_enc) == "kafka-pw"
    legacy_hmac = "a" * 64 + ":ldap-pw"
    assert secrets.decrypt(legacy_hmac, legacy_hmac=True) == "ldap-pw"
    assert secrets.decrypt("plain-value") == "plain-value"


def test_decrypt_failure_raises_instead_of_returning_ciphertext() -> None:
    other = Fernet(Fernet.generate_key()).encrypt(b"x").decode()
    with pytest.raises(secrets.SecretDecryptError):
        secrets.decrypt(f"rlsec:v1:local:deadbeef:{other}")


def test_master_key_rotation_rewraps(monkeypatch: pytest.MonkeyPatch) -> None:
    old = secrets.encrypt("rotate-me")
    new_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "secrets_master_key", new_key, raising=False)
    assert secrets.primary_key_id() != secrets.stored_key_id(old)
    assert secrets.decrypt(old) == "rotate-me"  # old key still decrypts
    rewrapped = secrets.rewrap(old)
    assert rewrapped != old and secrets.stored_key_id(rewrapped) == secrets.primary_key_id()
    assert secrets.decrypt(rewrapped) == "rotate-me"


def test_config_mask_merge_seal_open() -> None:
    stored = secrets.seal_config({"token": "t0k", "header_name": "X-Key", "Authorization": "B x"})
    assert stored is not None
    assert stored["token"].startswith("rlsec:") and stored["header_name"] == "X-Key"
    assert stored["Authorization"].startswith("rlsec:")
    opened = secrets.open_config(stored)
    assert opened == {"token": "t0k", "header_name": "X-Key", "Authorization": "B x"}
    masked = secrets.mask_config(opened)
    assert masked["token"] == secrets.SECRET_MASK and masked["header_name"] == "X-Key"
    # Sending the mask back keeps the stored value; a new value replaces it.
    assert secrets.merge_config(masked, opened)["token"] == "t0k"
    assert secrets.merge_config({**masked, "token": "new"}, opened)["token"] == "new"


def test_mask_url_hides_path_and_query() -> None:
    masked = secrets.mask_url("https://hooks.slack.com/services/T0/B0/xyz?token=abc")
    assert masked == f"https://hooks.slack.com/{secrets.SECRET_MASK}"


def test_encrypted_column_types() -> None:
    col = secrets.EncryptedText()
    bound = col.process_bind_param("s3cret", MagicMock())
    assert bound is not None and bound.startswith("rlsec:")
    assert col.process_result_value(bound, MagicMock()) == "s3cret"
    js = secrets.EncryptedSecretsJSON()
    sealed = js.process_bind_param({"api_key": "k", "model": "m"}, MagicMock())
    assert sealed["api_key"].startswith("rlsec:") and sealed["model"] == "m"
    assert js.process_result_value(sealed, MagicMock()) == {"api_key": "k", "model": "m"}


# ── logging redaction (P-27) ──────────────────────────────────────────────────


def test_redact_pii_processor() -> None:
    from runledger_api.core.logging import REDACTED, redact_pii

    event = redact_pii(
        None,
        "info",
        {
            "event": "login for alice@example.com from 10.1.2.3",
            "password": "pw",
            "headers": {"Authorization": "Bearer abc.def", "x-request-id": "r1"},
            "note": "key rl_live_abcdefghijklmnop used",
            "level": "info",
        },
    )
    assert event["password"] == REDACTED
    assert "alice@example.com" not in event["event"] and "10.1.2.3" not in event["event"]
    assert event["headers"]["Authorization"] == REDACTED
    assert event["headers"]["x-request-id"] == "r1"
    assert "rl_live_abcdefghijklmnop" not in event["note"]
    assert event["level"] == "info"


# ── audit chain ───────────────────────────────────────────────────────────────


def test_audit_hash_covers_content_and_prev() -> None:
    from runledger_api.services.audit import GENESIS_HASH, compute_hash

    ev = SimpleNamespace(
        id=uuid.uuid4(),
        seq=1,
        chain_key="ws:x",
        workspace_id=None,
        tenant_id=None,
        actor_user_id=None,
        actor_api_key_prefix="rl_live_",
        actor_type="api_key",
        actor_label="ci",
        action="budget.updated",
        target_type="budget",
        target_id="b1",
        before={"limit": 1},
        after={"limit": 2},
        ip_hash=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    h1 = compute_hash(ev, GENESIS_HASH)  # type: ignore[arg-type]
    assert h1 == compute_hash(ev, GENESIS_HASH)  # type: ignore[arg-type]
    assert compute_hash(ev, "1" * 64) != h1  # type: ignore[arg-type]
    ev.after = {"limit": 3}
    assert compute_hash(ev, GENESIS_HASH) != h1  # type: ignore[arg-type]


async def test_emit_uses_request_actor() -> None:
    from runledger_api.services.audit import Actor, emit_audit_event, reset_actor, set_actor

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.get = AsyncMock(return_value=None)
    user_id = uuid.uuid4()
    token = set_actor(Actor(kind="session", user_id=user_id, label="ops@example.test"))
    try:
        await emit_audit_event(db, uuid.uuid4(), "secret.rotated")
    finally:
        reset_actor(token)
    event = db.add.call_args.args[0]
    assert event.actor_user_id == user_id
    assert event.actor_type == "session" and event.actor_label == "ops@example.test"


# ── approvals: separation of duties + row lock (S-15) ─────────────────────────


async def test_requester_cannot_approve_own_request() -> None:
    from fastapi import HTTPException
    from runledger_api.routers.approvals import approve_approval
    from runledger_api.schemas.approvals import ApprovalDecision

    ws = SimpleNamespace(id=uuid.uuid4())
    approval = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        status="pending",
        request_type="custom",
        requested_by="Alice@Example.test",
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = approval
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    key = SimpleNamespace(created_by="alice@example.test", key_prefix="rl_test_x")
    with pytest.raises(HTTPException) as exc:
        await approve_approval(
            approval_id=approval.id,
            body=ApprovalDecision(note=None),
            auth=(ws, None, None),  # type: ignore[arg-type]
            api_key=key,  # type: ignore[arg-type]
            db=db,
        )
    assert exc.value.status_code == 403
    stmt = db.execute.call_args.args[0]
    assert stmt._for_update_arg is not None  # SELECT … FOR UPDATE
    db.commit.assert_not_called()


def test_workload_keys_get_a_requester_identity() -> None:
    from runledger_api.routers.approvals import _requester_label

    assert _requester_label(SimpleNamespace(created_by=None, key_prefix="rl_live_abc")) == (
        "api_key:rl_live_abc"
    )
