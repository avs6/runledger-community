from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.kafka import KafkaExportConfig, KafkaExportDelivery

log = structlog.get_logger()


def event_topic(topic_prefix: str, event_type: str) -> str:
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
    return {
        "event_id": event_id,
        "event_type": event_type,
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
        kwargs["sasl_plain_password"] = config.sasl_password_secret
    return kwargs


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
        topic = event_topic(config.topic_prefix, event_type)
        event_payload = envelope(workspace_id=workspace_id, event_type=event_type, payload=payload)
        delivery = KafkaExportDelivery(
            workspace_id=workspace_id,
            config_id=config.id,
            event_type=event_type,
            topic=topic,
            status="pending",
            payload=event_payload,
            attempt=1,
        )
        db.add(delivery)
        await db.flush()
        try:
            await _send(config, topic, event_payload)
            delivery.status = "success"
            delivery.delivered_at = datetime.now(UTC)
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
    topic = event_topic(config.topic_prefix, "run.completed")
    payload = envelope(
        workspace_id=config.workspace_id,
        event_type="runledger.kafka.test",
        payload={
            "message": "RunLedger Kafka export test",
            "config_id": str(config.id),
            "label": config.label,
        },
    )
    delivery = KafkaExportDelivery(
        workspace_id=config.workspace_id,
        config_id=config.id,
        event_type="runledger.kafka.test",
        topic=topic,
        status="pending",
        payload=payload,
        attempt=1,
    )
    db.add(delivery)
    await db.flush()
    try:
        await _send(config, topic, payload)
        delivery.status = "success"
        delivery.delivered_at = datetime.now(UTC)
        await db.commit()
        return True, None, topic
    except Exception as exc:  # noqa: BLE001
        delivery.status = "failed"
        delivery.error_detail = str(exc)
        await db.commit()
        return False, str(exc), topic
