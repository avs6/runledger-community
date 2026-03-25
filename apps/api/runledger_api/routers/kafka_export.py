"""
Kafka export config CRUD + test endpoint.

Prefix: /integrations/kafka
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_workspace_admin
from runledger_api.models.kafka_export import KafkaExportConfig, KafkaExportDelivery
from runledger_api.schemas.kafka_export import (
    KafkaExportConfigCreate,
    KafkaExportConfigList,
    KafkaExportConfigResponse,
    KafkaExportConfigUpdate,
    KafkaExportDeliveryList,
    KafkaExportDeliveryResponse,
    KafkaTestResult,
)
from runledger_api.services.crypto import encrypt_secret

log = structlog.get_logger()

router = APIRouter(prefix="/integrations/kafka", tags=["Kafka Export"])


def _to_response(cfg: KafkaExportConfig) -> KafkaExportConfigResponse:
    return KafkaExportConfigResponse(
        id=str(cfg.id),
        workspace_id=str(cfg.workspace_id),
        label=cfg.label,
        bootstrap_servers=cfg.bootstrap_servers,
        topic_prefix=cfg.topic_prefix,
        security_protocol=cfg.security_protocol,
        sasl_mechanism=cfg.sasl_mechanism,
        sasl_username=cfg.sasl_username,
        ssl_ca_cert=cfg.ssl_ca_cert,
        event_types=cfg.event_types or [],
        enabled=cfg.enabled,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


@router.post("/configs", response_model=KafkaExportConfigResponse, status_code=201)
async def create_kafka_config(
    body: KafkaExportConfigCreate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KafkaExportConfigResponse:
    workspace, *_ = auth
    cfg = KafkaExportConfig(
        workspace_id=workspace.id,
        label=body.label,
        bootstrap_servers=body.bootstrap_servers,
        topic_prefix=body.topic_prefix,
        security_protocol=body.security_protocol,
        sasl_mechanism=body.sasl_mechanism,
        sasl_username=body.sasl_username,
        sasl_password_encrypted=(
            encrypt_secret(body.sasl_password) if body.sasl_password else None
        ),
        ssl_ca_cert=body.ssl_ca_cert,
        event_types=body.event_types,
    )
    db.add(cfg)
    await db.flush()
    await db.refresh(cfg)
    await db.commit()
    return _to_response(cfg)


@router.get("/configs", response_model=KafkaExportConfigList)
async def list_kafka_configs(
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KafkaExportConfigList:
    workspace, *_ = auth
    result = await db.execute(
        select(KafkaExportConfig)
        .where(KafkaExportConfig.workspace_id == workspace.id)
        .order_by(KafkaExportConfig.created_at.desc())
    )
    configs = list(result.scalars().all())
    return KafkaExportConfigList(items=[_to_response(c) for c in configs])


@router.put("/configs/{config_id}", response_model=KafkaExportConfigResponse)
async def update_kafka_config(
    config_id: uuid.UUID,
    body: KafkaExportConfigUpdate,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KafkaExportConfigResponse:
    workspace, *_ = auth
    result = await db.execute(
        select(KafkaExportConfig).where(
            KafkaExportConfig.id == config_id,
            KafkaExportConfig.workspace_id == workspace.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Kafka export config not found")

    if body.label is not None:
        cfg.label = body.label
    if body.bootstrap_servers is not None:
        cfg.bootstrap_servers = body.bootstrap_servers
    if body.topic_prefix is not None:
        cfg.topic_prefix = body.topic_prefix
    if body.security_protocol is not None:
        cfg.security_protocol = body.security_protocol
    if body.sasl_mechanism is not None:
        cfg.sasl_mechanism = body.sasl_mechanism
    if body.sasl_username is not None:
        cfg.sasl_username = body.sasl_username
    if body.sasl_password is not None:
        cfg.sasl_password_encrypted = encrypt_secret(body.sasl_password)
    if body.ssl_ca_cert is not None:
        cfg.ssl_ca_cert = body.ssl_ca_cert
    if body.event_types is not None:
        cfg.event_types = body.event_types
    if body.enabled is not None:
        cfg.enabled = body.enabled

    cfg.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(cfg)
    return _to_response(cfg)


@router.delete("/configs/{config_id}", status_code=204)
async def delete_kafka_config(
    config_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    workspace, *_ = auth
    result = await db.execute(
        select(KafkaExportConfig).where(
            KafkaExportConfig.id == config_id,
            KafkaExportConfig.workspace_id == workspace.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Kafka export config not found")
    await db.delete(cfg)
    await db.commit()


@router.post("/configs/{config_id}/test", response_model=KafkaTestResult)
async def test_kafka_config(
    config_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KafkaTestResult:
    """Test-connect to the broker and publish a single test event."""
    workspace, *_ = auth
    result = await db.execute(
        select(KafkaExportConfig).where(
            KafkaExportConfig.id == config_id,
            KafkaExportConfig.workspace_id == workspace.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Kafka export config not found")

    from runledger_api.services.kafka_export import _topic_for, test_connection  # noqa: PLC0415

    ok, error = await test_connection(cfg)
    topic = _topic_for(cfg.topic_prefix, "run.completed")
    return KafkaTestResult(ok=ok, error=error, topic=topic)


@router.get("/configs/{config_id}/deliveries", response_model=KafkaExportDeliveryList)
async def list_kafka_deliveries(
    config_id: uuid.UUID,
    auth: Annotated[tuple[Any, ...], Depends(require_workspace_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> KafkaExportDeliveryList:
    workspace, *_ = auth
    # Verify ownership
    cfg_result = await db.execute(
        select(KafkaExportConfig).where(
            KafkaExportConfig.id == config_id,
            KafkaExportConfig.workspace_id == workspace.id,
        )
    )
    if cfg_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Kafka export config not found")

    result = await db.execute(
        select(KafkaExportDelivery)
        .where(KafkaExportDelivery.config_id == config_id)
        .order_by(KafkaExportDelivery.created_at.desc())
        .limit(limit)
    )
    deliveries = list(result.scalars().all())
    return KafkaExportDeliveryList(
        items=[
            KafkaExportDeliveryResponse(
                id=str(d.id),
                config_id=str(d.config_id),
                event_type=d.event_type,
                topic=d.topic,
                status=d.status,  # type: ignore[arg-type]
                error_detail=d.error_detail,
                attempt=d.attempt,
                delivered_at=d.delivered_at,
                created_at=d.created_at,
            )
            for d in deliveries
        ]
    )
