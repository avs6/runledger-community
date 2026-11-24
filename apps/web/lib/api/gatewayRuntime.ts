/** Gateway runtime: per-run decision trace ("why this route") and run-linked requests. */
import type { GatewayRequestList } from '@/types/api'
import { apiFetch } from './client'

export interface GatewayDecisionRoute {
  alias?: string
  requested?: string
  reason?: string | null
  primary_route_id?: string
  served?: {
    route_id: string
    alias: string
    provider: string
    target_model: string
    region?: string | null
    reason?: string | null
    shadow?: boolean
  }
}

export interface GatewayDecisionCandidate {
  route_id: string
  alias: string
  provider: string
  target_model: string
  trigger: string
  region?: string | null
}

export interface GatewayDecision {
  version?: number
  request_id?: string
  model_requested?: string
  route?: GatewayDecisionRoute
  cache?: { result?: string; exact?: string; semantic?: string }
  budget?: { status?: string; budget_id?: string | null; rerouted_from?: string | null }
  guardrail?: { result?: string; pre_call?: string; post_call?: string; checked?: number; reason?: string }
  prompt?: {
    prompt_ref?: string
    prompt_name?: string
    prompt_version?: number
    prompt_environment?: string
    missing_variables?: string[]
  }
  intelligent_routing?: { alias?: string | null; reason?: string | null; task_class?: string | null }
  candidates?: GatewayDecisionCandidate[]
  skipped_routes?: Array<{ route_id: string; alias: string; why: string }>
}

export interface GatewayRunDecision {
  run_id: string
  gateway_request_id: string | null
  decision: GatewayDecision | null
  decision_header: string | null
  status: string | null
  latency_ms: number | null
  gateway_overhead_ms: number | null
  workflow: string | null
  api_key_id: string | null
  guardrail_events: Array<{
    guardrail_name: string
    mode: string
    decision: string
    reason: string | null
    latency_ms: number | null
    created_at: string
  }>
}

export async function getGatewayRunDecision(apiKey: string, runId: string): Promise<GatewayRunDecision> {
  return apiFetch<GatewayRunDecision>(`/gateway/runs/${encodeURIComponent(runId)}/decision`, apiKey)
}

/** Gateway requests that recorded this run (persisted run_id; no time-window guess). */
export async function listGatewayRequestsForRun(apiKey: string, runId: string): Promise<GatewayRequestList> {
  return apiFetch<GatewayRequestList>(`/gateway/requests?run_id=${encodeURIComponent(runId)}&limit=5`, apiKey)
}
