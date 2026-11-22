'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { listGatewayPassThroughEndpoints, createGatewayPassThroughEndpoint, updateGatewayPassThroughEndpoint, deleteGatewayPassThroughEndpoint, testGatewayPassThroughEndpoint, listGatewayPassThroughStats } from '@/lib/api'
import type { GatewayPassThroughEndpoint, GatewayPassThroughEndpointStats, GatewayPassThroughTestResult } from '@/types/api'
import { inputCls, PassThroughEditState } from './shared'

export function PassThroughPanel({ apiKey, canManage }: { apiKey: string; canManage: boolean }) {
  const [items, setItems] = useState<GatewayPassThroughEndpoint[]>([])
  const [stats, setStats] = useState<Record<string, GatewayPassThroughEndpointStats>>({})
  const [testingId, setTestingId] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, GatewayPassThroughTestResult>>({})
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [slug, setSlug] = useState('')
  const [pathPrefix, setPathPrefix] = useState('/')
  const [upstreamBaseUrl, setUpstreamBaseUrl] = useState('')
  const [authType, setAuthType] = useState('')
  const [timeoutMs, setTimeoutMs] = useState('30000')
  const [rateLimitRpm, setRateLimitRpm] = useState('')
  const [costPerCallUsd, setCostPerCallUsd] = useState('')
  const [headerConfigStr, setHeaderConfigStr] = useState('{}')
  const [defaultQueryStr, setDefaultQueryStr] = useState('{}')
  const [editState, setEditState] = useState<PassThroughEditState | null>(null)
  const [savingEdit, setSavingEdit] = useState(false)
  const [editError, setEditError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [data, statsData] = await Promise.all([
        listGatewayPassThroughEndpoints(apiKey, true),
        listGatewayPassThroughStats(apiKey).catch(() => ({ items: [] })),
      ])
      setItems(data.items)
      setStats(
        Object.fromEntries(
          statsData.items.map((item) => [item.endpoint_id, item]),
        ),
      )
    } catch {
      toast.error('Failed to load pass-through endpoints')
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => { void load() }, [load])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    let headerConfig: Record<string, unknown> = {}
    let defaultQuery: Record<string, unknown> = {}
    try {
      headerConfig = JSON.parse(headerConfigStr || '{}')
      defaultQuery = JSON.parse(defaultQueryStr || '{}')
    } catch {
      toast.error('Header and query config must be valid JSON')
      return
    }
    setCreating(true)
    try {
      const created = await createGatewayPassThroughEndpoint(apiKey, {
        slug: slug.trim(),
        path_prefix: pathPrefix.trim() || '/',
        upstream_base_url: upstreamBaseUrl.trim(),
        auth_type: authType.trim() || null,
        timeout_ms: parseInt(timeoutMs, 10) || 30000,
        rate_limit_rpm: rateLimitRpm ? parseInt(rateLimitRpm, 10) : null,
        cost_per_call_usd: costPerCallUsd ? parseFloat(costPerCallUsd) : null,
        header_config: headerConfig,
        default_query: defaultQuery,
      })
      setItems((prev) => [created, ...prev])
      setSlug('')
      setPathPrefix('/')
      setUpstreamBaseUrl('')
      setAuthType('')
      setTimeoutMs('30000')
      setRateLimitRpm('')
      setCostPerCallUsd('')
      setHeaderConfigStr('{}')
      setDefaultQueryStr('{}')
      toast.success('Pass-through endpoint created')
    } catch {
      toast.error('Failed to create pass-through endpoint')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggle(item: GatewayPassThroughEndpoint) {
    try {
      const updated = await updateGatewayPassThroughEndpoint(apiKey, item.id, { is_active: !item.is_active })
      setItems((prev) => prev.map((cur) => (cur.id === item.id ? updated : cur)))
    } catch {
      toast.error('Failed to update pass-through endpoint')
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this pass-through endpoint?')) return
    try {
      await deleteGatewayPassThroughEndpoint(apiKey, id)
      setItems((prev) => prev.filter((item) => item.id !== id))
    } catch {
      toast.error('Failed to delete pass-through endpoint')
    }
  }

  async function handleTest(item: GatewayPassThroughEndpoint) {
    setTestingId(item.id)
    try {
      const result = await testGatewayPassThroughEndpoint(apiKey, item.id, {
        method: 'GET',
        path: '',
      })
      setTestResults((prev) => ({ ...prev, [item.id]: result }))
      toast.success(result.ok ? `Test succeeded (${result.status_code})` : `Test returned ${result.status_code}`)
    } catch {
      toast.error('Failed to test pass-through endpoint')
    } finally {
      setTestingId(null)
    }
  }

  function beginEdit(item: GatewayPassThroughEndpoint) {
    setEditError('')
    setEditState({
      id: item.id,
      pathPrefix: item.path_prefix,
      upstreamBaseUrl: item.upstream_base_url,
      authType: item.auth_type ?? '',
      authConfigStr: JSON.stringify(item.auth_config ?? {}, null, 2),
      timeoutMs: String(item.timeout_ms),
      rateLimitRpm: item.rate_limit_rpm != null ? String(item.rate_limit_rpm) : '',
      costPerCallUsd: item.cost_per_call_usd ?? '',
      headerConfigStr: JSON.stringify(item.header_config ?? {}, null, 2),
      defaultQueryStr: JSON.stringify(item.default_query ?? {}, null, 2),
      isActive: item.is_active,
    })
  }

  async function handleSaveEdit() {
    if (!editState) return
    let authConfig: Record<string, unknown> | null = null
    let headerConfig: Record<string, unknown> | null = null
    let defaultQuery: Record<string, unknown> | null = null
    try {
      authConfig = editState.authConfigStr.trim() ? JSON.parse(editState.authConfigStr) : null
      headerConfig = editState.headerConfigStr.trim() ? JSON.parse(editState.headerConfigStr) : null
      defaultQuery = editState.defaultQueryStr.trim() ? JSON.parse(editState.defaultQueryStr) : null
    } catch {
      setEditError('Auth, header, and query config must be valid JSON')
      return
    }
    setSavingEdit(true)
    setEditError('')
    try {
      const updated = await updateGatewayPassThroughEndpoint(apiKey, editState.id, {
        path_prefix: editState.pathPrefix.trim() || '/',
        upstream_base_url: editState.upstreamBaseUrl.trim(),
        auth_type: editState.authType.trim() || null,
        auth_config: authConfig,
        timeout_ms: parseInt(editState.timeoutMs, 10) || 30000,
        rate_limit_rpm: editState.rateLimitRpm ? parseInt(editState.rateLimitRpm, 10) : null,
        cost_per_call_usd: editState.costPerCallUsd ? parseFloat(editState.costPerCallUsd) : null,
        header_config: headerConfig,
        default_query: defaultQuery,
        is_active: editState.isActive,
      })
      setItems((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setEditState(null)
      toast.success('Pass-through endpoint updated')
      await load()
    } catch {
      toast.error('Failed to update pass-through endpoint')
    } finally {
      setSavingEdit(false)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold dark:text-white">Pass-Through Endpoints</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Register non-LLM upstream APIs behind the gateway with shared auth, timeout, and rate policy.
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {canManage && (
        <form onSubmit={handleCreate} className="grid gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4 sm:grid-cols-2">
          <input value={slug} onChange={(e) => setSlug(e.target.value)} className={inputCls} placeholder="slug (search-proxy)" required />
          <input value={pathPrefix} onChange={(e) => setPathPrefix(e.target.value)} className={inputCls} placeholder="/v1" />
          <input value={upstreamBaseUrl} onChange={(e) => setUpstreamBaseUrl(e.target.value)} className={inputCls + ' sm:col-span-2'} placeholder="https://upstream.example.com" required />
          <input value={authType} onChange={(e) => setAuthType(e.target.value)} className={inputCls} placeholder="bearer | api_key | none" />
          <input value={timeoutMs} onChange={(e) => setTimeoutMs(e.target.value)} className={inputCls} placeholder="30000" />
          <input value={rateLimitRpm} onChange={(e) => setRateLimitRpm(e.target.value)} className={inputCls} placeholder="Rate limit RPM" />
          <input value={costPerCallUsd} onChange={(e) => setCostPerCallUsd(e.target.value)} className={inputCls} placeholder="Cost per call USD" />
          <textarea value={headerConfigStr} onChange={(e) => setHeaderConfigStr(e.target.value)} className={inputCls + ' min-h-[96px] sm:col-span-2'} placeholder='{"x-api-version":"2026-08"}' />
          <textarea value={defaultQueryStr} onChange={(e) => setDefaultQueryStr(e.target.value)} className={inputCls + ' min-h-[96px] sm:col-span-2'} placeholder='{"region":"us"}' />
          <div className="sm:col-span-2">
            <button type="submit" disabled={creating} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
              {creating ? 'Creating...' : 'Add endpoint'}
            </button>
          </div>
        </form>
      )}

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
          No pass-through endpoints configured yet.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 p-4">
              {(() => {
                const itemStats = stats[item.id]
                const testResult = testResults[item.id]
                return (
              <>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm dark:text-slate-100">{item.slug}</span>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">{item.path_prefix}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${item.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'}`}>
                      {item.is_active ? 'active' : 'inactive'}
                    </span>
                  </div>
                  <p className="mt-1 text-xs font-mono text-slate-500 dark:text-slate-400 break-all">{item.upstream_base_url}</p>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500 dark:text-slate-400">
                    <span>auth {item.auth_type ?? 'none'}</span>
                    <span>timeout {item.timeout_ms}ms</span>
                    <span>rpm {item.rate_limit_rpm ?? 'unlimited'}</span>
                    <span>cost {item.cost_per_call_usd ? `$${item.cost_per_call_usd}` : 'unset'}</span>
                  </div>
                  {itemStats && (
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4">
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">Requests</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">{itemStats.total_requests}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">P95</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">{itemStats.p95_latency_ms ? `${parseFloat(itemStats.p95_latency_ms).toFixed(0)}ms` : '—'}</p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">Rate use</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">
                          {itemStats.rate_limit_utilization_pct ? `${(parseFloat(itemStats.rate_limit_utilization_pct) * 100).toFixed(1)}%` : '—'}
                        </p>
                      </div>
                      <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                        <p className="text-slate-400">24h cost</p>
                        <p className="font-semibold text-slate-700 dark:text-slate-100">
                          {itemStats.estimated_24h_cost_usd ? `$${parseFloat(itemStats.estimated_24h_cost_usd).toFixed(4)}` : '—'}
                        </p>
                      </div>
                    </div>
                  )}
                  {testResult && (
                    <div className={`mt-3 rounded-lg px-3 py-2 text-xs ${testResult.ok ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300'}`}>
                      <p className="font-medium">Last test: {testResult.status_code} in {testResult.latency_ms}ms</p>
                      <p className="mt-1 break-all">{testResult.target_url}</p>
                    </div>
                  )}
                </div>
                {canManage && (
                  <div className="flex shrink-0 gap-2">
                    <button onClick={() => void handleTest(item)} className="rounded-lg border border-indigo-200 px-3 py-1.5 text-xs text-indigo-700 hover:bg-indigo-50 dark:border-indigo-900/40 dark:text-indigo-300 dark:hover:bg-indigo-950/30">
                      {testingId === item.id ? 'Testing...' : 'Test'}
                    </button>
                    <button onClick={() => beginEdit(item)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                      Edit
                    </button>
                    <button onClick={() => void handleToggle(item)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                      {item.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button onClick={() => void handleDelete(item.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30">
                      Delete
                    </button>
                  </div>
                )}
              </div>
              {editState?.id === item.id && (
                <div className="mt-4 grid gap-3 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/40 dark:bg-indigo-900/10 p-4 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-300">Edit pass-through endpoint</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Tune upstream pathing, auth, timeout, headers, query defaults, and cost metadata without recreating the endpoint.</p>
                  </div>
                  <input value={editState.pathPrefix} onChange={(e) => setEditState({ ...editState, pathPrefix: e.target.value })} className={inputCls} placeholder="/v1" />
                  <input value={editState.upstreamBaseUrl} onChange={(e) => setEditState({ ...editState, upstreamBaseUrl: e.target.value })} className={inputCls} placeholder="https://upstream.example.com" />
                  <input value={editState.authType} onChange={(e) => setEditState({ ...editState, authType: e.target.value })} className={inputCls} placeholder="bearer | api_key | none" />
                  <input value={editState.timeoutMs} onChange={(e) => setEditState({ ...editState, timeoutMs: e.target.value })} className={inputCls} placeholder="30000" />
                  <input value={editState.rateLimitRpm} onChange={(e) => setEditState({ ...editState, rateLimitRpm: e.target.value })} className={inputCls} placeholder="Rate limit RPM" />
                  <input value={editState.costPerCallUsd} onChange={(e) => setEditState({ ...editState, costPerCallUsd: e.target.value })} className={inputCls} placeholder="Cost per call USD" />
                  <textarea value={editState.authConfigStr} onChange={(e) => { setEditState({ ...editState, authConfigStr: e.target.value }); setEditError('') }} className={`${inputCls} min-h-[96px] font-mono text-xs sm:col-span-2`} placeholder='{"token":"secret"}' />
                  <textarea value={editState.headerConfigStr} onChange={(e) => { setEditState({ ...editState, headerConfigStr: e.target.value }); setEditError('') }} className={`${inputCls} min-h-[96px] font-mono text-xs sm:col-span-2`} placeholder='{"x-api-version":"2026-08"}' />
                  <textarea value={editState.defaultQueryStr} onChange={(e) => { setEditState({ ...editState, defaultQueryStr: e.target.value }); setEditError('') }} className={`${inputCls} min-h-[96px] font-mono text-xs sm:col-span-2`} placeholder='{"region":"us"}' />
                  <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 sm:col-span-2">
                    <input type="checkbox" checked={editState.isActive} onChange={(e) => setEditState({ ...editState, isActive: e.target.checked })} className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500" />
                    Endpoint active
                  </label>
                  {editError && <p className="text-xs text-red-500 sm:col-span-2">{editError}</p>}
                  <div className="sm:col-span-2 flex items-center gap-2">
                    <button onClick={() => void handleSaveEdit()} disabled={savingEdit} className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                      {savingEdit ? 'Saving...' : 'Save changes'}
                    </button>
                    <button onClick={() => setEditState(null)} className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700">
                      Cancel
                    </button>
                  </div>
                </div>
              )}
              </>
                )
              })()}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
