/** Prompts, evaluations, datasets, experiments, replay, playground, vector stores, agent memory and plugins. */
import type { DatasetList, DatasetResponse, ExperimentList, ExperimentResponse, ExperimentResults, PromptList, PromptMetrics, PromptResponse, PromptVersion, ScoreEvent, ScoreList, VersionList, EvalDataset, EvalDatasetList, EvalExperiment, EvalExperimentList, ExperimentModelConfig, GithubConfig, GithubSyncResult, DatasetItem } from '@/types/api'
import { apiFetch } from './client'

// ── Phase 10 — Replay helpers ─────────────────────────────────────────────────

export async function createDataset(
  apiKey: string,
  body: { name: string; run_ids: string[]; source?: string }
): Promise<DatasetResponse> {
  return apiFetch<DatasetResponse>('/replay/datasets', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listDatasets(apiKey: string): Promise<DatasetList> {
  return apiFetch<DatasetList>('/replay/datasets', apiKey)
}

export async function createExperiment(
  apiKey: string,
  body: { dataset_id: string; name: string; configs: { model: string; label?: string }[] }
): Promise<ExperimentResponse> {
  return apiFetch<ExperimentResponse>('/replay/experiments', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listExperiments(
  apiKey: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<ExperimentList> {
  const qs = new URLSearchParams()
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<ExperimentList>(`/replay/experiments${query}`, apiKey)
}

export async function runExperiment(apiKey: string, id: string): Promise<ExperimentResponse> {
  return apiFetch<ExperimentResponse>(`/replay/experiments/${id}/run`, apiKey, { method: 'POST' })
}

export async function getExperimentResults(
  apiKey: string,
  id: string
): Promise<ExperimentResults> {
  return apiFetch<ExperimentResults>(`/replay/experiments/${id}/results`, apiKey)
}

// ── Phase 17 — Evaluations & Scores ───────────────────────────────────────────

export async function submitScore(
  apiKey: string,
  body: {
    name: string
    value: number
    run_id?: string | null
    span_id?: string | null
    label?: string | null
    source?: string
    confidence?: number | null
    evidence?: Record<string, unknown> | null
  }
): Promise<ScoreEvent> {
  return apiFetch<ScoreEvent>('/evaluations/scores', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listScores(
  apiKey: string,
  params: {
    run_id?: string
    name?: string
    source?: string
    from?: string
    to?: string
    access_group_id?: string
    api_key_id?: string
    limit?: number
  } = {}
): Promise<ScoreList> {
  const qs = new URLSearchParams()
  if (params.run_id) qs.set('run_id', params.run_id)
  if (params.name) qs.set('name', params.name)
  if (params.source) qs.set('source', params.source)
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  if (params.limit) qs.set('limit', String(params.limit))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<ScoreList>(`/evaluations/scores${query}`, apiKey)
}

// ── Phase 18 — Prompt Management ───────────────────────────────────────────────

export async function listPrompts(apiKey: string): Promise<PromptList> {
  return apiFetch<PromptList>('/prompts', apiKey)
}

export async function createPrompt(
  apiKey: string,
  body: { name: string; description?: string | null; default_environment?: string }
): Promise<PromptResponse> {
  return apiFetch<PromptResponse>('/prompts', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function getPrompt(apiKey: string, name: string): Promise<PromptResponse> {
  return apiFetch<PromptResponse>(`/prompts/${encodeURIComponent(name)}`, apiKey)
}

export async function deletePrompt(apiKey: string, name: string): Promise<void> {
  return apiFetch<void>(`/prompts/${encodeURIComponent(name)}`, apiKey, {
    method: 'DELETE',
  })
}

export async function createVersion(
  apiKey: string,
  name: string,
  body: {
    content: string
    variables?: Array<{ name: string; type?: string; description?: string }>
    commit_message?: string | null
    environment?: string
    model_hint?: string | null
  }
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(
    `/prompts/${encodeURIComponent(name)}/versions`,
    apiKey,
    { method: 'POST', body: JSON.stringify(body) }
  )
}

export async function listVersions(
  apiKey: string,
  name: string,
  environment?: string
): Promise<VersionList> {
  const qs = environment ? `?environment=${encodeURIComponent(environment)}` : ''
  return apiFetch<VersionList>(
    `/prompts/${encodeURIComponent(name)}/versions${qs}`,
    apiKey
  )
}

export async function getLatestVersion(
  apiKey: string,
  name: string,
  environment = 'production'
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(
    `/prompts/${encodeURIComponent(name)}/latest?environment=${environment}`,
    apiKey
  )
}

export async function promoteVersion(
  apiKey: string,
  name: string,
  body: {
    source_environment?: string
    target_environment?: string
    commit_message?: string | null
  }
): Promise<PromptVersion> {
  return apiFetch<PromptVersion>(
    `/prompts/${encodeURIComponent(name)}/promote`,
    apiKey,
    { method: 'POST', body: JSON.stringify(body) }
  )
}

export async function getPromptMetrics(
  apiKey: string,
  name: string
): Promise<PromptMetrics> {
  return apiFetch<PromptMetrics>(
    `/prompts/${encodeURIComponent(name)}/metrics`,
    apiKey
  )
}

// ── Evaluators ────────────────────────────────────────────────────────────────

export async function listEvaluators(apiKey: string): Promise<import('@/types/api').EvaluatorList> {
  return apiFetch<import('@/types/api').EvaluatorList>('/evaluations/evaluators', apiKey)
}

export async function createEvaluator(
  apiKey: string,
  body: { name: string; description?: string; type: string; config: Record<string, unknown> }
): Promise<import('@/types/api').EvaluatorResponse> {
  return apiFetch<import('@/types/api').EvaluatorResponse>('/evaluations/evaluators', apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function deleteEvaluator(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/evaluations/evaluators/${id}`, apiKey, { method: 'DELETE' })
}

export async function runEvaluator(
  apiKey: string,
  id: string,
  body?: { limit?: number }
): Promise<import('@/types/api').EvaluatorRunResult> {
  return apiFetch<import('@/types/api').EvaluatorRunResult>(`/evaluations/evaluators/${id}/run`, apiKey, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? { limit: 100 }),
  })
}

// ── Eval Datasets ──────────────────────────────────────────────────────────────

export async function listEvalDatasets(apiKey: string, limit = 50): Promise<EvalDatasetList> {
  return apiFetch<EvalDatasetList>(`/datasets?limit=${limit}`, apiKey)
}

export async function createEvalDataset(
  apiKey: string,
  data: { name: string; description?: string; source?: string; items?: DatasetItem[] }
): Promise<EvalDataset> {
  return apiFetch<EvalDataset>('/datasets', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function getEvalDataset(apiKey: string, id: string): Promise<EvalDataset> {
  return apiFetch<EvalDataset>(`/datasets/${id}`, apiKey)
}

export async function updateEvalDataset(
  apiKey: string,
  id: string,
  data: { name?: string; description?: string; items?: DatasetItem[] }
): Promise<EvalDataset> {
  return apiFetch<EvalDataset>(`/datasets/${id}`, apiKey, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteEvalDataset(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/datasets/${id}`, apiKey, { method: 'DELETE' })
}

// ── Eval Experiments ───────────────────────────────────────────────────────────

export async function listEvalExperiments(
  apiKey: string,
  params: { limit?: number; access_group_id?: string; api_key_id?: string } = {}
): Promise<EvalExperimentList> {
  const qs = new URLSearchParams()
  qs.set('limit', String(params.limit ?? 50))
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.api_key_id) qs.set('api_key_id', params.api_key_id)
  return apiFetch<EvalExperimentList>(`/experiments?${qs.toString()}`, apiKey)
}

export async function createEvalExperiment(
  apiKey: string,
  data: {
    name: string
    description?: string
    dataset_id?: string
    prompt_name?: string
    prompt_version?: number
    evaluator_ids?: string[]
    models?: ExperimentModelConfig[]
  }
): Promise<EvalExperiment> {
  return apiFetch<EvalExperiment>('/experiments', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function getEvalExperiment(apiKey: string, id: string): Promise<EvalExperiment> {
  return apiFetch<EvalExperiment>(`/experiments/${id}`, apiKey)
}

export async function deleteEvalExperiment(apiKey: string, id: string): Promise<void> {
  return apiFetch<void>(`/experiments/${id}`, apiKey, { method: 'DELETE' })
}

export async function runEvalExperiment(apiKey: string, id: string): Promise<EvalExperiment> {
  return apiFetch<EvalExperiment>(`/experiments/${id}/run`, apiKey, { method: 'POST' })
}

// ── GitHub Sync ────────────────────────────────────────────────────────────────

export async function getGithubConfig(apiKey: string): Promise<GithubConfig | null> {
  try {
    return await apiFetch<GithubConfig>('/prompts/github-config', apiKey)
  } catch {
    return null
  }
}

export async function saveGithubConfig(
  apiKey: string,
  data: { repo: string; branch: string; path_prefix: string; token?: string; auto_sync?: boolean },
  exists: boolean
): Promise<GithubConfig> {
  return apiFetch<GithubConfig>('/prompts/github-config', apiKey, {
    method: exists ? 'PUT' : 'POST',
    body: JSON.stringify(data),
  })
}

export async function pushToGithub(apiKey: string): Promise<GithubSyncResult> {
  return apiFetch<GithubSyncResult>('/prompts/sync/push', apiKey, { method: 'POST' })
}

export async function pullFromGithub(apiKey: string): Promise<GithubSyncResult> {
  return apiFetch<GithubSyncResult>('/prompts/sync/pull', apiKey, { method: 'POST' })
}

// ── Agent Memory ──────────────────────────────────────────────────────────

export async function getAgentMemories(
  apiKey: string,
  agentId: string,
  params: { memory_type?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').AgentMemoryListResponse> {
  const qs = new URLSearchParams()
  if (params.memory_type) qs.set('memory_type', params.memory_type)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').AgentMemoryListResponse>(`/agents/${agentId}/memory${query}`, apiKey)
}

export async function getAgentMemoryStats(
  apiKey: string,
  agentId: string
): Promise<import('@/types/api').AgentMemoryStats> {
  return apiFetch<import('@/types/api').AgentMemoryStats>(`/agents/${agentId}/memory/stats`, apiKey)
}

export async function getAgentMemoryAudit(
  apiKey: string,
  agentId: string,
  params: { limit?: number; offset?: number } = {}
): Promise<import('@/types/api').AgentMemoryAuditListResponse> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').AgentMemoryAuditListResponse>(`/agents/${agentId}/memory/audit${query}`, apiKey)
}

export async function searchAgentMemory(
  apiKey: string,
  agentId: string,
  data: { query: string; memory_type?: string; limit?: number }
): Promise<import('@/types/api').AgentMemoryListResponse> {
  return apiFetch<import('@/types/api').AgentMemoryListResponse>(`/agents/${agentId}/memory/search`, apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAgentMemory(
  apiKey: string,
  agentId: string,
  key: string
): Promise<void> {
  return apiFetch<void>(`/agents/${agentId}/memory/${encodeURIComponent(key)}`, apiKey, { method: 'DELETE' })
}

// ── Vector Store Management ───────────────────────────────────────────────

export async function getVectorCollections(
  apiKey: string,
  params: { status?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').VectorCollectionListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').VectorCollectionListResponse>(`/vector-stores${query}`, apiKey)
}

export async function createVectorCollection(
  apiKey: string,
  data: { name: string; qdrant_collection: string; description?: string; embedding_model?: string; dimensions?: number; distance_metric?: string; config?: Record<string, unknown> }
): Promise<import('@/types/api').VectorCollectionResponse> {
  return apiFetch<import('@/types/api').VectorCollectionResponse>('/vector-stores', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteVectorCollection(
  apiKey: string,
  collectionId: string
): Promise<void> {
  await apiFetch<void>(`/vector-stores/${collectionId}`, apiKey, { method: 'DELETE' })
}

export async function getVectorCollection(
  apiKey: string,
  collectionId: string
): Promise<import('@/types/api').VectorCollectionResponse> {
  return apiFetch<import('@/types/api').VectorCollectionResponse>(`/vector-stores/${collectionId}`, apiKey)
}

export async function getVectorCollectionStats(
  apiKey: string,
  collectionId: string
): Promise<import('@/types/api').VectorCollectionStats> {
  return apiFetch<import('@/types/api').VectorCollectionStats>(`/vector-stores/${collectionId}/stats`, apiKey)
}

export async function getVectorQueries(
  apiKey: string,
  collectionId: string,
  params: { limit?: number; offset?: number } = {}
): Promise<import('@/types/api').VectorQueryListResponse> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').VectorQueryListResponse>(`/vector-stores/${collectionId}/queries${query}`, apiKey)
}

export async function testVectorSearch(
  apiKey: string,
  collectionId: string,
  data: { query: string; top_k?: number; threshold?: number }
): Promise<import('@/types/api').VectorSearchTestResponse> {
  return apiFetch<import('@/types/api').VectorSearchTestResponse>(`/vector-stores/${collectionId}/search-test`, apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ── API Playground ────────────────────────────────────────────────────────

export async function getPlaygroundSessions(
  apiKey: string,
  params: { favorites_only?: boolean; access_group_id?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').PlaygroundSessionListResponse> {
  const qs = new URLSearchParams()
  if (params.favorites_only) qs.set('favorites_only', 'true')
  if (params.access_group_id) qs.set('access_group_id', params.access_group_id)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').PlaygroundSessionListResponse>(`/playground/sessions${query}`, apiKey)
}

export async function getPlaygroundHistory(
  apiKey: string,
  params: { session_id?: string; model?: string; limit?: number; offset?: number } = {}
): Promise<import('@/types/api').PlaygroundRequestListResponse> {
  const qs = new URLSearchParams()
  if (params.session_id) qs.set('session_id', params.session_id)
  if (params.model) qs.set('model', params.model)
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.offset) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<import('@/types/api').PlaygroundRequestListResponse>(`/playground/history${query}`, apiKey)
}

export async function sendPlaygroundRequest(
  apiKey: string,
  data: {
    model: string
    provider?: string
    system_prompt?: string
    user_prompt: string
    session_id?: string
    parameters?: Record<string, unknown>
  }
): Promise<import('@/types/api').PlaygroundRequestResponse> {
  return apiFetch<import('@/types/api').PlaygroundRequestResponse>('/playground/send', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function comparePlaygroundModels(
  apiKey: string,
  data: {
    models: string[]
    system_prompt?: string
    user_prompt: string
    parameters?: Record<string, unknown>
  }
): Promise<import('@/types/api').PlaygroundCompareResponse> {
  return apiFetch<import('@/types/api').PlaygroundCompareResponse>('/playground/compare', apiKey, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function seedDefaultPlugins(apiKey: string): Promise<{ status: string; plugins_added: number; total: number }> {
  return apiFetch<{ status: string; plugins_added: number; total: number }>('/plugins/seed-defaults', apiKey, { method: 'POST' })
}

// ── Plugins ──────────────────────────────────────────────────────────────

export async function createPlugin(
  apiKey: string,
  data: { name: string; plugin_type: string; hooks?: string[]; config?: Record<string, unknown>; priority?: number; version?: string; author?: string; description?: string }
): Promise<import('@/types/api').PluginResponse> {
  return apiFetch<import('@/types/api').PluginResponse>('/plugins', apiKey, { method: 'POST', body: JSON.stringify(data) })
}

export async function listPlugins(apiKey: string, includeInactive = false): Promise<import('@/types/api').PluginList> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return apiFetch<import('@/types/api').PluginList>(`/plugins${qs}`, apiKey)
}

export async function getPlugin(apiKey: string, id: string): Promise<import('@/types/api').PluginResponse> {
  return apiFetch<import('@/types/api').PluginResponse>(`/plugins/${id}`, apiKey)
}

export async function updatePlugin(apiKey: string, id: string, data: Record<string, unknown>): Promise<import('@/types/api').PluginResponse> {
  return apiFetch<import('@/types/api').PluginResponse>(`/plugins/${id}`, apiKey, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deletePlugin(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/plugins/${id}`, apiKey, { method: 'DELETE' })
}

export async function listPluginExecutions(apiKey: string, pluginId: string, limit = 50): Promise<import('@/types/api').PluginExecutionList> {
  return apiFetch<import('@/types/api').PluginExecutionList>(`/plugins/${pluginId}/executions?limit=${limit}`, apiKey)
}
