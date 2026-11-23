"""In-memory stand-ins for the budget spend store (budget_spend / budget_spend_calls).

The service's Postgres helpers (``_db_*`` in services.budgets) are tiny SQL
statements; tests swap them for this dict-backed store so the spend path can be
exercised without a database.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from runledger_api.services import budgets as budgets_svc


class FakeRedis:
    """Just enough of redis.asyncio for budget caches, flags and throttles."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        return self.store.get(key)

    async def set(self, key: str, value: Any, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def incr(self, key: str) -> int:
        self.store[key] = int(self.store.get(key, 0)) + 1
        return int(self.store[key])

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0


class SpendStore:
    def __init__(self) -> None:
        self.spend: dict[tuple[uuid.UUID, str], Decimal] = {}
        self.calls: dict[tuple[uuid.UUID, str], int] = {}
        self.flags: set[tuple[uuid.UUID, str, str]] = set()
        self.counted: set[uuid.UUID] = set()

    async def claim(self, db: Any, workspace_id: uuid.UUID, provider_call_id: uuid.UUID) -> bool:
        if provider_call_id in self.counted:
            return False
        self.counted.add(provider_call_id)
        return True

    async def add(self, db: Any, budget_id: uuid.UUID, pk: str, cost: Decimal) -> Decimal:
        key = (budget_id, pk)
        self.spend[key] = self.spend.get(key, Decimal(0)) + cost
        self.calls[key] = self.calls.get(key, 0) + 1
        return self.spend[key]

    async def load(self, db: Any, budget_id: uuid.UUID, pk: str) -> Decimal:
        return self.spend.get((budget_id, pk), Decimal(0))

    async def set_(self, db: Any, budget_id: uuid.UUID, pk: str, value: Decimal, n: int) -> None:
        self.spend[(budget_id, pk)] = value
        self.calls[(budget_id, pk)] = n

    async def mark_once(self, db: Any, budget_id: uuid.UUID, pk: str, flag: str) -> bool:
        key = (budget_id, pk, flag)
        if key in self.flags:
            return False
        self.flags.add(key)
        return True

    def total(self, budget_id: str | uuid.UUID) -> Decimal:
        bid = uuid.UUID(str(budget_id))
        return sum((v for (b, _), v in self.spend.items() if b == bid), Decimal(0))


@contextmanager
def spend_store() -> Iterator[SpendStore]:
    store = SpendStore()
    with (
        patch.object(budgets_svc, "_db_claim_call", store.claim),
        patch.object(budgets_svc, "_db_add_spend", store.add),
        patch.object(budgets_svc, "_db_load_spend", store.load),
        patch.object(budgets_svc, "_db_set_spend", store.set_),
        patch.object(budgets_svc, "_db_mark_once", store.mark_once),
    ):
        yield store
