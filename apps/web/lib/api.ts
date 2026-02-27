import type {
  AnalyticsSummary,
  BreachList,
  Budget,
  BudgetList,
  RunDetailResponse,
  RunGraphResponse,
  RunListResponse,
  SpendByFeature,
  SpendByModel,
  SpendByUser,
  SpendOverTime,
  UserSpendDetail,
} from '@/types/api'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
      ...init?.headers,
    },
    cache: 'no-store',
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

export async function getRuns(
  apiKey: string,
  params: {
    limit?: number
    cursor?: string
    status?: string
    feature_tag?: string
    end_user_id?: string
    search?: string
    from?: string
    to?: string
  } = {}
): Promise<RunListResponse> {
  const qs = new URLSearchParams()
  if (params.limit) qs.set('limit', String(params.limit))
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.status) qs.set('status', params.status)
  if (params.feature_tag) qs.set('feature_tag', params.feature_tag)
  if (params.end_user_id) qs.set('end_user_id', params.end_user_id)
  if (params.search) qs.set('search', params.search)
  if (params.from) qs.set('from', params.from)
  if (params.to) qs.set('to', params.to)

  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<RunListResponse>(`/runs${query}`, apiKey)
}

export async function getRun(apiKey: string, runId: string): Promise<RunDetailResponse> {
  return apiFetch<RunDetailResponse>(`/runs/${runId}`, apiKey)
}

export async function getRunGraph(apiKey: string, runId: string): Promise<RunGraphResponse> {
  return apiFetch<RunGraphResponse>(`/runs/${runId}/graph`, apiKey)
}

// ── Analytics helpers ─────────────────────────────────────────────────────────

interface TimeWindow {
  from?: string
  to?: string
}

function _analyticsQs(params: TimeWindow & Record<string, string | undefined>): string {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) qs.set(k, v)
  })
  const s = qs.toString()
  return s ? `?${s}` : ''
}

export async function getAnalyticsSummary(
  apiKey: string,
  window: TimeWindow = {}
): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>(
    `/analytics/summary${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getSpendOverTime(
  apiKey: string,
  granularity: 'hourly' | 'daily' = 'daily',
  window: TimeWindow = {}
): Promise<SpendOverTime> {
  return apiFetch<SpendOverTime>(
    `/analytics/spend-over-time${_analyticsQs({ granularity, ...window })}`,
    apiKey
  )
}

export async function getSpendByModel(
  apiKey: string,
  window: TimeWindow = {}
): Promise<SpendByModel> {
  return apiFetch<SpendByModel>(
    `/analytics/spend-by-model${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getSpendByFeature(
  apiKey: string,
  window: TimeWindow = {}
): Promise<SpendByFeature> {
  return apiFetch<SpendByFeature>(
    `/analytics/spend-by-feature${_analyticsQs(window)}`,
    apiKey
  )
}

export async function getSpendByUser(
  apiKey: string,
  limit?: number,
  window: TimeWindow = {}
): Promise<SpendByUser> {
  return apiFetch<SpendByUser>(
    `/analytics/spend-by-user${_analyticsQs({
      ...(limit !== undefined ? { limit: String(limit) } : {}),
      ...window,
    })}`,
    apiKey
  )
}

export async function getUserSpend(
  apiKey: string,
  userId: string,
  window: TimeWindow = {}
): Promise<UserSpendDetail> {
  return apiFetch<UserSpendDetail>(
    `/analytics/users/${encodeURIComponent(userId)}${_analyticsQs(window)}`,
    apiKey
  )
}

// ── Budget helpers ─────────────────────────────────────────────────────────────

export async function getBudgets(apiKey: string): Promise<BudgetList> {
  return apiFetch<BudgetList>('/budgets', apiKey)
}

export async function createBudget(
  apiKey: string,
  body: {
    scope_type: string
    scope_id?: string | null
    period_type: string
    limit_usd: number
    action: string
    downgrade_to_model?: string | null
  }
): Promise<Budget> {
  return apiFetch<Budget>('/budgets', apiKey, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function deleteBudget(apiKey: string, id: string): Promise<void> {
  await apiFetch<void>(`/budgets/${id}`, apiKey, { method: 'DELETE' })
}

export async function getBudgetBreaches(apiKey: string, id: string): Promise<BreachList> {
  return apiFetch<BreachList>(`/budgets/${id}/breaches`, apiKey)
}
