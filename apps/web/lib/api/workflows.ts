/** Workflows (the product's top-level object) and the agent registry. Runs are a view
 * over agent_runs, attributed at ingest; see docs/workflows.md. */
import { apiFetch, type Page } from './client'

// ── Agent Registry ─────────────────────────────────────────────────────────

export async function getAgents(
  apiKey: string,
  params: { status?: string; agent_type?: string; q?: string; api_key_id?: string; limit?: number; offset?: number } = {},
): Promise<import('@/types/api').AgentListResponse> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') qs.set(k, String(v))
  const query = qs.toString() ? `?${qs}` : ''
  return apiFetch<import('@/types/api').AgentListResponse>(`/agents${query}`, apiKey)
}

export async function getAgent(
  apiKey: string,
  agentId: string
): Promise<import('@/types/api').AgentResponse> {
  return apiFetch<import('@/types/api').AgentResponse>(`/agents/${agentId}`, apiKey)
}

export async function getAgentStats(
  apiKey: string,
  agentId: string,
  days?: number,
): Promise<import('@/types/api').AgentStats> {
  return apiFetch<import('@/types/api').AgentStats>(`/agents/${agentId}/stats${days ? `?days=${days}` : ''}`, apiKey)
}

/** Runs attributed to an agent, as one DataTable page (total from X-Total-Count). */
export async function getAgentRunsPage(
  apiKey: string,
  agentId: string,
  params: { limit: number; offset: number; status?: string },
): Promise<Page<import('@/types/api').RunSummary>> {
  const qs = new URLSearchParams({ limit: String(params.limit), offset: String(params.offset) })
  if (params.status) qs.set('status', params.status)
  const body = await apiFetch<import('@/types/api').RunSummaryListResponse>(`/agents/${agentId}/runs?${qs}`, apiKey)
  return { items: body.runs, total: body.total }
}

export async function createAgent(
  apiKey: string,
  body: Partial<Omit<import('@/types/api').AgentResponse, 'id' | 'workspace_id' | 'created_at' | 'updated_at'>> & { name: string },
): Promise<import('@/types/api').AgentResponse> {
  return apiFetch<import('@/types/api').AgentResponse>('/agents', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateAgent(
  apiKey: string,
  agentId: string,
  body: Partial<Omit<import('@/types/api').AgentResponse, 'id' | 'workspace_id' | 'created_at' | 'updated_at'>>,
): Promise<import('@/types/api').AgentResponse> {
  return apiFetch<import('@/types/api').AgentResponse>(`/agents/${agentId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function retireAgent(apiKey: string, agentId: string): Promise<void> {
  return apiFetch<void>(`/agents/${agentId}`, apiKey, { method: 'DELETE' })
}

// ── Workflows (runs are a view over agent_runs) ────────────────────────────

export interface WorkflowListParams {
  status?: string
  q?: string
  days?: number
  sort?: string
  dir?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export async function getWorkflows(
  apiKey: string,
  params: WorkflowListParams = {},
): Promise<import('@/types/api').WorkflowDefinitionListResponse> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== '') qs.set(k, String(v))
  const query = qs.toString() ? `?${qs}` : ''
  return apiFetch<import('@/types/api').WorkflowDefinitionListResponse>(`/workflows${query}`, apiKey)
}

/** One page of workflows (with stats) for DataTable. */
export async function getWorkflowsPage(
  apiKey: string,
  params: WorkflowListParams,
): Promise<Page<import('@/types/api').WorkflowDefinitionResponse>> {
  const body = await getWorkflows(apiKey, params)
  return { items: body.workflows, total: body.total }
}

export async function getWorkflow(
  apiKey: string,
  workflowId: string,
): Promise<import('@/types/api').WorkflowDefinitionResponse> {
  return apiFetch<import('@/types/api').WorkflowDefinitionResponse>(`/workflows/${workflowId}`, apiKey)
}

export async function createWorkflow(
  apiKey: string,
  body: import('@/types/api').WorkflowInput & { name: string },
): Promise<import('@/types/api').WorkflowDefinitionResponse> {
  return apiFetch<import('@/types/api').WorkflowDefinitionResponse>('/workflows', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function updateWorkflow(
  apiKey: string,
  workflowId: string,
  body: import('@/types/api').WorkflowInput,
): Promise<import('@/types/api').WorkflowDefinitionResponse> {
  return apiFetch<import('@/types/api').WorkflowDefinitionResponse>(`/workflows/${workflowId}`, apiKey, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

/** Archive: the workflow stops matching new traffic; its runs keep their history. */
export async function archiveWorkflow(apiKey: string, workflowId: string): Promise<void> {
  return apiFetch<void>(`/workflows/${workflowId}`, apiKey, { method: 'DELETE' })
}

export async function getWorkflowOverview(
  apiKey: string,
  workflowId: string,
  days = 30,
): Promise<import('@/types/api').WorkflowOverview> {
  return apiFetch<import('@/types/api').WorkflowOverview>(`/workflows/${workflowId}/overview?days=${days}`, apiKey)
}

export async function getWorkflowRunsPage(
  apiKey: string,
  workflowId: string,
  params: { limit: number; offset: number; status?: string },
): Promise<Page<import('@/types/api').RunSummary>> {
  const qs = new URLSearchParams({ limit: String(params.limit), offset: String(params.offset) })
  if (params.status) qs.set('status', params.status)
  const body = await apiFetch<import('@/types/api').RunSummaryListResponse>(`/workflows/${workflowId}/runs?${qs}`, apiKey)
  return { items: body.runs, total: body.total }
}

export async function getWorkflowCost(
  apiKey: string,
  workflowId: string,
  days = 30,
): Promise<import('@/types/api').WorkflowCostAttribution> {
  return apiFetch<import('@/types/api').WorkflowCostAttribution>(`/workflows/${workflowId}/cost?days=${days}`, apiKey)
}
