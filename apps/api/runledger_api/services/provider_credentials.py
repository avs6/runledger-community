"""Which server-side credentials and hosts a gateway route may use (review S-02).

Routes name a provider key by environment variable (``api_key_env_var``) and may set
a custom ``base_url``. Those keys belong to the operator, and routes are created by
org admins, so without limits a tenant could name ``ADMIN_SECRET`` (or the operator's
``OPENAI_API_KEY``) and point the route at their own server — the gateway would send
the value there — or point it at an internal address (SSRF).

Rules
- ``api_key_env_var`` must be an uppercase name matching ``PROVIDER_KEY_ENV_ALLOWLIST``
  (default ``*_API_KEY,*_PROXY_KEY,*_SERVICE_ACCOUNT_JSON``) and must not look like a platform secret (``SECRET_KEY``,
  ``ADMIN_SECRET``, ``*PASSWORD*``, ``DATABASE*``, ``RUNLEDGER_*`` …). For Bedrock it
  is a prefix (``<PREFIX>_AWS_ACCESS_KEY_ID``) and must be a plain uppercase prefix.
- A route that uses a server-side key with a custom ``base_url`` must point at the
  provider's official host or a host in ``GATEWAY_BASE_URL_ALLOWLIST``. Platform
  admins may override this (still subject to the SSRF check).
- Every ``base_url`` passes the egress check (no private, loopback, link-local or
  metadata addresses) when saved and on every request. Hosts of ``OLLAMA_BASE_URL`` and
  ``VLLM_BASE_URL`` and ``EGRESS_PRIVATE_ALLOWLIST`` may be private (local models).
- At request time a disallowed variable name is never read.
"""

from __future__ import annotations

import fnmatch
import os
import re
from urllib.parse import urlsplit

from runledger_api.core.config import settings
from runledger_api.services.egress import EgressBlocked, check_url


class RouteConfigRejected(ValueError):
    """The route's credential or host is not allowed (message safe to show)."""


_NAME = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
_PREFIX = re.compile(r"^[A-Z][A-Z0-9]{0,31}(?:_[A-Z0-9]{1,31}){0,3}$")
_DENY_PARTS = (
    "SECRET_KEY",
    "ADMIN",
    "PASSWORD",
    "PASSWD",
    "DATABASE",
    "POSTGRES",
    "REDIS",
    "MINIO",
    "NEXTAUTH",
    "INTERNAL",
    "METRICS",
    "LEDGER",
    "SIGNING",
    "PEPPER",
    "RUNLEDGER",
    "JWT",
    "SESSION",
    "PRIVATE",
    "SMTP",
    "WEBHOOK",
    "KAFKA",
    "BACKUP",
    "S3_",
)
OFFICIAL_HOSTS: dict[str, tuple[str, ...]] = {
    "openai": ("api.openai.com",),
    "anthropic": ("api.anthropic.com",),
    "groq": ("api.groq.com",),
    "mistral": ("api.mistral.ai",),
    "azure": ("*.openai.azure.com", "*.cognitiveservices.azure.com"),
    "gemini": ("generativelanguage.googleapis.com",),
    "vertex": ("*-aiplatform.googleapis.com", "aiplatform.googleapis.com"),
    "bedrock": ("bedrock-runtime.*.amazonaws.com",),
}
_LOCAL_PROVIDERS = {"ollama", "vllm", "local"}

# OpenAI-compatible endpoint and key variable each provider uses when the route sets
# none. Previously every one of them defaulted to api.openai.com with OPENAI_API_KEY, so
# an Anthropic, Groq or Mistral route sent the OpenAI key to OpenAI, and local routes
# sent it to the local server (review G-21).
_OPENAI_COMPATIBLE_DEFAULTS: dict[str, tuple[str, str | None]] = {
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "anthropic": ("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
}


def openai_compatible_target(
    provider: str | None, base_url: str | None, api_key_env_var: str | None
) -> tuple[str, str | None]:
    """(base_url, api_key) for an OpenAI-compatible route. Local providers get no key
    unless the route names one; ``custom`` routes must set their own base_url."""
    prov = (provider or "").lower()
    if prov in ("ollama", "local"):
        default_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
        default_key: str | None = None
    elif prov == "vllm":
        default_url = os.getenv("VLLM_BASE_URL", "http://host.docker.internal:8001/v1")
        default_key = None
    else:
        default_url, default_key = _OPENAI_COMPATIBLE_DEFAULTS.get(
            prov, ("https://api.openai.com/v1", "OPENAI_API_KEY")
        )
    url = (base_url or default_url).rstrip("/")
    if api_key_env_var or default_key:
        key: str | None = resolve_key(api_key_env_var, default_key or "", prov)
        return url, (None if key == "none" else key)
    return url, None


def _globs(raw: str) -> list[str]:
    return [g.strip() for g in (raw or "").split(",") if g.strip()]


def env_var_allowed(name: str | None, provider: str | None = None) -> bool:
    if not name:
        return True
    upper = name.upper()
    if name != upper:
        return False
    if any(part in upper for part in _DENY_PARTS):
        return False
    if (provider or "").lower() == "bedrock":
        return bool(_PREFIX.match(name))
    if not _NAME.match(name):
        return False
    return any(fnmatch.fnmatchcase(name, g) for g in _globs(settings.provider_key_env_allowlist))


def _host_matches(host: str, patterns: tuple[str, ...] | list[str]) -> bool:
    return any(fnmatch.fnmatchcase(host.lower(), p.lower()) for p in patterns)


def _local_model_hosts() -> set[str]:
    hosts = set()
    for var in ("OLLAMA_BASE_URL", "VLLM_BASE_URL"):
        h = urlsplit(os.getenv(var, "")).hostname
        if h:
            hosts.add(h.lower())
    hosts.add("host.docker.internal")
    return hosts


def check_base_url(url: str | None, provider: str | None) -> None:
    """SSRF check for a route's base URL (local-model hosts may be private)."""
    if not url:
        return
    host = (urlsplit(url).hostname or "").lower()
    if (provider or "").lower() in _LOCAL_PROVIDERS and host in _local_model_hosts():
        return
    try:
        check_url(url)
    except EgressBlocked as exc:
        raise RouteConfigRejected(str(exc)) from exc


def validate_route(
    *,
    provider: str | None,
    base_url: str | None,
    api_key_env_var: str | None,
    is_platform_admin: bool,
) -> None:
    """Validate a route's credential reference and host before it is saved."""
    prov = (provider or "").lower()
    if not env_var_allowed(api_key_env_var, prov):
        raise RouteConfigRejected(
            f"api_key_env_var {api_key_env_var!r} is not allowed: use a provider key variable "
            f"matching {settings.provider_key_env_allowlist!r} (platform secrets can't be referenced)"
        )
    check_base_url(base_url, prov)
    if not base_url or prov in _LOCAL_PROVIDERS or is_platform_admin:
        return
    host = (urlsplit(base_url).hostname or "").lower()
    allowed = list(OFFICIAL_HOSTS.get(prov, ())) + _globs(settings.gateway_base_url_allowlist)
    if not _host_matches(host, allowed):
        raise RouteConfigRejected(
            f"base_url host {host!r} is not an official {prov or 'provider'} host or in "
            "GATEWAY_BASE_URL_ALLOWLIST; server-side provider keys are only sent to approved "
            "hosts (ask a platform admin)"
        )


def resolve_key(api_key_env_var: str | None, default_var: str, provider: str | None) -> str:
    """Read a provider key at request time, never a disallowed variable."""
    name = api_key_env_var or default_var
    if not env_var_allowed(name, provider):
        return "none"
    return os.getenv(name, "none") or "none"
