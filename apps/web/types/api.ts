export interface RunListItem {
  id: string
  status: 'running' | 'succeeded' | 'failed' | 'cancelled'
  end_user_id: string | null
  session_id: string | null
  feature_tag: string | null
  deployment_version: string | null
  total_cost_usd: string | null
  total_input_tokens: number | null
  total_output_tokens: number | null
  started_at: string
  ended_at: string | null
  duration_ms: number | null
  primary_model: string | null
}

export interface RunListResponse {
  items: RunListItem[]
  next_cursor: string | null
  total: number
}

export interface SpanDetail {
  id: string
  run_id: string
  parent_span_id: string | null
  span_type: 'chain' | 'llm' | 'tool' | 'agent' | 'retrieval' | 'run'
  name: string
  started_at: string
  ended_at: string | null
  status: string
  cost_usd: string | null
  metadata: Record<string, unknown> | null
}

export interface ProviderCallDetail {
  id: string
  span_id: string | null
  run_id: string
  provider: string
  model: string
  input_tokens: number | null
  output_tokens: number | null
  cached_input_tokens: number | null
  latency_ms: number | null
  cost_usd: string | null
  status: string
  error_type: string | null
  created_at: string
}

export interface ToolCallDetail {
  id: string
  span_id: string | null
  run_id: string
  tool_name: string
  tool_type: string
  risk_score: number | null
  duration_ms: number | null
  status: string
  created_at: string
}

export interface RunDetailResponse {
  id: string
  status: string
  end_user_id: string | null
  session_id: string | null
  feature_tag: string | null
  deployment_version: string | null
  total_cost_usd: string | null
  total_input_tokens: number | null
  total_output_tokens: number | null
  started_at: string
  ended_at: string | null
  duration_ms: number | null
  spans: SpanDetail[]
  provider_calls: ProviderCallDetail[]
  tool_calls: ToolCallDetail[]
}

export interface GraphNodeData {
  span_type: string
  status: string
  cost_usd: string | null
  input_tokens: number | null
  output_tokens: number | null
  latency_ms: number | null
  model: string | null
  provider: string | null
  error_type: string | null
  started_at: string | null
  ended_at: string | null
  duration_ms: number | null
  metadata: Record<string, unknown> | null
}

export interface GraphNode {
  id: string
  label: string
  data: GraphNodeData
}

export interface GraphEdge {
  id: string
  source: string
  target: string
}

export interface RunGraphResponse {
  run_id: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AnalyticsSummary {
  total_cost_usd: string
  total_input_tokens: number
  total_output_tokens: number
  run_count: number
  call_count: number
  prev_cost_usd: string
  cost_delta_pct: string | null
}

export interface SpendPoint {
  period: string
  cost_usd: string
  input_tokens: number
  output_tokens: number
  call_count: number
}

export interface SpendOverTime {
  granularity: string
  points: SpendPoint[]
}

export interface ModelSpend {
  provider: string
  model: string
  cost_usd: string
  input_tokens: number
  output_tokens: number
  call_count: number
}

export interface SpendByModel {
  items: ModelSpend[]
}

export interface UserSpend {
  end_user_id: string
  cost_usd: string
  run_count: number
  call_count: number
  avg_cost_per_run: string
  last_active: string | null
}

export interface SpendByUser {
  items: UserSpend[]
}

export interface FeatureSpend {
  feature_tag: string | null
  cost_usd: string
  run_count: number
  call_count: number
}

export interface SpendByFeature {
  items: FeatureSpend[]
}

export interface UserSpendDetail {
  end_user_id: string
  cost_usd: string
  run_count: number
  call_count: number
  avg_cost_per_run: string
  last_active: string | null
  spend_over_time: SpendPoint[]
  models_used: ModelSpend[]
  features_used: FeatureSpend[]
}
