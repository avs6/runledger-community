"""
Provider-specific HTTP adapters for the RunLedger Model Gateway.

Each adapter handles:
  - URL construction
  - Auth headers
  - Payload translation (OpenAI canonical → provider-native)
  - Response normalization (provider-native → OpenAI-compatible)
  - Streaming (where supported)

Usage:
    adapter = get_adapter("azure")
    response = await adapter.forward(route, messages, temperature, ...)
    async for chunk in adapter.stream(route, messages, temperature, ...):
        yield chunk
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from runledger_api.models.gateway import GatewayRoute

log = logging.getLogger(__name__)


# ── Response normalizer helpers ────────────────────────────────────────────────


def _openai_response(
    model: str,
    content: str,
    input_tokens: int,
    output_tokens: int,
    finish_reason: str = "stop",
) -> dict[str, Any]:
    """Return an OpenAI-compatible chat completion response dict."""
    return {
        "id": f"rl-gw-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    }


def _sse_chunk(content: str, model: str, finish: bool = False) -> bytes:
    """Encode a single SSE chunk in OpenAI streaming format."""
    chunk: dict[str, Any] = {
        "id": "rl-gw-chunk",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {} if finish else {"content": content},
                "finish_reason": "stop" if finish else None,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n".encode()


# ── OpenAI / OpenAI-compatible adapter (existing behaviour) ───────────────────


class OpenAIAdapter:
    """Handles OpenAI, Anthropic (via OpenAI-compat endpoint), Ollama, Groq,
    Mistral, and any custom OpenAI-compatible endpoint."""

    def _resolve(self, route: GatewayRoute) -> tuple[str, str]:
        """Return (base_url, api_key)."""
        if route.api_key_env_var:
            api_key = os.getenv(route.api_key_env_var, "none") or "none"
        else:
            api_key = os.getenv("OPENAI_API_KEY", "none") or "none"
        base_url = (route.base_url or "https://api.openai.com/v1").rstrip("/")
        return base_url, api_key

    def build_payload(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": route.target_model, "messages": messages}
        for k in (
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "seed",
            "stop",
            "response_format",
            "tools",
            "tool_choice",
        ):
            v = kwargs.get(k)
            if v is not None:
                payload[k] = v
        if kwargs.get("stream"):
            payload["stream"] = True
        return payload

    async def forward(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        base_url, api_key = self._resolve(route)
        payload = self.build_payload(route, messages, **kwargs)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def stream(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncGenerator[bytes]:
        base_url, api_key = self._resolve(route)
        payload = self.build_payload(route, messages, stream=True, **kwargs)
        async with (
            httpx.AsyncClient(timeout=300.0) as client,
            client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    yield (line + "\n\n").encode()


# ── Azure OpenAI adapter ───────────────────────────────────────────────────────


class AzureAdapter:
    """
    Azure OpenAI Service adapter.

    config keys (set on GatewayRoute.config):
      deployment_name  — Azure deployment name (defaults to target_model)
      api_version      — Azure API version (defaults to 2024-02-01)

    base_url should be the Azure resource endpoint:
      https://{resource-name}.openai.azure.com

    api_key_env_var should hold the Azure API key env var name (e.g. AZURE_OPENAI_API_KEY).

    Auth: api-key header (not Bearer).
    Payload: OpenAI-compatible, but model is omitted (deployment is in URL).
    Response: OpenAI-compatible — no normalization needed.
    """

    _DEFAULT_API_VERSION = "2024-02-01"

    def _resolve(self, route: GatewayRoute) -> tuple[str, str]:
        cfg = route.config or {}
        api_key_var = route.api_key_env_var or "AZURE_OPENAI_API_KEY"
        api_key = os.getenv(api_key_var, "none") or "none"
        resource_endpoint = (route.base_url or "").rstrip("/")
        if not resource_endpoint:
            raise ValueError("Azure route requires base_url set to your Azure resource endpoint")
        deployment = cfg.get("deployment_name") or route.target_model
        api_version = cfg.get("api_version") or self._DEFAULT_API_VERSION
        url = f"{resource_endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        return url, api_key

    def build_payload(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        # Azure: do NOT include "model" in payload — deployment is in URL
        payload: dict[str, Any] = {"messages": messages}
        for k in (
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "seed",
            "stop",
            "response_format",
            "tools",
            "tool_choice",
        ):
            v = kwargs.get(k)
            if v is not None:
                payload[k] = v
        if kwargs.get("stream"):
            payload["stream"] = True
        return payload

    async def forward(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        url, api_key = self._resolve(route)
        payload = self.build_payload(route, messages, **kwargs)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url,
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def stream(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncGenerator[bytes]:
        url, api_key = self._resolve(route)
        payload = self.build_payload(route, messages, stream=True, **kwargs)
        async with (
            httpx.AsyncClient(timeout=300.0) as client,
            client.stream(
                "POST",
                url,
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json=payload,
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    yield (line + "\n\n").encode()


# ── AWS Bedrock adapter ────────────────────────────────────────────────────────


def _messages_to_bedrock(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split system messages out; convert rest to Bedrock Converse format."""
    system: list[dict[str, Any]] = []
    converse: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            # multimodal — flatten text parts
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        if role == "system":
            system.append({"text": str(content)})
        else:
            bedrock_role = "assistant" if role == "assistant" else "user"
            converse.append({"role": bedrock_role, "content": [{"text": str(content)}]})
    return converse, system


def _normalize_bedrock_response(raw: dict[str, Any], model: str) -> dict[str, Any]:
    """Normalize Bedrock Converse API response to OpenAI-compatible format."""
    output = raw.get("output", {})
    message = output.get("message", {})
    content_blocks = message.get("content", [])
    text = " ".join(b.get("text", "") for b in content_blocks if isinstance(b, dict))
    usage = raw.get("usage", {})
    stop_reason = raw.get("stopReason", "end_turn")
    finish = (
        "stop"
        if stop_reason in ("end_turn", "stop_sequence")
        else "length"
        if stop_reason == "max_tokens"
        else stop_reason
    )
    return _openai_response(
        model=model,
        content=text,
        input_tokens=usage.get("inputTokens", 0),
        output_tokens=usage.get("outputTokens", 0),
        finish_reason=finish,
    )


def _bedrock_sync_call(
    region: str,
    access_key: str,
    secret_key: str,
    model_id: str,
    converse_messages: list[dict[str, Any]],
    system: list[dict[str, Any]],
    inference_config: dict[str, Any],
) -> dict[str, Any]:
    """Synchronous boto3 Bedrock Converse call — run in asyncio.to_thread."""
    import boto3  # noqa: PLC0415

    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "messages": converse_messages,
        "inferenceConfig": {k: v for k, v in inference_config.items() if v is not None},
    }
    if system:
        kwargs["system"] = system

    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    return client.converse(**kwargs)  # type: ignore[no-any-return]


def _bedrock_sync_stream(
    region: str,
    access_key: str,
    secret_key: str,
    model_id: str,
    converse_messages: list[dict[str, Any]],
    system: list[dict[str, Any]],
    inference_config: dict[str, Any],
) -> list[str]:
    """Synchronous boto3 Bedrock streaming call — returns list of text chunks."""
    import boto3  # noqa: PLC0415

    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "messages": converse_messages,
        "inferenceConfig": {k: v for k, v in inference_config.items() if v is not None},
    }
    if system:
        kwargs["system"] = system

    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )
    response = client.converse_stream(**kwargs)
    chunks: list[str] = []
    for event in response.get("stream", []):
        delta = event.get("contentBlockDelta", {}).get("delta", {})
        text = delta.get("text", "")
        if text:
            chunks.append(text)
    return chunks


class BedrockAdapter:
    """
    AWS Bedrock Converse API adapter.

    config keys (set on GatewayRoute.config):
      region   — AWS region (defaults to us-east-1)

    api_key_env_var convention:
      Set to prefix for env vars, e.g. "BEDROCK" → uses BEDROCK_AWS_ACCESS_KEY_ID
      and BEDROCK_AWS_SECRET_ACCESS_KEY. Defaults to AWS_ prefix.

    target_model must be the Bedrock model ID, e.g.:
      anthropic.claude-3-5-sonnet-20241022-v2:0
      amazon.nova-pro-v1:0
      meta.llama3-2-90b-instruct-v1:0

    Response is normalized to OpenAI format. Streaming is fake-streamed
    (full response collected first, then chunked) since boto3 is synchronous.
    """

    def _resolve(self, route: GatewayRoute) -> tuple[str, str, str]:
        """Return (region, access_key, secret_key)."""
        cfg = route.config or {}
        region = (
            cfg.get("region")
            or os.getenv("BEDROCK_AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        )
        prefix = (route.api_key_env_var or "").rstrip("_") or "BEDROCK"
        access_key = os.getenv(f"{prefix}_AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID", "")
        secret_key = os.getenv(f"{prefix}_AWS_SECRET_ACCESS_KEY") or os.getenv(
            "AWS_SECRET_ACCESS_KEY", ""
        )
        return region, access_key, secret_key  # type: ignore[return-value]

    async def forward(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        region, access_key, secret_key = self._resolve(route)
        converse_messages, system = _messages_to_bedrock(messages)
        inference_config: dict[str, Any] = {
            "maxTokens": kwargs.get("max_tokens"),
            "temperature": kwargs.get("temperature"),
            "topP": kwargs.get("top_p"),
        }
        raw = await asyncio.to_thread(
            _bedrock_sync_call,
            region,
            access_key,
            secret_key,
            route.target_model,
            converse_messages,
            system,
            inference_config,
        )
        return _normalize_bedrock_response(raw, route.target_model)

    async def stream(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncGenerator[bytes]:
        region, access_key, secret_key = self._resolve(route)
        converse_messages, system = _messages_to_bedrock(messages)
        inference_config: dict[str, Any] = {
            "maxTokens": kwargs.get("max_tokens"),
            "temperature": kwargs.get("temperature"),
            "topP": kwargs.get("top_p"),
        }
        chunks = await asyncio.to_thread(
            _bedrock_sync_stream,
            region,
            access_key,
            secret_key,
            route.target_model,
            converse_messages,
            system,
            inference_config,
        )
        model = route.target_model
        for chunk_text in chunks:
            yield _sse_chunk(chunk_text, model)
        yield _sse_chunk("", model, finish=True)
        yield b"data: [DONE]\n\n"


# ── Google Vertex AI / Gemini adapter ─────────────────────────────────────────


def _messages_to_gemini(messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    """Convert OpenAI messages to Gemini contents format.
    Returns (contents, system_instruction_text | None).
    """
    system_text: str | None = None
    contents: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
        if role == "system":
            system_text = str(content)
        else:
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": str(content)}]})
    return contents, system_text


def _normalize_gemini_response(raw: dict[str, Any], model: str) -> dict[str, Any]:
    """Normalize Gemini generateContent response to OpenAI-compatible format."""
    candidates = raw.get("candidates", [{}])
    first = candidates[0] if candidates else {}
    parts = first.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    finish_map = {"STOP": "stop", "MAX_TOKENS": "length", "SAFETY": "content_filter"}
    finish_reason = finish_map.get(first.get("finishReason", "STOP"), "stop")
    meta = raw.get("usageMetadata", {})
    return _openai_response(
        model=model,
        content=text,
        input_tokens=meta.get("promptTokenCount", 0),
        output_tokens=meta.get("candidatesTokenCount", 0),
        finish_reason=finish_reason,
    )


class VertexAdapter:
    """
    Google Vertex AI (Gemini) adapter.

    config keys (set on GatewayRoute.config):
      project   — GCP project ID (required)
      location  — GCP region (defaults to us-central1)

    api_key_env_var should hold the name of an env var containing the
    service account JSON as a string, e.g. VERTEX_SERVICE_ACCOUNT_JSON.
    Alternatively, set GOOGLE_APPLICATION_CREDENTIALS to a file path.

    target_model should be the Gemini model name, e.g. gemini-1.5-pro.

    Auth: Bearer token from GCP service account.
    Requires google-auth PyPI package.
    Response is normalized to OpenAI format.
    """

    _SCOPE = "https://www.googleapis.com/auth/cloud-platform"

    def _get_credentials(self, route: GatewayRoute) -> Any:
        """Return a refreshed google.oauth2 Credentials object."""
        try:
            import google.auth  # noqa: PLC0415
            import google.auth.transport.requests  # noqa: PLC0415
            import google.oauth2.service_account  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "google-auth package is required for Vertex AI. "
                "Install with: uv add google-auth --package runledger-api"
            ) from exc

        sa_json_var = route.api_key_env_var or "VERTEX_SERVICE_ACCOUNT_JSON"
        sa_json = os.getenv(sa_json_var, "")
        if sa_json:
            import json as _json  # noqa: PLC0415

            info = _json.loads(sa_json)
            creds = google.oauth2.service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
                info, scopes=[self._SCOPE]
            )
        else:
            creds, _ = google.auth.default(scopes=[self._SCOPE])

        request = google.auth.transport.requests.Request()
        if not creds.valid:
            creds.refresh(request)
        return creds

    def _resolve(self, route: GatewayRoute) -> tuple[str, str]:
        """Return (url, bearer_token)."""
        cfg = route.config or {}
        project = cfg.get("project") or os.getenv("VERTEX_PROJECT_ID", "")
        location = cfg.get("location") or os.getenv("VERTEX_LOCATION", "us-central1")
        if not project:
            raise ValueError("Vertex route requires config.project or VERTEX_PROJECT_ID env var")
        model = route.target_model
        url = (
            f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
            f"/locations/{location}/publishers/google/models/{model}:generateContent"
        )
        creds = self._get_credentials(route)
        return url, creds.token

    def _build_gemini_payload(
        self,
        contents: list[dict[str, Any]],
        system_text: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"contents": contents}
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        gen_cfg: dict[str, Any] = {}
        if kwargs.get("max_tokens") is not None:
            gen_cfg["maxOutputTokens"] = kwargs["max_tokens"]
        if kwargs.get("temperature") is not None:
            gen_cfg["temperature"] = kwargs["temperature"]
        if kwargs.get("top_p") is not None:
            gen_cfg["topP"] = kwargs["top_p"]
        if kwargs.get("stop") is not None:
            stop = kwargs["stop"]
            gen_cfg["stopSequences"] = [stop] if isinstance(stop, str) else stop
        if gen_cfg:
            payload["generationConfig"] = gen_cfg
        return payload

    async def forward(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        contents, system_text = _messages_to_gemini(messages)
        url, token = await asyncio.to_thread(self._resolve, route)
        payload = self._build_gemini_payload(contents, system_text, **kwargs)
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            raw = resp.json()
        return _normalize_gemini_response(raw, route.target_model)

    async def stream(
        self, route: GatewayRoute, messages: list[dict[str, Any]], **kwargs: Any
    ) -> AsyncGenerator[bytes]:
        """Vertex streaming via streamGenerateContent SSE endpoint."""
        contents, system_text = _messages_to_gemini(messages)
        url_base, token = await asyncio.to_thread(self._resolve, route)
        stream_url = url_base.replace(":generateContent", ":streamGenerateContent") + "?alt=sse"
        payload = self._build_gemini_payload(contents, system_text, **kwargs)
        model = route.target_model
        async with (
            httpx.AsyncClient(timeout=300.0) as client,
            client.stream(
                "POST",
                stream_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            ) as resp,
        ):
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    raw_str = line[6:].strip()
                    if not raw_str or raw_str == "[DONE]":
                        continue
                    try:
                        raw = json.loads(raw_str)
                    except json.JSONDecodeError:
                        continue
                    candidates = raw.get("candidates", [{}])
                    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
                    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                    if text:
                        yield _sse_chunk(text, model)
        yield _sse_chunk("", model, finish=True)
        yield b"data: [DONE]\n\n"


# ── Adapter registry ───────────────────────────────────────────────────────────

_OPENAI_ADAPTER = OpenAIAdapter()
_AZURE_ADAPTER = AzureAdapter()
_BEDROCK_ADAPTER = BedrockAdapter()
_VERTEX_ADAPTER = VertexAdapter()

_ADAPTER_MAP: dict[str, OpenAIAdapter | AzureAdapter | BedrockAdapter | VertexAdapter] = {
    "openai": _OPENAI_ADAPTER,
    "anthropic": _OPENAI_ADAPTER,
    "ollama": _OPENAI_ADAPTER,
    "vllm": _OPENAI_ADAPTER,  # local vLLM server (OpenAI-compatible /v1)
    "local": _OPENAI_ADAPTER,  # generic local OpenAI-compatible endpoint
    "groq": _OPENAI_ADAPTER,
    "mistral": _OPENAI_ADAPTER,
    "custom": _OPENAI_ADAPTER,
    "azure": _AZURE_ADAPTER,
    "bedrock": _BEDROCK_ADAPTER,
    "vertex": _VERTEX_ADAPTER,
}


def get_adapter(provider: str) -> OpenAIAdapter | AzureAdapter | BedrockAdapter | VertexAdapter:
    """Return the appropriate provider adapter."""
    return _ADAPTER_MAP.get(provider, _OPENAI_ADAPTER)
