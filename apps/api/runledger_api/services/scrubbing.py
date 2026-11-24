"""PII scrubbing for ingested metadata (OTLP attributes, run/span metadata).

There is one PII redactor in RunLedger (review S-11): the patterns and placeholders
live in :mod:`runledger_api.services.gateway_redact` and are shared by gateway route
redaction, ingest scrubbing and the Data Capture "test PII" endpoint, so a value is
redacted the same way wherever it enters. Placeholders: ``[EMAIL]``, ``[PHONE]``,
``[SSN]``, ``[CARD]``.
"""

from __future__ import annotations

from typing import Any

from runledger_api.services.gateway_redact import redact_text


def scrub_value(s: str) -> str:
    """Replace PII in ``s`` with typed placeholders (the shared redactor)."""
    return redact_text(s)


def _scrub_any(v: Any) -> Any:
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
