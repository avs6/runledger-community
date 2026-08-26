from __future__ import annotations

import base64
import hashlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.config import settings
from runledger_api.models.kafka import KafkaExportConfig, KafkaExportDelivery

log = structlog.get_logger()


_REDACTED_KEYS = {
    "prompt",
    "prompts",
    "input",
    "inputs",
    "output",
    "outputs",
    "content",
    "arguments",
    "tool_arguments",
    "payload",
}


def event_topic(config: KafkaExportConfig, event_type: str) -> str:
    if config.single_topic_mode and config.single_topic_name:
        return config.single_topic_name.strip()
    topic_prefix = config.topic_prefix
    clean_prefix = topic_prefix.strip().rstrip(".")
    if event_type.startswith("run."):
        suffix = "runs"
    elif event_type.startswith("gateway."):
        suffix = "gateway"
    elif event_type.startswith("alert."):
        suffix = "alerts"
    elif event_type.startswith("budget."):
        suffix = "budgets"
    elif event_type.startswith("optimization.") or event_type.startswith("route."):
        suffix = "optimization"
    elif event_type.startswith("mcp."):
        suffix = "mcp"
    elif event_type.startswith("approval."):
        suffix = "approvals"
    elif event_type.startswith("email.") or event_type.startswith("backup."):
        suffix = "ops"
    elif event_type.startswith("compliance."):
        suffix = "compliance"
    else:
        suffix = "events"
    return f"{clean_prefix}.{suffix}"


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, uuid.UUID, Decimal)):
        return str(value)
    return str(value)


def envelope(
    *,
    workspace_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    event_id = str(uuid.uuid4())
    occurred_at = datetime.now(UTC).isoformat()
    idempotency_key = payload.get("idempotency_key") or _derive_idempotency_key(
        workspace_id=workspace_id,
        event_type=event_type,
        payload=payload,
    )
    return {
        "event_id": event_id,
        "event_type": event_type,
        "idempotency_key": idempotency_key,
        "schema_version": "v1",
        "occurred_at": occurred_at,
        "workspace_id": str(workspace_id),
        "run_id": payload.get("run_id"),
        "trace_id": payload.get("trace_id"),
        "source": payload.get("source", "runledger"),
        "data": payload,
        "metadata": {},
        "ce_specversion": "1.0",
        "ce_type": event_type,
        "ce_id": event_id,
        "ce_time": occurred_at,
    }


def _derive_idempotency_key(
    *,
    workspace_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "workspace_id": str(workspace_id),
            "event_type": event_type,
            "run_id": payload.get("run_id"),
            "trace_id": payload.get("trace_id"),
            "data": payload,
        },
        default=_json_default,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret_value(value: str) -> str:
    return "enc::" + _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def is_secret_reference(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("secretref://") or lowered.startswith("env://")


def resolve_secret_value(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("enc::"):
        token = value.removeprefix("enc::").encode("utf-8")
        try:
            return _fernet().decrypt(token).decode("utf-8")
        except InvalidToken as exc:  # noqa: PERF203
            raise ValueError("Stored Kafka secret could not be decrypted") from exc
    if is_secret_reference(value):
        env_name = value.split("://", 1)[1].strip()
        if not env_name:
            raise ValueError("Kafka secret reference is missing an environment variable name")
        resolved = os.getenv(env_name)
        if not resolved:
            raise ValueError(f"Kafka secret reference '{env_name}' is not set in the environment")
        return resolved
    return value


def _producer_kwargs(config: KafkaExportConfig) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "bootstrap_servers": [s.strip() for s in config.bootstrap_servers.split(",") if s.strip()],
        "security_protocol": config.security_protocol,
        "request_timeout_ms": 5000,
        "metadata_max_age_ms": 5000,
    }
    if config.sasl_mechanism:
        kwargs["sasl_mechanism"] = config.sasl_mechanism
    if config.sasl_username:
        kwargs["sasl_plain_username"] = config.sasl_username
    if config.sasl_password_secret:
        kwargs["sasl_plain_password"] = resolve_secret_value(config.sasl_password_secret)
    return kwargs


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _REDACTED_KEYS:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


def prepare_event_payload(config: KafkaExportConfig, payload: dict[str, Any]) -> dict[str, Any]:
    if config.redaction_mode == "metadata_only":
        base = {
            "run_id": payload.get("run_id"),
            "trace_id": payload.get("trace_id"),
            "source": payload.get("source"),
            "status": payload.get("status"),
            "event_summary": payload.get("event_summary") or payload.get("event_type"),
        }
        return {k: v for k, v in base.items() if v is not None}
    return _redact_value(payload)


async def _send(config: KafkaExportConfig, topic: str, payload: dict[str, Any]) -> None:
    from aiokafka import AIOKafkaProducer  # noqa: PLC0415

    producer = AIOKafkaProducer(
        **_producer_kwargs(config),
        value_serializer=lambda value: json.dumps(value, default=_json_default).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, payload)
    finally:
        await producer.stop()


async def _send_dead_letter(
    config: KafkaExportConfig,
    *,
    delivery: KafkaExportDelivery,
    payload: dict[str, Any],
) -> None:
    if not config.dead_letter_topic:
        return
    dead_letter_payload = {
        "failed_topic": delivery.topic,
        "delivery_id": str(delivery.id),
        "error_detail": delivery.error_detail,
        "failed_at": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    await _send(config, config.dead_letter_topic, dead_letter_payload)
    delivery.dead_letter_topic = config.dead_letter_topic
    delivery.dead_lettered_at = datetime.now(UTC)


def _retry_delay_seconds(config: KafkaExportConfig, attempt: int) -> int:
    base = max(0, int(config.retry_backoff_seconds))
    return base * max(1, attempt)


async def _deliver_once(
    config: KafkaExportConfig,
    *,
    delivery: KafkaExportDelivery,
    payload: dict[str, Any],
) -> bool:
    topic = delivery.topic
    attempt = max(1, int(delivery.attempt or 1))
    delivery.attempt = attempt
    max_attempts = max(1, int(config.max_retries) + 1)
    try:
        await _send(config, topic, payload)
        delivery.status = "success"
        delivery.error_detail = None
        delivery.next_retry_at = None
        delivery.delivered_at = datetime.now(UTC)
        return True
    except Exception as exc:  # noqa: BLE001
        delivery.error_detail = str(exc)
        delivery.last_error_at = datetime.now(UTC)
        delivery.delivered_at = None
        if attempt < max_attempts:
            delivery.status = "retry_scheduled"
            delivery.next_retry_at = datetime.now(UTC) + timedelta(
                seconds=_retry_delay_seconds(config, attempt)
            )
            return False
        delivery.status = "failed"
        delivery.next_retry_at = None
        await _send_dead_letter(config, delivery=delivery, payload=payload)
        raise


async def publish_event(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
) -> list[KafkaExportDelivery]:
    configs = list(
        (
            await db.execute(
                select(KafkaExportConfig).where(
                    KafkaExportConfig.workspace_id == workspace_id,
                    KafkaExportConfig.enabled.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    deliveries: list[KafkaExportDelivery] = []
    for config in configs:
        if event_type not in set(config.event_types or []):
            continue
        event_payload = envelope(
            workspace_id=workspace_id,
            event_type=event_type,
            payload=prepare_event_payload(config, payload),
        )
        topic = event_topic(config, event_type)
        delivery = KafkaExportDelivery(
            workspace_id=workspace_id,
            config_id=config.id,
            event_type=event_type,
            topic=topic,
            idempotency_key=event_payload["idempotency_key"],
            status="pending",
            payload=event_payload,
            attempt=1,
        )
        db.add(delivery)
        await db.flush()
        try:
            await _deliver_once(config, delivery=delivery, payload=event_payload)
            log.info(
                "kafka_export.delivery.ok",
                workspace_id=str(workspace_id),
                config_id=str(config.id),
                event_type=event_type,
                topic=topic,
            )
        except Exception as exc:  # noqa: BLE001
            delivery.status = "failed"
            delivery.error_detail = str(exc)
            log.warning(
                "kafka_export.delivery.failed",
                workspace_id=str(workspace_id),
                config_id=str(config.id),
                event_type=event_type,
                topic=topic,
                error=str(exc),
            )
        deliveries.append(delivery)
    return deliveries


async def test_config(db: AsyncSession, config: KafkaExportConfig) -> tuple[bool, str | None, str]:
    topic = event_topic(config, "runledger.kafka.test")
    payload = envelope(
        workspace_id=config.workspace_id,
        event_type="runledger.kafka.test",
        payload=prepare_event_payload(
            config,
            {
                "message": "RunLedger Kafka export test",
                "config_id": str(config.id),
                "label": config.label,
            },
        ),
    )
    delivery = KafkaExportDelivery(
        workspace_id=config.workspace_id,
        config_id=config.id,
        event_type="runledger.kafka.test",
        topic=topic,
        idempotency_key=payload["idempotency_key"],
        status="pending",
        payload=payload,
        attempt=1,
    )
    db.add(delivery)
    await db.flush()
    try:
        await _deliver_once(config, delivery=delivery, payload=payload)
        await db.commit()
        return delivery.status == "success", delivery.error_detail, topic
    except Exception as exc:  # noqa: BLE001
        delivery.status = "failed"
        delivery.error_detail = str(exc)
        await db.commit()
        return False, str(exc), topic


async def retry_delivery(
    db: AsyncSession,
    *,
    config: KafkaExportConfig,
    delivery: KafkaExportDelivery,
) -> KafkaExportDelivery:
    payload = delivery.payload or {}
    delivery.attempt = max(1, int(delivery.attempt or 1))
    if delivery.status in {"retry_scheduled", "failed"}:
        delivery.attempt += 1
    delivery.next_retry_at = None
    await _deliver_once(config, delivery=delivery, payload=payload)
    await db.commit()
    await db.refresh(delivery)
    return delivery


async def process_pending_deliveries(db: AsyncSession, *, limit: int = 100) -> int:
    now = datetime.now(UTC)
    rows = list(
        (
            await db.execute(
                select(KafkaExportDelivery, KafkaExportConfig)
                .join(KafkaExportConfig, KafkaExportConfig.id == KafkaExportDelivery.config_id)
                .where(
                    KafkaExportConfig.enabled.is_(True),
                    KafkaExportDelivery.status == "retry_scheduled",
                    KafkaExportDelivery.next_retry_at.is_not(None),
                    KafkaExportDelivery.next_retry_at <= now,
                )
                .order_by(KafkaExportDelivery.next_retry_at.asc())
                .limit(limit)
            )
        ).all()
    )
    processed = 0
    for delivery, config in rows:
        delivery.attempt = max(1, int(delivery.attempt or 1)) + 1
        try:
            await _deliver_once(config, delivery=delivery, payload=delivery.payload or {})
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "kafka_export.retry.failed",
                config_id=str(config.id),
                delivery_id=str(delivery.id),
                event_type=delivery.event_type,
                error=str(exc),
            )
        processed += 1
    if processed:
        await db.commit()
    return processed
