"""The one definition of billable cost.

Billing periods, exports, chargeback, budget sync and the analytics spend totals all
count cost the same way: a provider call is billable when it has a priced cost and
``is_billable`` is true. Call status does not matter — a provider can charge for a
failed call. Unpriced calls (``cost_usd`` NULL) are listed separately as unpriced
usage (``GET /providers/pricing/unpriced``) instead of being counted as zero.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import func

from runledger_api.models.events import ProviderCall


def billable_filters() -> list[sa.ColumnElement[bool]]:
    """WHERE clauses selecting billable provider calls."""
    return [ProviderCall.cost_usd.is_not(None), ProviderCall.is_billable.is_(True)]


def billable_cost_sum() -> Any:
    """SUM of billable cost, for queries that also count non-billable calls."""
    return func.coalesce(
        func.sum(
            sa.case(
                (sa.and_(*billable_filters()), ProviderCall.cost_usd),
                else_=None,
            )
        ),
        Decimal(0),
    )
