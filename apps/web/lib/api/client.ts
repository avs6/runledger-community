/** Shared fetch helpers and types for the API client modules (split from lib/api.ts). */
import type { AnalyticsExport, CapturePolicyResponse } from '@/types/api'

// Where API calls go (review P-06, BFF):
//   * Browser: the same-origin BFF proxy (`/api/rl/*`). It reads the session key from the
//     httpOnly NextAuth cookie and adds the Authorization header server-side, so the key
//     is never readable by browser JS. `session.apiKey` on the client is only the
//     placeholder BFF_SESSION_KEY; callers keep passing it, so apiFetch's signature and
//     every page that uses it stay unchanged.
//   * Server (RSC / route handlers): the API directly at API_URL (an internal URL never
//     exposed to the browser), with the real key resolved from the session cookie.

/** Placeholder `session.apiKey` the browser sees instead of the real session key. */
export const BFF_SESSION_KEY = 'bff-session'

/** Same-origin path of the BFF proxy (app/api/rl/[...path]/route.ts). */
export const BFF_BASE_PATH = '/api/rl'

const SERVER_API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201'

export const API_URL = typeof window === 'undefined' ? SERVER_API_URL : BFF_BASE_PATH

/**
 * Authorization header for a call. In the browser there is none: the BFF adds it. On the
 * server, the placeholder is swapped for the real key from the session cookie (via the
 * resolver lib/server-session.ts registers); explicit keys (scripts, tests) pass through.
 */
export async function authHeaders(apiKey: string | null | undefined): Promise<Record<string, string>> {
  if (typeof window !== 'undefined') return {}
  let key = apiKey ?? ''
  if (!key || key === BFF_SESSION_KEY) {
    key = (await globalThis.__runledgerSessionKey?.()) ?? ''
  }
  return key ? { Authorization: `Bearer ${key}` } : {}
}

/** fetch() against the API (via the BFF in the browser) with auth applied. */
export async function apiRequest(path: string, apiKey: string | null | undefined, init?: RequestInit): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    cache: 'no-store',
    ...init,
    headers: { ...(await authHeaders(apiKey)), ...(init?.headers as Record<string, string> | undefined) },
  })
}

async function redirectToLogin(): Promise<never> {
  if (typeof window !== 'undefined') {
    window.location.href = '/login'
    throw new Error('API 401: session expired')
  }
  const { redirect } = await import('next/navigation')
  return redirect('/login')
}

export async function apiFetch<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  const res = await apiRequest(path, apiKey, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers as Record<string, string> | undefined) },
  })

  if (res.status === 401) await redirectToLogin()

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** One page of a list endpoint on the pagination standard: rows plus X-Total-Count. */
export interface Page<T> {
  items: T[]
  total: number
}

/**
 * GET a paginated list (`?limit=&offset=`) and read the total from X-Total-Count. Accepts
 * endpoints that return either a bare array or `{ items: [...] }`.
 */
export async function apiFetchPage<T>(path: string, apiKey: string): Promise<Page<T>> {
  const res = await apiRequest(path, apiKey, { headers: { 'Content-Type': 'application/json' } })
  if (res.status === 401) await redirectToLogin()
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  const body = await res.json()
  const items: T[] = Array.isArray(body) ? body : (body?.items ?? [])
  const header = res.headers.get('x-total-count')
  const total = header != null ? Number(header) : typeof body?.total === 'number' ? body.total : items.length
  return { items, total }
}

// ── Analytics helpers ─────────────────────────────────────────────────────────

export interface TimeWindow {
  from?: string
  to?: string
  [key: string]: string | number | boolean | undefined
}

export function _analyticsQs(params: TimeWindow & Record<string, string | number | boolean | undefined>): string {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) qs.set(k, String(v))
  })
  const s = qs.toString()
  return s ? `?${s}` : ''
}

export async function exportPeriodCsv(
  apiKey: string,
  id: string,
  params: { access_group_id?: string; api_key_id?: string } = {}
): Promise<string> {
  const query = new URLSearchParams({ format: 'csv' })
  if (params.access_group_id) query.set('access_group_id', params.access_group_id)
  if (params.api_key_id) query.set('api_key_id', params.api_key_id)
  const res = await apiRequest(`/billing/periods/${id}/export?${query.toString()}`, apiKey)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.text()
}




export async function listWebhookDeliveries(
  apiKey: string,
  webhookId: string
): Promise<import('@/types/api').BillingWebhookDeliveryList> {
  void apiKey
  void webhookId
  return { items: [] }
}

// ── Phase 11 — Privacy helpers ─────────────────────────────────────────────────

export async function getCapturePolicy(
  apiKey: string
): Promise<CapturePolicyResponse | null> {
  const res = await apiRequest(`/privacy/capture-policy`, apiKey)
  if (res.status === 404) {
    // Drain the body so the connection is released (an unread body keeps the request open).
    await res.text().catch(() => '')
    return null
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<CapturePolicyResponse>
}

// ── Identity registry (org-admin) — Users page ────────────────────────────────
export interface OrgUser {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  email_verified: boolean
  org_role: string | null
  org_status?: string | null
  last_login_at: string | null
  created_at: string
  /** False when the account is shared with another org or is a platform admin. */
  can_manage_identity?: boolean
  must_change_password?: boolean
  /** Only returned once, by createOrgUser, when a password was generated. */
  temporary_password?: string | null
}

export async function importProviderPricing(
  apiKey: string,
  file: File,
): Promise<import('@/types/api').PricingImportResult> {
  const form = new FormData()
  form.append('file', file)
  // No Content-Type: the browser sets the multipart boundary.
  const res = await apiRequest('/providers/pricing/import', apiKey, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}

export async function getPricingExampleYaml(apiKey: string): Promise<string> {
  const res = await apiRequest(`/providers/pricing/example`, apiKey)
  if (!res.ok) throw new Error(`API ${res.status}`)
  return res.text()
}

// ── Phase 14 — Integrations helpers ────────────────────────────────────────────

export async function exportAnalytics(
  apiKey: string,
  format: 'csv' | 'json' = 'json',
  from?: string,
  to?: string
): Promise<AnalyticsExport | string> {
  const qs = new URLSearchParams({ format })
  if (from) qs.set('from', from)
  if (to) qs.set('to', to)

  const res = await apiRequest(`/analytics/export?${qs.toString()}`, apiKey)

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }

  if (format === 'csv') {
    return res.text()
  }

  return res.json() as Promise<AnalyticsExport>
}

export async function uploadInvoice(
  apiKey: string,
  file: File,
  periodStart: string,
  periodEnd: string,
  provider?: string
): Promise<import('@/types/api').InvoiceResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const qs = new URLSearchParams({ period_start: periodStart, period_end: periodEnd })
  if (provider) qs.set('provider', provider)
  const res = await apiRequest(`/invoices/upload?${qs}`, apiKey, { method: 'POST', body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `Upload failed: ${res.status}`)
  }
  return res.json()
}

// ── Phase 13: Audit Export ───────────────────────────────────────────────────

export async function exportAuditEvents(
  apiKey: string,
  format: 'csv' | 'json' = 'csv',
  action?: string,
  targetType?: string
): Promise<string> {
  const qs = new URLSearchParams({ format })
  if (action) qs.set('action', action)
  if (targetType) qs.set('target_type', targetType)
  const res = await apiRequest(`/audit/events/export?${qs}`, apiKey)
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

export async function exportRunbook(
  apiKey: string,
  runbookId: string,
  format: 'markdown' | 'json' = 'markdown'
): Promise<string> {
  const res = await apiRequest(`/runbooks/${runbookId}/export?format=${format}`, apiKey)
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

export async function exportChargebackReport(
  apiKey: string,
  params?: { period?: string; dimension?: string; format?: 'csv' | 'json'; access_group_id?: string; api_key_id?: string; end_user_id?: string }
): Promise<string> {
  const q = new URLSearchParams({ format: params?.format ?? 'csv' })
  if (params?.period) q.set('period', params.period)
  if (params?.dimension) q.set('dimension', params.dimension)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_id) q.set('api_key_id', params.api_key_id)
  if (params?.end_user_id) q.set('end_user_id', params.end_user_id)
  const res = await apiRequest(`/billing/chargeback-report/export?${q}`, apiKey)
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

export async function exportGovernanceAuditPack(
  apiKey: string,
  params?: { from?: string; to?: string; format?: 'json' | 'csv' }
): Promise<string> {
  const q = new URLSearchParams({ format: params?.format ?? 'json' })
  if (params?.from) q.set('from', params.from)
  if (params?.to) q.set('to', params.to)
  const res = await apiRequest(`/governance/audit-pack/export?${q}`, apiKey)
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

export async function exportBilling(
  apiKey: string,
  format: 'csv' | 'json' = 'json',
  months?: number
): Promise<Blob> {
  const params = new URLSearchParams({ format })
  if (months) params.set('months', String(months))
  const res = await apiRequest(`/budgets/billing-export?${params}`, apiKey)
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  return res.blob()
}

export interface HubAccessRequestResult { status: 'requested' | 'pending'; approval_id: string; model_id: string; total_requests: number }
export function apiErrorMessage(err: unknown, fallback = 'Request failed'): string {
  if (!(err instanceof Error)) return fallback
  const match = err.message.match(/^API \d+: ([\s\S]*)$/)
  if (!match) return err.message || fallback
  try {
    const body = JSON.parse(match[1])
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return String(body.detail[0].msg)
  } catch {
    /* not JSON */
  }
  return match[1] || fallback
}

export interface SessionKey {
  id: string
  workspace_id: string
  workspace_name: string | null
  key_prefix: string
  name: string | null
  created_at: string
  expires_at: string | null
  last_used_at: string | null
  current: boolean
}

export interface PendingInvitation {
  tenant_id: string
  tenant_name: string
  role: string
  invited_by_email: string | null
  created_at: string
}

// ── Related context (replaces per-page posture endpoints) ──────────────────────

export type ContextEntity = 'workspace' | 'workflow' | 'api_key' | 'route' | 'budget' | 'prompt'
