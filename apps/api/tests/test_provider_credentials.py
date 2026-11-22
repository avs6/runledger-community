"""Gateway routes can't exfiltrate server secrets or reach internal hosts (review S-02)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from runledger_api.services.provider_credentials import (
    RouteConfigRejected,
    env_var_allowed,
    resolve_key,
    validate_route,
)


@pytest.mark.parametrize(
    "name",
    [
        "SECRET_KEY",
        "ADMIN_SECRET",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
        "RUNLEDGER_API_KEY",
        "INTERNAL_SERVICE_TOKEN",
        "openai_api_key",
        "AWS_SECRET_ACCESS_KEY",
        "HOME",
        "PATH",
    ],
)
def test_platform_secrets_and_odd_names_refused(name: str) -> None:
    assert not env_var_allowed(name, "openai")


@pytest.mark.parametrize(
    "name", ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "LITELLM_PROXY_KEY"]
)
def test_provider_keys_allowed(name: str) -> None:
    assert env_var_allowed(name, "openai")


def test_bedrock_prefix_rules() -> None:
    assert env_var_allowed("BEDROCK", "bedrock")
    assert env_var_allowed("TEAM_A", "bedrock")
    assert not env_var_allowed("ADMIN", "bedrock")
    assert not env_var_allowed("bedrock", "bedrock")


def test_resolve_key_never_reads_disallowed_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_SECRET", "top-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert resolve_key("ADMIN_SECRET", "OPENAI_API_KEY", "openai") == "none"
    assert resolve_key(None, "OPENAI_API_KEY", "openai") == "sk-test"


def _public(*_a: object, **_k: object) -> None:
    return None


def test_custom_host_needs_allowlist_unless_platform_admin() -> None:
    with patch("runledger_api.services.provider_credentials.check_url", _public):
        with pytest.raises(RouteConfigRejected, match="not an official"):
            validate_route(
                provider="openai",
                base_url="https://evil.example.com/v1",
                api_key_env_var="OPENAI_API_KEY",
                is_platform_admin=False,
            )
        validate_route(
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key_env_var="OPENAI_API_KEY",
            is_platform_admin=False,
        )
        validate_route(
            provider="azure",
            base_url="https://acme.openai.azure.com",
            api_key_env_var="AZURE_OPENAI_API_KEY",
            is_platform_admin=False,
        )
        validate_route(
            provider="openai",
            base_url="https://proxy.example.com/v1",
            api_key_env_var="OPENAI_API_KEY",
            is_platform_admin=True,
        )
        with patch(
            "runledger_api.services.provider_credentials.settings.gateway_base_url_allowlist",
            "*.example.com",
        ):
            validate_route(
                provider="openai",
                base_url="https://proxy.example.com/v1",
                api_key_env_var="OPENAI_API_KEY",
                is_platform_admin=False,
            )


def test_internal_hosts_refused_even_for_platform_admins() -> None:
    for url in ("http://169.254.169.254/latest", "http://127.0.0.1:8201", "http://10.0.0.5/v1"):
        with pytest.raises(RouteConfigRejected):
            validate_route(
                provider="openai", base_url=url, api_key_env_var=None, is_platform_admin=True
            )


def test_secret_env_var_refused_on_save() -> None:
    with pytest.raises(RouteConfigRejected, match="not allowed"):
        validate_route(
            provider="openai", base_url=None, api_key_env_var="ADMIN_SECRET", is_platform_admin=True
        )


def test_local_model_host_may_be_private() -> None:
    validate_route(
        provider="ollama",
        base_url="http://host.docker.internal:11434/v1",
        api_key_env_var=None,
        is_platform_admin=False,
    )


@pytest.mark.asyncio
async def test_route_create_rejects_secret_env_var(authed_client) -> None:  # type: ignore[no-untyped-def]
    resp = await authed_client.post(
        "/gateway/routes",
        json={
            "alias": "exfil",
            "provider": "openai",
            "target_model": "gpt-4o",
            "base_url": "https://evil.example.com/v1",
            "api_key_env_var": "ADMIN_SECRET",
        },
    )
    assert resp.status_code == 422


def test_openai_compatible_defaults_per_provider(monkeypatch) -> None:
    """Each provider uses its own endpoint and key; local servers get no key (G-21)."""
    from runledger_api.services.provider_credentials import openai_compatible_target

    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setenv("GROQ_API_KEY", "gsk")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
    assert openai_compatible_target("anthropic", None, None) == (
        "https://api.anthropic.com/v1",
        "sk-ant",
    )
    assert openai_compatible_target("groq", None, None) == ("https://api.groq.com/openai/v1", "gsk")
    assert openai_compatible_target("openai", None, None) == (
        "https://api.openai.com/v1",
        "sk-openai",
    )
    assert openai_compatible_target("ollama", None, None) == ("http://ollama:11434/v1", None)
    assert openai_compatible_target("mistral", None, None)[1] is None  # unset key: none sent
    assert openai_compatible_target("anthropic", "https://proxy.example/v1/", None)[0] == (
        "https://proxy.example/v1"
    )
