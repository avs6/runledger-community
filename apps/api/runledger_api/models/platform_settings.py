from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from runledger_api.core.db import Base


class PlatformWebhookSettings(Base):
    __tablename__ = "platform_webhook_settings"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=False)
    generic_webhook_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    slack_webhook_url: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    events: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), nullable=False, server_default=sa.text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False
    )
