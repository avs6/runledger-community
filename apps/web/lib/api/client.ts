/** Shared fetch helpers and types for the API client modules (split from lib/api.ts). */
import type { AnalyticsExport, CapturePolicyResponse } from '@/types/api'

// Server-side (SSR/RSC): use API_URL — an internal Docker/Railway URL not visible to the browser.
// Client-side (browser): use NEXT_PUBLIC_API_URL — baked at build time, must be browser-reachable.

export const API_URL =
  typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')

export async function apiFetch<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
      ...init?.headers,
    },
    cache: 'no-store',
  })

  if (res.status === 401) {
    const { redirect } = await import('next/navigation')
    redirect('/login')
  }

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
  const res = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (res.status === 401) {
    const { redirect } = await import('next/navigation')
    redirect('/login')
  }
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  const body = await res.json()
  const items: T[] = Array.isArray(body) ? body : (body?.items ?? [])
  const header = res.headers.get('x-total-count')
  const total = header != null ? Number(header) : typeof body?.total === 'number' ? body.total : items.length
  return { items, total }
}

export async function adminFetch<T>(path: string, adminSecret: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Secret': adminSecret,
      ...init?.headers,
    },
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
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
  const res = await fetch(`${API_URL}/billing/periods/${id}/export?${query.toString()}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
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
  const res = await fetch(`${API_URL}/privacy/capture-policy`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (res.status === 404) return null
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
  const res = await fetch(`${API_URL}/providers/pricing/import`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}` }, // no Content-Type — browser sets multipart boundary
    body: form,
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}

export async function getPricingExampleYaml(apiKey: string): Promise<string> {
  const res = await fetch(`${API_URL}/providers/pricing/example`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
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

  const res = await fetch(`${API_URL}/analytics/export?${qs.toString()}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })

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
  const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201'
  const res = await fetch(`${API_URL}/invoices/upload?${qs}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}` },
    body: formData,
  })
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
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
  const res = await fetch(`${API}/audit/events/export?${qs}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

export async function exportRunbook(
  apiKey: string,
  runbookId: string,
  format: 'markdown' | 'json' = 'markdown'
): Promise<string> {
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
  const res = await fetch(`${API}/runs/runbooks/${runbookId}/export?format=${format}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
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
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
  const res = await fetch(`${API}/billing/chargeback-report/export?${q}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.text()
}

export async function exportGovernanceAuditPack(
  apiKey: string,
  params?: { from?: string; to?: string; format?: 'json' | 'csv'; user_id?: string; access_group_id?: string; api_key_id?: string }
): Promise<string> {
  const q = new URLSearchParams({ format: params?.format ?? 'json' })
  if (params?.from) q.set('from', params.from)
  if (params?.to) q.set('to', params.to)
  if (params?.user_id) q.set('user_id', params.user_id)
  if (params?.access_group_id) q.set('access_group_id', params.access_group_id)
  if (params?.api_key_id) q.set('api_key_id', params.api_key_id)
  const API = typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201')
  const res = await fetch(`${API}/governance/audit-pack/export?${q}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
    cache: 'no-store',
  })
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
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8201'}/budgets/billing-export?${params}`, {
    headers: { Authorization: `Bearer ${apiKey}` },
  })
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
