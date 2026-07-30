"""Schemas for email preferences and log."""

from __future__ import annotations

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, field_validator


class EmailPreferenceUpdate(BaseModel):
    report_frequency: str | None = None  # 'daily'|'weekly'|'monthly'|'never'
    report_hour: int | None = None
    report_timezone: str | None = None
    report_recipient_mode: str | None = None
    report_recipients: str | None = None
    alerts_enabled: bool | None = None
    approvals_enabled: bool | None = None
    reconciliation_enabled: bool | None = None
    budget_alerts_enabled: bool | None = None
    billing_closed_enabled: bool | None = None
    score_regression_enabled: bool | None = None
    dispute_flagged_enabled: bool | None = None

    @field_validator("report_hour")
    @classmethod
    def valid_report_hour(cls, value: int | None) -> int | None:
        if value is not None and not 0 <= value <= 23:
            raise ValueError("report_hour must be 0-23")
        return value

    @field_validator("report_timezone")
    @classmethod
    def valid_report_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("invalid report_timezone") from exc
        return value

    @field_validator("report_recipient_mode")
    @classmethod
    def valid_report_recipient_mode(cls, value: str | None) -> str | None:
        if value is not None and value not in {"workspace_admins", "custom"}:
            raise ValueError("invalid report_recipient_mode")
        return value


class EmailPreferenceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    workspace_id: uuid.UUID
    report_frequency: str
    report_hour: int
    report_timezone: str
    report_recipient_mode: str
    report_recipients: str | None
    report_last_sent_at: datetime | None
    alerts_enabled: bool
    approvals_enabled: bool
    reconciliation_enabled: bool
    budget_alerts_enabled: bool
    billing_closed_enabled: bool
    score_regression_enabled: bool
    dispute_flagged_enabled: bool
    created_at: datetime
    updated_at: datetime


class EmailLogItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    to_email: str
    subject: str
    event_type: str
    status: str
    error_message: str | None
    sent_at: datetime


class EmailLogList(BaseModel):
    items: list[EmailLogItem]
    total: int
