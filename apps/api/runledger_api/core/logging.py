"""Structured logging with PII and secret redaction (review P-27).

Every log event passes through :func:`redact_pii` before rendering:

- values under sensitive keys (passwords, tokens, API keys, secrets, cookies,
  authorization headers, prompts and payload bodies) are replaced wholesale;
- inside any other string, e-mail addresses, bearer tokens, RunLedger/OpenAI/
  Anthropic-style API keys, JWTs, ``rlsec:`` ciphertexts, card-like numbers and
  IPv4 addresses are masked.

Set ``LOG_REDACTION=off`` only for local debugging.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

from runledger_api.core.config import settings

REDACTED = "[REDACTED]"

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "client_secret",
        "bind_password",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "set-cookie",
        "x-admin-secret",
        "x-internal-token",
        "x-gateway-internal-token",
        "private_key",
        "secret_access_key",
        "sasl_password",
        "prompt",
        "messages",
        "input_payload",
        "output_payload",
        "request_body",
        "response_body",
        "body",
    }
)
_SENSITIVE_SUFFIXES = ("_password", "_secret", "_token", "_api_key", "_key_value")

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"rlsec:v1:[A-Za-z0-9:_\-=]+"), "[ENCRYPTED]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-~+/]+=*"), "Bearer [REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), "[JWT]"),
    (re.compile(r"\b(?:sk|rk|pk|rl|rlk|sk-ant|ghp|gho|xox[abpr])[-_][A-Za-z0-9_\-]{12,}"), "[KEY]"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[NUMBER]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
]


def _is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return k in SENSITIVE_KEYS or k.endswith(_SENSITIVE_SUFFIXES)


def scrub_text(value: str) -> str:
    for pattern, replacement in _PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _scrub(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return value
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, Mapping):
        return {
            k: (
                REDACTED
                if isinstance(k, str) and _is_sensitive_key(k) and v
                else _scrub(v, depth + 1)
            )
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return type(value)(_scrub(v, depth + 1) for v in value)
    return value


# Keys structlog itself adds; never rewritten.
_PASSTHROUGH = frozenset({"timestamp", "level", "logger", "exc_info", "stack_info"})


def redact_pii(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: mask secrets and PII in every event."""
    for key in list(event_dict):
        if key in _PASSTHROUGH:
            continue
        value = event_dict[key]
        if _is_sensitive_key(key) and value:
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _scrub(value)
    return event_dict


def redaction_enabled() -> bool:
    return os.getenv("LOG_REDACTION", "on").lower() not in {"off", "0", "false"}


def configure_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if redaction_enabled():
        shared_processors.append(redact_pii)

    if settings.is_development:
        processors: list[structlog.types.Processor] = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
