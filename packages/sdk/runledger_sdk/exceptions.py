"""
RunLedger SDK exceptions.
"""

from __future__ import annotations


class RunLedgerBudgetExceededError(RuntimeError):
    """Raised when a budget check returns action='block'."""

    def __init__(self, budget_id: str, message: str = "Budget exceeded") -> None:
        self.budget_id = budget_id
        super().__init__(message)


class ToolBlockedError(RuntimeError):
    """
    Raised when a tool call is blocked by the workspace Tool Registry policy.

    The SDK raises this *before* the tool executes, giving the agent loop a
    chance to handle the blocked call gracefully (e.g. return an error message
    instead of crashing).

    Attributes
    ----------
    tool_name:
        The name of the tool that was blocked.

    Example
    -------
    ::

        from runledger_sdk.exceptions import ToolBlockedError

        try:
            result = agent.run("search the web and send an email")
        except ToolBlockedError as e:
            print(f"Blocked: {e.tool_name}")
            # → "Blocked: send_email"
    """

    def __init__(
        self,
        tool_name: str,
        message: str = "Tool blocked by workspace policy",
    ) -> None:
        self.tool_name = tool_name
        super().__init__(f"{message}: {tool_name!r}")
