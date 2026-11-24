"""``@rl.workflow(...)``: attribute every call of a function to a RunLedger workflow."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def workflow_decorator(
    client: Any,
    workflow: str,
    *,
    agent: str | None = None,
    agent_id: str | None = None,
    feature_tag: str | None = None,
    enforce_envelope: bool = True,
) -> Callable[[F], F]:
    """Build the decorator behind :meth:`RunLedger.workflow`."""

    def _task(fn: Callable[..., Any]) -> Any:
        return client.task(
            getattr(fn, "__qualname__", getattr(fn, "__name__", "workflow")),
            workflow=workflow,
            agent=agent,
            agent_id=agent_id,
            feature_tag=feature_tag,
            enforce_envelope=enforce_envelope,
        )

    def decorate(fn: F) -> F:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with _task(fn):
                    return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with _task(fn):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorate
