"""Pydantic schemas for SaaS Foundation."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ── Signup ────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=255)
    org_name: str = Field(min_length=1, max_length=255)


class SignupResponse(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    api_key: str
    message: str


# ── Subscription ──────────────────────────────────────────────────────────────

class SubscriptionResponse(BaseModel):
    tenant_id: uuid.UUID
    plan: str
    status: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    events_limit: int
    events_used: int
    usage_pct: float  # 0.0–100.0

    model_config = {"from_attributes": True}


# ── Stripe checkout ───────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str  # "starter" | "growth" | "enterprise"
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalRequest(BaseModel):
    return_url: str


class PortalResponse(BaseModel):
    portal_url: str
