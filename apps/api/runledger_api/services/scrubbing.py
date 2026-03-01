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


def scrub_dict(d: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recursively scrub all string values in a dict."""
    if d is None:
        return None
    result: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k] = scrub_value(v)
        elif isinstance(v, dict):
            result[k] = scrub_dict(v)
        else:
            result[k] = v
    return result
