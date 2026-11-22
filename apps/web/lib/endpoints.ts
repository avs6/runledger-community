/**
 * Public endpoints for copy-paste setup snippets (onboarding, MCP setup, telemetry).
 * Derived from the deployment's NEXT_PUBLIC_* settings so snippets point at this
 * install, never at a placeholder host.
 */
const strip = (url: string) => url.replace(/\/$/, '')

export const PUBLIC_API_URL = strip(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8201')

/** gateway-rs; defaults to the API host on port 8210. */
export const PUBLIC_GATEWAY_URL = strip(
  process.env.NEXT_PUBLIC_GATEWAY_RUNTIME_URL || PUBLIC_API_URL.replace(/:\d+$/, ':8210'),
)

/** OpenAI-compatible base URL (clients append /chat/completions). */
export const GATEWAY_OPENAI_BASE_URL = `${PUBLIC_GATEWAY_URL}/gateway`

/** Streamable-HTTP MCP endpoint (needs an API key with the `mcp` scope). */
export const MCP_URL = `${PUBLIC_API_URL}/mcp`

/** OTLP/HTTP traces endpoint (needs an API key with the `ingest` scope). */
export const OTLP_TRACES_URL = `${PUBLIC_API_URL}/v1/traces`

export const SDK_INSTALL =
  'pip install "runledger-sdk[langgraph] @ git+https://github.com/avs6/runledger-community#subdirectory=packages/sdk"'
