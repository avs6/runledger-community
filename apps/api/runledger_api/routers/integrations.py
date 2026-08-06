"""
Integrations router — Slack webhook connectivity testing.

Prefix: /integrations
Auth:   Bearer API key (get_current_workspace)
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runledger_api.core.db import get_db
from runledger_api.core.deps import require_org_admin
from runledger_api.core.ratelimit import management_rate_limit
from runledger_api.models.kafka import KafkaExportConfig, KafkaExportDelivery
from runledger_api.schemas.kafka import (
    KafkaExportConfigCreate,
    KafkaExportConfigList,
    KafkaExportConfigResponse,
    KafkaExportConfigUpdate,
    KafkaExportDeliveryList,
    KafkaExportDeliveryResponse,
    KafkaTestResult,
)
from runledger_api.services import kafka_export
from runledger_api.services.audit import emit_audit_event
from runledger_api.services.notifications import build_test_blocks, send_slack_message

router = APIRouter(
    prefix="/integrations", tags=["integrations"], dependencies=[Depends(management_rate_limit)]
)
log = structlog.get_logger()
OrgAdminDep = Annotated[tuple[Any, ...], Depends(require_org_admin)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


# ── Schemas ───────────────────────────────────────────────────────────────────


class SlackTestRequest(BaseModel):
    webhook_url: str


class SlackTestResponse(BaseModel):
    ok: bool
    error: str | None = None


# ── POST /integrations/slack/test ─────────────────────────────────────────────


@router.post("/slack/test", response_model=SlackTestResponse)
async def test_slack_webhook(
    body: SlackTestRequest,
    auth: OrgAdminDep,
) -> SlackTestResponse:
    """Send a test Block Kit message to the given Slack webhook URL."""
    workspace = auth[0]
    blocks = build_test_blocks()
    try:
        await send_slack_message(body.webhook_url, blocks, "RunLedger test alert")
        log.info("integrations.slack.test.ok", workspace_id=str(workspace.id))
        return SlackTestResponse(ok=True)
    except Exception as exc:
        log.warning(
            "integrations.slack.test.failed",
            workspace_id=str(workspace.id),
            error=str(exc),
        )
        return SlackTestResponse(ok=False, error=str(exc))


def _response(config: KafkaExportConfig) -> KafkaExportConfigResponse:
    return KafkaExportConfigResponse.model_validate(config)


async def _get_config(
    db: AsyncSession, workspace_id: uuid.UUID, config_id: uuid.UUID
) -> KafkaExportConfig:
    config = await db.get(KafkaExportConfig, config_id)
    if config is None or config.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kafka export config not found")
    return config


@router.get("/kafka/configs", response_model=KafkaExportConfigList)
async def list_kafka_export_configs(auth: OrgAdminDep, db: DbDep) -> KafkaExportConfigList:
    workspace = auth[0]
    rows = (
        (
            await db.execute(
                select(KafkaExportConfig)
                .where(KafkaExportConfig.workspace_id == workspace.id)
                .order_by(KafkaExportConfig.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return KafkaExportConfigList(items=[_response(row) for row in rows])


@router.post("/kafka/configs", response_model=KafkaExportConfigResponse)
async def create_kafka_export_config(
    body: KafkaExportConfigCreate,
    auth: OrgAdminDep,
    db: DbDep,
) -> KafkaExportConfigResponse:
    workspace = auth[0]
    config = KafkaExportConfig(
        workspace_id=workspace.id,
        label=body.label,
        bootstrap_servers=body.bootstrap_servers,
        topic_prefix=body.topic_prefix,
        security_protocol=body.security_protocol,
        sasl_mechanism=body.sasl_mechanism,
        sasl_username=body.sasl_username,
        sasl_password_secret=body.sasl_password,
        ssl_ca_cert=body.ssl_ca_cert,
        single_topic_mode=body.single_topic_mode,
        single_topic_name=body.single_topic_name,
        event_types=list(body.event_types),
        enabled=True,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    await emit_audit_event(
        db,
        workspace.id,
        "kafka.config.created",
        target_type="kafka_export_config",
        target_id=str(config.id),
        after={"label": config.label, "event_types": config.event_types},
    )
    await db.commit()
    return _response(config)


@router.put("/kafka/configs/{config_id}", response_model=KafkaExportConfigResponse)
async def update_kafka_export_config(
    config_id: uuid.UUID,
    body: KafkaExportConfigUpdate,
    auth: OrgAdminDep,
    db: DbDep,
) -> KafkaExportConfigResponse:
    workspace = auth[0]
    config = await _get_config(db, workspace.id, config_id)
    before = {
        "label": config.label,
        "event_types": list(config.event_types or []),
        "enabled": config.enabled,
        "redaction_mode": getattr(config, "redaction_mode", "none"),
    }
    data = body.model_dump(exclude_unset=True)
    if "sasl_password" in data:
        config.sasl_password_secret = data.pop("sasl_password")
    for key, value in data.items():
        if key == "event_types" and value is not None:
            setattr(config, key, list(value))
        else:
            setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    await emit_audit_event(
        db,
        workspace.id,
        "kafka.config.updated",
        target_type="kafka_export_config",
        target_id=str(config.id),
        before=before,
        after={
            "label": config.label,
            "event_types": list(config.event_types or []),
            "enabled": config.enabled,
            "redaction_mode": getattr(config, "redaction_mode", "none"),
        },
    )
    await db.commit()
    return _response(config)


@router.delete("/kafka/configs/{config_id}", status_code=204)
async def delete_kafka_export_config(
    config_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> None:
    workspace = auth[0]
    config = await _get_config(db, workspace.id, config_id)
    before = {"label": config.label, "event_types": list(config.event_types or [])}
    await db.delete(config)
    await db.commit()
    await emit_audit_event(
        db,
        workspace.id,
        "kafka.config.deleted",
        target_type="kafka_export_config",
        target_id=str(config_id),
        before=before,
    )
    await db.commit()


@router.post("/kafka/configs/{config_id}/test", response_model=KafkaTestResult)
async def test_kafka_export_config(
    config_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> KafkaTestResult:
    workspace = auth[0]
    config = await _get_config(db, workspace.id, config_id)
    ok, error, topic = await kafka_export.test_config(db, config)
    await emit_audit_event(
        db,
        workspace.id,
        "kafka.config.tested",
        target_type="kafka_export_config",
        target_id=str(config.id),
        after={"ok": ok, "topic": topic, "error": error},
    )
    await db.commit()
    return KafkaTestResult(ok=ok, error=error, topic=topic)


@router.get("/kafka/configs/{config_id}/deliveries", response_model=KafkaExportDeliveryList)
async def list_kafka_export_deliveries(
    config_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=200),
) -> KafkaExportDeliveryList:
    workspace = auth[0]
    await _get_config(db, workspace.id, config_id)
    rows = (
        (
            await db.execute(
                select(KafkaExportDelivery)
                .where(
                    KafkaExportDelivery.workspace_id == workspace.id,
                    KafkaExportDelivery.config_id == config_id,
                )
                .order_by(KafkaExportDelivery.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return KafkaExportDeliveryList(
        items=[KafkaExportDeliveryResponse.model_validate(row) for row in rows]
    )


@router.post(
    "/kafka/configs/{config_id}/deliveries/{delivery_id}/retry",
    response_model=KafkaExportDeliveryResponse,
)
async def retry_kafka_export_delivery(
    config_id: uuid.UUID,
    delivery_id: uuid.UUID,
    auth: OrgAdminDep,
    db: DbDep,
) -> KafkaExportDeliveryResponse:
    workspace = auth[0]
    config = await _get_config(db, workspace.id, config_id)
    delivery = await db.get(KafkaExportDelivery, delivery_id)
    if delivery is None or delivery.workspace_id != workspace.id or delivery.config_id != config.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kafka export delivery not found")
    delivery = await kafka_export.retry_delivery(db, config=config, delivery=delivery)
    await emit_audit_event(
        db,
        workspace.id,
        "kafka.delivery.retried",
        target_type="kafka_export_delivery",
        target_id=str(delivery.id),
        after={"status": delivery.status, "attempt": delivery.attempt},
    )
    await db.commit()
    return KafkaExportDeliveryResponse.model_validate(delivery)
