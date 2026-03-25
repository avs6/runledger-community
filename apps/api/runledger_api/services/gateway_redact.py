"""
Gateway PII redaction service.

Regex-based scrubbing applied to chat messages before forwarding to providers
when a route has pii_redaction_enabled=True.

Patterns covered:
  - Email addresses
  - Phone numbers (US + international formats)
  - US Social Security Numbers (SSN)
  - Credit / debit card numbers (Luhn-like 13–19 digit sequences)
"""

from __future__ import annotations

import re
from typing import Any

# ── PII patterns ──────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?1[\s\-.]?)?"
    r"(?:\(?\d{3}\)?[\s\-.]?)"
    r"\d{3}[\s\-.]?\d{4}"
    r"(?!\d)"
)

_SSN_RE = re.compile(r"\b\d{3}[\-\s]\d{2}[\-\s]\d{4}\b")

_CARD_RE = re.compile(
    r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{0,4}\b"
)

_PATTERNS = [
    (_EMAIL_RE, "[EMAIL]"),
    (_PHONE_RE, "[PHONE]"),
    (_SSN_RE, "[SSN]"),
    (_CARD_RE, "[CARD]"),
]


def redact_text(text: str) -> str:
    """Replace PII tokens in *text* with bracketed placeholders."""
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _redact_content(content: str | list[Any]) -> str | list[Any]:
    """Recursively redact content that may be a string or a multimodal parts list."""
    if isinstance(content, str):
        return redact_text(content)
    if isinstance(content, list):
        redacted = []
        for part in content:
            if isinstance(part, dict):
                part = dict(part)
                if "text" in part and isinstance(part["text"], str):
                    part["text"] = redact_text(part["text"])
            redacted.append(part)
        return redacted
    return content


def redact_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a new list of messages with PII scrubbed from all content fields."""
    result = []
    for msg in messages:
        msg = dict(msg)
        if "content" in msg:
            msg["content"] = _redact_content(msg["content"])
        result.append(msg)
    return result
