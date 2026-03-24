"""
Tests for gateway provider adapters (services/gateway_providers.py).

Covers:
  OpenAI adapter  — forward + stream
  Azure adapter   — URL construction, custom api_version, stream
  Bedrock adapter — message conversion, response normalization, forward, stream
  Vertex adapter  — message conversion, response normalization, forward
  Adapter registry — get_adapter routing
  Router integration — POST /gateway/routes with config field
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Helper factories ──────────────────────────────────────────────────────────


def _make_route(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        alias="gpt-4o",
        provider="openai",
        target_model="gpt-4o",
        base_url=None,
        api_key_env_var="OPENAI_API_KEY",
        priority=10,
        is_active=True,
        config=None,
        created_at=datetime.now(UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _scalars_all_result(rows: list) -> MagicMock:
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=rows)
    m = MagicMock()
    m.scalars = MagicMock(return_value=scalars)
    return m


# ── OpenAI adapter ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_adapter_forward() -> None:
    """OpenAI adapter forward uses Bearer auth + /chat/completions + model in payload."""
    from runledger_api.services.gateway_providers import OpenAIAdapter

    adapter = OpenAIAdapter()
    route = _make_route(
        provider="openai",
        target_model="gpt-4o",
        base_url="https://api.openai.com/v1",
        api_key_env_var="OPENAI_API_KEY",
    )
    messages = [{"role": "user", "content": "Hello"}]
    expected_response = {"id": "chatcmpl-1", "choices": [{"message": {"content": "Hi"}}]}

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=expected_response)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("runledger_api.services.gateway_providers.httpx.AsyncClient", return_value=mock_client),
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
    ):
        result = await adapter.forward(route, messages)

    assert result == expected_response
    call_kwargs = mock_client.post.call_args
    assert "/chat/completions" in call_kwargs.args[0]
    headers = call_kwargs.kwargs["headers"]
    assert headers["Authorization"] == "Bearer sk-test"
    payload = call_kwargs.kwargs["json"]
    assert payload["model"] == "gpt-4o"
    assert payload["messages"] == messages


@pytest.mark.asyncio
async def test_openai_adapter_stream() -> None:
    """OpenAI adapter stream yields raw SSE lines as bytes."""
    from runledger_api.services.gateway_providers import OpenAIAdapter

    adapter = OpenAIAdapter()
    route = _make_route(provider="openai", target_model="gpt-4o")
    messages = [{"role": "user", "content": "Hello"}]

    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()

    async def _lines():
        yield 'data: {"choices": [{"delta": {"content": "Hi"}}]}'
        yield "data: [DONE]"

    mock_resp.aiter_lines = _lines
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    chunks: list[bytes] = []
    with (
        patch("runledger_api.services.gateway_providers.httpx.AsyncClient", return_value=mock_client),
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
    ):
        async for chunk in adapter.stream(route, messages):
            chunks.append(chunk)

    # Both non-empty lines should have been yielded with \n\n appended
    assert len(chunks) == 2
    assert b"data:" in chunks[0]
    assert chunks[0].endswith(b"\n\n")


# ── Azure adapter ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_azure_adapter_url_construction() -> None:
    """Azure adapter builds deployment-based URL + uses api-key header + no model in payload."""
    from runledger_api.services.gateway_providers import AzureAdapter

    adapter = AzureAdapter()
    route = _make_route(
        provider="azure",
        target_model="gpt-4o",
        base_url="https://myresource.openai.azure.com",
        api_key_env_var="AZURE_OPENAI_API_KEY",
        config=None,
    )
    messages = [{"role": "user", "content": "Hello"}]
    expected_response = {"id": "az-1", "choices": [{"message": {"content": "Hi"}}]}

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=expected_response)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("runledger_api.services.gateway_providers.httpx.AsyncClient", return_value=mock_client),
        patch.dict("os.environ", {"AZURE_OPENAI_API_KEY": "azure-key-123"}),
    ):
        result = await adapter.forward(route, messages)

    assert result == expected_response
    call_kwargs = mock_client.post.call_args
    url = call_kwargs.args[0]
    # URL should include deployment name and api-version
    assert "myresource.openai.azure.com" in url
    assert "/openai/deployments/gpt-4o/chat/completions" in url
    assert "api-version=2024-02-01" in url
    headers = call_kwargs.kwargs["headers"]
    assert headers["api-key"] == "azure-key-123"
    # Payload must NOT contain model key
    payload = call_kwargs.kwargs["json"]
    assert "model" not in payload
    assert payload["messages"] == messages


@pytest.mark.asyncio
async def test_azure_adapter_custom_api_version() -> None:
    """Azure adapter uses api_version from route.config when provided."""
    from runledger_api.services.gateway_providers import AzureAdapter

    adapter = AzureAdapter()
    route = _make_route(
        provider="azure",
        target_model="gpt-4o",
        base_url="https://myresource.openai.azure.com",
        api_key_env_var="AZURE_OPENAI_API_KEY",
        config={"deployment_name": "my-gpt4o-deployment", "api_version": "2025-01-01-preview"},
    )
    messages = [{"role": "user", "content": "Test"}]

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={"choices": []})

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("runledger_api.services.gateway_providers.httpx.AsyncClient", return_value=mock_client),
        patch.dict("os.environ", {"AZURE_OPENAI_API_KEY": "key"}),
    ):
        await adapter.forward(route, messages)

    call_kwargs = mock_client.post.call_args
    url = call_kwargs.args[0]
    assert "my-gpt4o-deployment" in url
    assert "api-version=2025-01-01-preview" in url


@pytest.mark.asyncio
async def test_azure_adapter_stream() -> None:
    """Azure adapter stream yields raw SSE lines with api-key header."""
    from runledger_api.services.gateway_providers import AzureAdapter

    adapter = AzureAdapter()
    route = _make_route(
        provider="azure",
        target_model="gpt-4o",
        base_url="https://myresource.openai.azure.com",
        api_key_env_var="AZURE_OPENAI_API_KEY",
        config=None,
    )
    messages = [{"role": "user", "content": "Stream test"}]

    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()

    async def _lines():
        yield 'data: {"choices": [{"delta": {"content": "chunk1"}}]}'

    mock_resp.aiter_lines = _lines
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    chunks: list[bytes] = []
    with (
        patch("runledger_api.services.gateway_providers.httpx.AsyncClient", return_value=mock_client),
        patch.dict("os.environ", {"AZURE_OPENAI_API_KEY": "azure-key"}),
    ):
        async for chunk in adapter.stream(route, messages):
            chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].endswith(b"\n\n")
    # The stream call should use api-key header
    stream_call = mock_client.stream.call_args
    headers = stream_call.kwargs["headers"]
    assert "api-key" in headers


# ── Bedrock adapter ───────────────────────────────────────────────────────────


def test_bedrock_messages_to_bedrock_basic() -> None:
    """System messages extracted, user/assistant converted to Converse format."""
    from runledger_api.services.gateway_providers import _messages_to_bedrock

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "What is 2+2?"},
    ]
    converse, system = _messages_to_bedrock(messages)

    assert len(system) == 1
    assert system[0]["text"] == "You are helpful."

    assert len(converse) == 3
    assert converse[0]["role"] == "user"
    assert converse[0]["content"] == [{"text": "Hi"}]
    assert converse[1]["role"] == "assistant"
    assert converse[1]["content"] == [{"text": "Hello!"}]
    assert converse[2]["role"] == "user"


def test_bedrock_normalize_response() -> None:
    """Bedrock Converse response normalized to OpenAI-compatible format."""
    from runledger_api.services.gateway_providers import _normalize_bedrock_response

    raw = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": "The answer is 42."}],
            }
        },
        "usage": {"inputTokens": 15, "outputTokens": 7},
        "stopReason": "end_turn",
    }
    result = _normalize_bedrock_response(raw, "anthropic.claude-3-5-sonnet-20241022-v2:0")

    assert result["object"] == "chat.completion"
    assert result["model"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    assert len(result["choices"]) == 1
    assert result["choices"][0]["message"]["content"] == "The answer is 42."
    assert result["choices"][0]["finish_reason"] == "stop"
    assert result["usage"]["prompt_tokens"] == 15
    assert result["usage"]["completion_tokens"] == 7
    assert result["usage"]["total_tokens"] == 22


@pytest.mark.asyncio
async def test_bedrock_adapter_forward() -> None:
    """Bedrock adapter forward calls asyncio.to_thread with _bedrock_sync_call."""
    from runledger_api.services.gateway_providers import BedrockAdapter

    adapter = BedrockAdapter()
    route = _make_route(
        provider="bedrock",
        target_model="anthropic.claude-3-5-sonnet-20241022-v2:0",
        base_url=None,
        api_key_env_var="BEDROCK",
        config={"region": "us-east-1"},
    )
    messages = [{"role": "user", "content": "Hello from Bedrock"}]

    fake_raw = {
        "output": {"message": {"content": [{"text": "Bedrock response"}]}},
        "usage": {"inputTokens": 10, "outputTokens": 5},
        "stopReason": "end_turn",
    }

    with patch(
        "runledger_api.services.gateway_providers.asyncio.to_thread",
        new_callable=AsyncMock,
        return_value=fake_raw,
    ), patch.dict("os.environ", {
        "BEDROCK_AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7",
        "BEDROCK_AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI",
    }):
        result = await adapter.forward(route, messages, temperature=0.7)

    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["content"] == "Bedrock response"
    assert result["usage"]["prompt_tokens"] == 10


@pytest.mark.asyncio
async def test_bedrock_adapter_stream() -> None:
    """Bedrock adapter stream yields SSE chunks from text pieces."""
    from runledger_api.services.gateway_providers import BedrockAdapter

    adapter = BedrockAdapter()
    route = _make_route(
        provider="bedrock",
        target_model="anthropic.claude-3-5-sonnet-20241022-v2:0",
        config={"region": "us-east-1"},
        api_key_env_var="BEDROCK",
    )
    messages = [{"role": "user", "content": "Stream me"}]

    # _bedrock_sync_stream returns list of text strings
    fake_chunks = ["Hello", " world", "!"]

    with patch(
        "runledger_api.services.gateway_providers.asyncio.to_thread",
        new_callable=AsyncMock,
        return_value=fake_chunks,
    ), patch.dict("os.environ", {
        "BEDROCK_AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7",
        "BEDROCK_AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI",
    }):
        chunks: list[bytes] = []
        async for chunk in adapter.stream(route, messages):
            chunks.append(chunk)

    # 3 text chunks + 1 finish chunk + 1 [DONE] chunk
    assert len(chunks) == 5
    assert b"data: " in chunks[0]
    # last chunk should be [DONE]
    assert chunks[-1] == b"data: [DONE]\n\n"
    # second-to-last should be finish chunk (empty delta)
    finish_data = json.loads(chunks[-2][6:])
    assert finish_data["choices"][0]["finish_reason"] == "stop"


# ── Vertex adapter ────────────────────────────────────────────────────────────


def test_vertex_messages_to_gemini() -> None:
    """System messages extracted; roles mapped to Gemini format."""
    from runledger_api.services.gateway_providers import _messages_to_gemini

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "Paris."},
        {"role": "user", "content": "Thanks!"},
    ]
    contents, system_text = _messages_to_gemini(messages)

    assert system_text == "You are a helpful assistant."
    assert len(contents) == 3
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"] == [{"text": "What is the capital of France?"}]
    assert contents[1]["role"] == "model"
    assert contents[1]["parts"] == [{"text": "Paris."}]
    assert contents[2]["role"] == "user"


def test_vertex_normalize_response() -> None:
    """Gemini generateContent response normalized to OpenAI-compatible format."""
    from runledger_api.services.gateway_providers import _normalize_gemini_response

    raw = {
        "candidates": [
            {
                "content": {"parts": [{"text": "The capital is Paris."}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 12,
            "candidatesTokenCount": 6,
        },
    }
    result = _normalize_gemini_response(raw, "gemini-1.5-pro")

    assert result["object"] == "chat.completion"
    assert result["model"] == "gemini-1.5-pro"
    assert result["choices"][0]["message"]["content"] == "The capital is Paris."
    assert result["choices"][0]["finish_reason"] == "stop"
    assert result["usage"]["prompt_tokens"] == 12
    assert result["usage"]["completion_tokens"] == 6
    assert result["usage"]["total_tokens"] == 18


@pytest.mark.asyncio
async def test_vertex_adapter_forward() -> None:
    """Vertex adapter forward calls asyncio.to_thread for _resolve then httpx POST."""
    from runledger_api.services.gateway_providers import VertexAdapter

    adapter = VertexAdapter()
    route = _make_route(
        provider="vertex",
        target_model="gemini-1.5-pro",
        base_url=None,
        api_key_env_var="VERTEX_SERVICE_ACCOUNT_JSON",
        config={"project": "my-gcp-project", "location": "us-central1"},
    )
    messages = [{"role": "user", "content": "Hello Gemini"}]

    fake_url = "https://us-central1-aiplatform.googleapis.com/v1/projects/my-gcp-project/locations/us-central1/publishers/google/models/gemini-1.5-pro:generateContent"
    fake_token = "ya29.fake-token"

    gemini_response = {
        "candidates": [
            {
                "content": {"parts": [{"text": "Hello from Gemini!"}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 4},
    }

    mock_http_response = MagicMock()
    mock_http_response.raise_for_status = MagicMock()
    mock_http_response.json = MagicMock(return_value=gemini_response)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_http_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "runledger_api.services.gateway_providers.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=(fake_url, fake_token),
        ),
        patch("runledger_api.services.gateway_providers.httpx.AsyncClient", return_value=mock_client),
    ):
        result = await adapter.forward(route, messages)

    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["content"] == "Hello from Gemini!"
    assert result["usage"]["prompt_tokens"] == 8
    # Verify Bearer token was used
    call_kwargs = mock_client.post.call_args
    headers = call_kwargs.kwargs["headers"]
    assert headers["Authorization"] == f"Bearer {fake_token}"


# ── Adapter registry ──────────────────────────────────────────────────────────


def test_get_adapter_routing() -> None:
    """get_adapter returns the correct adapter class for each provider."""
    from runledger_api.services.gateway_providers import (
        AzureAdapter,
        BedrockAdapter,
        OpenAIAdapter,
        VertexAdapter,
        get_adapter,
    )

    assert isinstance(get_adapter("openai"), OpenAIAdapter)
    assert isinstance(get_adapter("anthropic"), OpenAIAdapter)
    assert isinstance(get_adapter("ollama"), OpenAIAdapter)
    assert isinstance(get_adapter("groq"), OpenAIAdapter)
    assert isinstance(get_adapter("mistral"), OpenAIAdapter)
    assert isinstance(get_adapter("custom"), OpenAIAdapter)
    assert isinstance(get_adapter("azure"), AzureAdapter)
    assert isinstance(get_adapter("bedrock"), BedrockAdapter)
    assert isinstance(get_adapter("vertex"), VertexAdapter)
    # Unknown provider falls back to OpenAI adapter
    assert isinstance(get_adapter("unknown_xyz"), OpenAIAdapter)


# ── Router integration — POST /gateway/routes with config ─────────────────────


@pytest.mark.asyncio
async def test_gateway_route_create_with_config(
    authed_client,
    mock_db_session: AsyncMock,
    mock_workspace,
) -> None:
    """POST /gateway/routes with config dict → 201, config stored."""
    route_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    async def set_attrs(obj) -> None:
        obj.id = route_id
        obj.created_at = created_at
        obj.is_active = True
        obj.priority = 10
        obj.base_url = "https://myresource.openai.azure.com"
        obj.api_key_env_var = "AZURE_OPENAI_API_KEY"
        obj.config = {"deployment_name": "my-gpt4o", "api_version": "2024-02-01"}

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/gateway/routes",
        json={
            "alias": "azure-gpt4o",
            "provider": "azure",
            "target_model": "gpt-4o",
            "base_url": "https://myresource.openai.azure.com",
            "api_key_env_var": "AZURE_OPENAI_API_KEY",
            "config": {"deployment_name": "my-gpt4o", "api_version": "2024-02-01"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "azure"
    assert data["config"] == {"deployment_name": "my-gpt4o", "api_version": "2024-02-01"}


@pytest.mark.asyncio
async def test_gateway_route_create_bedrock_provider(
    authed_client,
    mock_db_session: AsyncMock,
    mock_workspace,
) -> None:
    """POST /gateway/routes with bedrock provider → 201."""
    route_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    async def set_attrs(obj) -> None:
        obj.id = route_id
        obj.created_at = created_at
        obj.is_active = True
        obj.priority = 10
        obj.base_url = None
        obj.api_key_env_var = "BEDROCK"
        obj.config = {"region": "us-east-1"}

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/gateway/routes",
        json={
            "alias": "claude-bedrock",
            "provider": "bedrock",
            "target_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "api_key_env_var": "BEDROCK",
            "config": {"region": "us-east-1"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "bedrock"
    assert data["config"]["region"] == "us-east-1"


@pytest.mark.asyncio
async def test_gateway_route_create_vertex_provider(
    authed_client,
    mock_db_session: AsyncMock,
    mock_workspace,
) -> None:
    """POST /gateway/routes with vertex provider → 201."""
    route_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    async def set_attrs(obj) -> None:
        obj.id = route_id
        obj.created_at = created_at
        obj.is_active = True
        obj.priority = 10
        obj.base_url = None
        obj.api_key_env_var = "VERTEX_SERVICE_ACCOUNT_JSON"
        obj.config = {"project": "my-gcp-project", "location": "us-central1"}

    mock_db_session.refresh.side_effect = set_attrs

    resp = await authed_client.post(
        "/gateway/routes",
        json={
            "alias": "gemini-vertex",
            "provider": "vertex",
            "target_model": "gemini-1.5-pro",
            "api_key_env_var": "VERTEX_SERVICE_ACCOUNT_JSON",
            "config": {"project": "my-gcp-project", "location": "us-central1"},
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "vertex"
    assert data["config"]["project"] == "my-gcp-project"
