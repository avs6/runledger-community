"""
RunLedger SDK exceptions.
"""

from __future__ import annotations


class RunLedgerBudgetExceededError(RuntimeError):
    """Raised when a budget check returns action='block'."""

    def __init__(self, budget_id: str, message: str = "Budget exceeded") -> None:
        self.budget_id = budget_id
        super().__init__(message)
