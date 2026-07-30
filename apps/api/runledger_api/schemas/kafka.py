from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


KafkaSecurityProtocol = Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"]
KafkaSaslMechanism = Literal["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]

KafkaEventType = Literal[
    "run.started",
    "run.completed",
    "run.failed",
    "gateway.request.completed",
    "gateway.request.rejected",
    "budget.threshold_crossed",
    "budget.breached",
    "alert.fired",
    "optimization.applied",
    "route.changed",
    "mcp.tool.called",
    "mcp.tool.blocked",
    "approval.requested",
    "approval.decided",
    "email.report.sent",
    "backup.completed",
    "backup.failed",
    "compliance.export.ready",
]


class KafkaExportConfigCreate(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    bootstrap_servers: str = Field(min_length=1)
    topic_prefix: str = Field(default="runledger.dev", min_length=1, max_length=255)
    security_protocol: KafkaSecurityProtocol = "PLAINTEXT"
    sasl_mechanism: KafkaSaslMechanism | None = None
    sasl_username: str | None = None
    sasl_password: str | None = None
    ssl_ca_cert: str | None = None
    event_types: list[KafkaEventType] = Field(default_factory=lambda: ["run.completed", "run.failed"])


class KafkaExportConfigUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    bootstrap_servers: str | None = Field(default=None, min_length=1)
    topic_prefix: str | None = Field(default=None, min_length=1, max_length=255)
    security_protocol: KafkaSecurityProtocol | None = None
    sasl_mechanism: KafkaSaslMechanism | None = None
    sasl_username: str | None = None
    sasl_password: str | None = None
    ssl_ca_cert: str | None = None
    event_types: list[KafkaEventType] | None = None
    enabled: bool | None = None


class KafkaExportConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    label: str
    bootstrap_servers: str
    topic_prefix: str
    security_protocol: str
    sasl_mechanism: str | None
    sasl_username: str | None
    ssl_ca_cert: str | None
    event_types: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class KafkaExportConfigList(BaseModel):
    items: list[KafkaExportConfigResponse]


class KafkaExportDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    config_id: uuid.UUID
    event_type: str
    topic: str
    status: str
    error_detail: str | None
    attempt: int
    delivered_at: datetime | None
    created_at: datetime


class KafkaExportDeliveryList(BaseModel):
    items: list[KafkaExportDeliveryResponse]


class KafkaTestResult(BaseModel):
    ok: bool
    error: str | None = None
    topic: str | None = None
