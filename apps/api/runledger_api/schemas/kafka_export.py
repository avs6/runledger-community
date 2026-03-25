"""Pydantic schemas for Kafka export configs and delivery log."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

_VALID_PROTOCOLS = {"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"}
_VALID_SASL = {"PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"}
_VALID_EVENT_TYPES = {
    "run.completed",
    "run.failed",
    "alert.fired",
    "budget.breached",
    "score.submitted",
}
_DEFAULT_EVENT_TYPES = list(_VALID_EVENT_TYPES)


class KafkaExportConfigCreate(BaseModel):
    label: str = Field("kafka export", max_length=128)
    bootstrap_servers: str = Field(..., min_length=1, max_length=1024)
    topic_prefix: str = Field("runledger", max_length=64)
    security_protocol: str = Field("PLAINTEXT")
    sasl_mechanism: str | None = None
    sasl_username: str | None = Field(None, max_length=256)
    sasl_password: str | None = Field(None, max_length=512)
    ssl_ca_cert: str | None = None
    event_types: list[str] = Field(default_factory=lambda: list(_DEFAULT_EVENT_TYPES))


class KafkaExportConfigUpdate(BaseModel):
    label: str | None = Field(None, max_length=128)
    bootstrap_servers: str | None = Field(None, min_length=1, max_length=1024)
    topic_prefix: str | None = Field(None, max_length=64)
    security_protocol: str | None = None
    sasl_mechanism: str | None = None
    sasl_username: str | None = None
    sasl_password: str | None = None
    ssl_ca_cert: str | None = None
    event_types: list[str] | None = None
    enabled: bool | None = None


class KafkaExportConfigResponse(BaseModel):
    id: str
    workspace_id: str
    label: str
    bootstrap_servers: str
    topic_prefix: str
    security_protocol: str
    sasl_mechanism: str | None
    sasl_username: str | None
    # sasl_password is never returned
    ssl_ca_cert: str | None
    event_types: list[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KafkaExportConfigList(BaseModel):
    items: list[KafkaExportConfigResponse]


class KafkaExportDeliveryResponse(BaseModel):
    id: str
    config_id: str
    event_type: str
    topic: str
    status: Literal["pending", "success", "failed"]
    error_detail: str | None
    attempt: int
    delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KafkaExportDeliveryList(BaseModel):
    items: list[KafkaExportDeliveryResponse]


class KafkaTestResult(BaseModel):
    ok: bool
    error: str | None = None
    topic: str | None = None
