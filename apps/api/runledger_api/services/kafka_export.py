"""
Kafka export service.

Publishes RunLedger events to user-configured Kafka topics.

Topic routing:
  run.completed / run.failed   → {prefix}.runs
  alert.fired                  → {prefix}.alerts
  budget.breached              → {prefix}.budgets
  score.submitted              → {prefix}.scores
"""

from __future__ import annotations

import contextlib
import json
import os
import ssl
import tempfile
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.models.kafka_export import KafkaExportConfig, KafkaExportDelivery
from runledger_api.services.crypto import decrypt_secret

log = structlog.get_logger()

_TOPIC_MAP: dict[str, str] = {
    "run.completed": "runs",
    "run.failed": "runs",
    "alert.fired": "alerts",
    "budget.breached": "budgets",
    "score.submitted": "scores",
}

_CONNECT_TIMEOUT = 10.0  # seconds


def _topic_for(prefix: str, event_type: str) -> str:
    suffix = _TOPIC_MAP.get(event_type, "events")
    return f"{prefix}.{suffix}"


def _build_producer_kwargs(config: KafkaExportConfig) -> dict[str, Any]:
    """Build keyword arguments for AIOKafkaProducer from a KafkaExportConfig."""
    kwargs: dict[str, Any] = {
        "bootstrap_servers": config.bootstrap_servers,
        "security_protocol": config.security_protocol,
        "request_timeout_ms": int(_CONNECT_TIMEOUT * 1000),
    }

    sasl_proto = config.security_protocol in ("SASL_PLAINTEXT", "SASL_SSL")
    if sasl_proto and config.sasl_mechanism:
        kwargs["sasl_mechanism"] = config.sasl_mechanism
        if config.sasl_username:
            kwargs["sasl_plain_username"] = config.sasl_username
        if config.sasl_password_encrypted:
            kwargs["sasl_plain_password"] = decrypt_secret(config.sasl_password_encrypted)

    ssl_proto = config.security_protocol in ("SSL", "SASL_SSL")
    if ssl_proto and config.ssl_ca_cert:
        # Write PEM to a temp file so ssl.SSLContext can load it
        ctx = ssl.create_default_context()
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False, mode="w") as f:
            f.write(config.ssl_ca_cert)
            tmp_path = f.name
        try:
            ctx.load_verify_locations(tmp_path)
        finally:
            os.unlink(tmp_path)
        kwargs["ssl_context"] = ctx

    return kwargs


async def test_connection(config: KafkaExportConfig) -> tuple[bool, str | None]:
    """
    Try to connect to the broker and publish a single test message.
    Returns (success, error_message).
    """
    try:
        from aiokafka import AIOKafkaProducer  # noqa: PLC0415
    except ImportError:
        return False, "aiokafka is not installed (pip install aiokafka)"

    topic = _topic_for(config.topic_prefix, "run.completed")
    payload = json.dumps(
        {
            "event": "kafka.test",
            "workspace_id": str(config.workspace_id),
            "config_id": str(config.id),
            "sent_at": datetime.now(UTC).isoformat(),
        }
    ).encode()

    producer = None
    try:
        producer = AIOKafkaProducer(**_build_producer_kwargs(config))
        await producer.start()
        await producer.send_and_wait(topic, payload)
        return True, None
    except Exception as exc:
        log.warning("kafka_test_failed", config_id=str(config.id), error=str(exc))
        return False, str(exc)[:256]
    finally:
        if producer is not None:
            with contextlib.suppress(Exception):
                await producer.stop()


async def dispatch_to_kafka(
    db: AsyncSession,
    workspace_id: Any,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """
    Find all enabled Kafka configs for the workspace that subscribe to this
    event_type, publish the payload, and record delivery.
    """
    try:
        from aiokafka import AIOKafkaProducer  # noqa: PLC0415
    except ImportError:
        log.warning("kafka_dispatch_skipped", reason="aiokafka not installed")
        return

    result = await db.execute(
        select(KafkaExportConfig).where(
            KafkaExportConfig.workspace_id == workspace_id,
            KafkaExportConfig.enabled.is_(True),
        )
    )
    configs = list(result.scalars().all())
    if not configs:
        return

    body = json.dumps(payload, default=str).encode()

    for cfg in configs:
        subscribed: list[str] = cfg.event_types or []
        if event_type not in subscribed:
            continue

        topic = _topic_for(cfg.topic_prefix, event_type)
        success = False
        error_detail: str | None = None
        producer = None

        try:
            producer = AIOKafkaProducer(**_build_producer_kwargs(cfg))
            await producer.start()
            await producer.send_and_wait(topic, body)
            success = True
        except Exception as exc:
            error_detail = str(exc)[:512]
            log.warning(
                "kafka_publish_failed",
                config_id=str(cfg.id),
                event_type=event_type,
                topic=topic,
                error=error_detail,
            )
        finally:
            if producer is not None:
                with contextlib.suppress(Exception):
                    await producer.stop()

        now = datetime.now(UTC)
        delivery = KafkaExportDelivery(
            config_id=cfg.id,
            event_type=event_type,
            topic=topic,
            status="success" if success else "failed",
            error_detail=error_detail,
            attempt=1,
            delivered_at=now if success else None,
        )
        db.add(delivery)
        if success:
            log.info(
                "kafka_published",
                config_id=str(cfg.id),
                event_type=event_type,
                topic=topic,
            )

    await db.commit()
