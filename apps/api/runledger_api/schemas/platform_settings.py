from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlatformWebhookSettingsResponse(BaseModel):
    generic_webhook_configured: bool
    slack_webhook_configured: bool
    events: list[str]
    generic_webhook_url: str | None
    slack_webhook_url: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlatformWebhookSettingsUpdate(BaseModel):
    generic_webhook_url: str | None = None
    slack_webhook_url: str | None = None
    events: list[str] = Field(default_factory=list)


class PlatformWebhookSettingsTestStatus(BaseModel):
    channel: str
    ok: bool
    error: str | None = None


class PlatformWebhookSettingsTestResult(BaseModel):
    ok: bool
    message: str
    results: list[PlatformWebhookSettingsTestStatus]
