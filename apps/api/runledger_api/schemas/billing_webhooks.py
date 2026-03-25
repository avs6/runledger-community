"""Pydantic schemas for billing webhook endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BillingWebhookConfigCreate(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048, description="HTTPS endpoint URL")
    secret: str = Field(
        ..., min_length=8, max_length=256, description="Shared secret for HMAC-SHA256 signing"
    )
    label: str = Field("billing webhook", max_length=128)


class BillingWebhookConfigUpdate(BaseModel):
    url: str | None = Field(None, min_length=8, max_length=2048)
    secret: str | None = Field(None, min_length=8, max_length=256)
    label: str | None = Field(None, max_length=128)
    enabled: bool | None = None


class BillingWebhookConfigResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    url: str
    label: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingWebhookConfigList(BaseModel):
    items: list[BillingWebhookConfigResponse]


class BillingWebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    webhook_config_id: uuid.UUID
    billing_period_id: uuid.UUID
    attempt: int
    status: str
    response_status: int | None
    delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingWebhookDeliveryList(BaseModel):
    items: list[BillingWebhookDeliveryResponse]
