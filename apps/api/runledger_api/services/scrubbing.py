"""
PII scrubbing for event metadata.

Patterns replaced with [REDACTED]:
  - Email addresses
  - Social Security Numbers (SSN)
  - Credit card numbers
  - Phone numbers
"""

from __future__ import annotations

import re
from typing import Any

_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email
    re.compile(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b"),  # SSN
    re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),  # credit card
    re.compile(r"\b\+?1?\s?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # phone
]


def scrub_value(s: str) -> str:
    """Replace PII patterns with [REDACTED]."""
    for pattern in _PATTERNS:
        s = pattern.sub("[REDACTED]", s)
    return s


def _scrub_any(v: Any) -> Any:
    """Scrub a single value of any type."""
    if isinstance(v, str):
        return scrub_value(v)
    if isinstance(v, dict):
        return scrub_dict(v)
    if isinstance(v, list):
        return [_scrub_any(item) for item in v]
    return v


def scrub_dict(d: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recursively scrub all string values in a dict (including nested lists)."""
    if d is None:
        return None
    return {k: _scrub_any(v) for k, v in d.items()}
