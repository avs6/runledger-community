// ── Event types sent to RunLedger ingest API ─────────────────────────────────

export interface RunStartEvent {
  event_type: 'run_start'
  run_id: string
  started_at: string
  agent_name?: string
  end_user_id?: string
  session_id?: string
  feature_tag?: string
  deployment_version?: string
  metadata?: Record<string, unknown>
  intent?: string
  run_metadata?: Record<string, unknown>
}

export interface RunEndEvent {
  event_type: 'run_end'
  run_id: string
  ended_at: string
  status: 'succeeded' | 'failed'
  total_cost_usd?: number
  total_input_tokens?: number
  total_output_tokens?: number
}

export interface SpanStartEvent {
  event_type: 'span_start'
  run_id: string
  span_id: string
  span_type: 'llm' | 'tool' | 'retrieval'
  name: string
  started_at: string
}

export interface SpanEndEvent {
  event_type: 'span_end'
  run_id: string
  span_id: string
  status: 'succeeded' | 'failed'
  ended_at: string
  metadata?: Record<string, unknown>
}

export interface TokenDetails {
  cached_tokens?: number
  reasoning_tokens?: number
  audio_tokens?: number
  text_tokens?: number
}

export interface ProviderCallEvent {
  event_type: 'provider_call'
  run_id: string
  span_id: string
  provider: string
  model: string
  latency_ms: number
  status: 'success' | 'error'
  input_tokens?: number
  output_tokens?: number
  cached_input_tokens?: number
  /** Provider-assigned request ID (e.g. chatcmpl-xxx, msg_01xxx) for invoice reconciliation */
  provider_request_id?: string
  /** Sub-token breakdowns for prompt tokens (cached, audio, text) */
  input_tokens_details?: TokenDetails
  /** Sub-token breakdowns for completion tokens (reasoning, audio, text) */
  output_tokens_details?: TokenDetails
  error_type?: string
}

export interface ToolCallEvent {
  event_type: 'tool_call'
  run_id: string
  span_id?: string
  tool_name: string
  tool_type?: 'read' | 'write' | 'privileged'
  risk_score?: number
  duration_ms?: number
  status: 'success' | 'error' | 'succeeded' | 'failed'
}

export interface OutcomeEvent {
  event_type: 'outcome'
  run_id: string
  outcome_type: string
  success: boolean
  labels?: Record<string, unknown>
}

export type RunLedgerEvent =
  | RunStartEvent
  | RunEndEvent
  | SpanStartEvent
  | SpanEndEvent
  | ProviderCallEvent
  | ToolCallEvent
  | OutcomeEvent

// ── Context ──────────────────────────────────────────────────────────────────

export interface RunLedgerContextData {
  runId: string | null
  endUserId: string | null
  sessionId: string | null
  featureTag: string | null
  deploymentVersion: string | null
}

// ── Client options ────────────────────────────────────────────────────────────

export interface RunLedgerOptions {
  /** RunLedger API key (rl_live_... or rl_test_...). Defaults to RUNLEDGER_API_KEY env var. */
  apiKey?: string
  /** RunLedger API base URL. Defaults to RUNLEDGER_BASE_URL or https://api.runledger.io */
  baseUrl?: string
  /** If true, print events to console instead of sending. */
  local?: boolean
  /** Enable pre-call budget check against /budgets/check. */
  budgetCheck?: boolean
  /** Privacy mode: 'metadata_only' | 'full' | 'errors_only' | 'sampled' */
  privacyMode?: 'metadata_only' | 'full' | 'errors_only' | 'sampled'
  /** Default task metadata attached by fromEnv/task helpers. */
  defaultTaskMetadata?: Record<string, unknown>
}

export interface ContextOptions {
  runId?: string
  endUserId?: string
  sessionId?: string
  featureTag?: string
  deploymentVersion?: string
}

export interface TaskOptions extends ContextOptions {
  intent?: string
  metadata?: Record<string, unknown>
}
