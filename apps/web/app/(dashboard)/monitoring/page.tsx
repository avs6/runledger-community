'use client'

import Link from 'next/link'
import { Suspense, useCallback, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Bell, Network, Shield } from 'lucide-react'
import { DataTable, type DataTableColumn, type DataTableQuery } from '@/components/ui/data-table'
import { PageHeader } from '@/components/ui/page-header'
import { TIME_RANGES, TimeRangePicker, rangeToWindow, type TimeRange } from '@/components/ui/time-range-picker'
import {
  listMonitoringAlerts,
  listMonitoringGatewayRequests,
  listMonitoringSecurityEvents,
} from '@/lib/api/observe'
import type { AlertFiring, GatewayRequestLog, SecurityEventResponse } from '@/types/api'

type Tab = 'events' | 'alerts' | 'gateway'
const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'events', label: 'Security', icon: <Shield className="h-3.5 w-3.5" aria-hidden /> },
  { id: 'alerts', label: 'Alerts', icon: <Bell className="h-3.5 w-3.5" aria-hidden /> },
  { id: 'gateway', label: 'Gateway', icon: <Network className="h-3.5 w-3.5" aria-hidden /> },
]

const selectCls =
  'h-8 rounded-lg border border-slate-200 bg-white px-2 text-xs text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'

function when(iso: string) {
  return new Date(iso).toLocaleString()
}

const eventColumns: DataTableColumn<SecurityEventResponse>[] = [
  { key: 'detected_at', header: 'Time', render: r => when(r.detected_at), value: r => r.detected_at },
  { key: 'event_type', header: 'Event type', render: r => <span className="font-mono">{r.event_type}</span> },
  { key: 'tool_name', header: 'Tool / source', value: r => r.tool_name ?? 'system' },
  { key: 'end_user_id', header: 'End user', value: r => r.end_user_id ?? '' },
  {
    key: 'run_id',
    header: 'Run',
    render: r => (r.run_id ? <Link className="font-mono text-blue-600 hover:underline dark:text-blue-400" href={`/runs/${r.run_id}`}>{r.run_id.slice(0, 8)}</Link> : '—'),
    value: r => r.run_id ?? '',
  },
  { key: 'details', header: 'Details', value: r => JSON.stringify(r.details ?? {}), className: 'max-w-[260px] truncate', defaultHidden: true },
]

const alertColumns: DataTableColumn<AlertFiring>[] = [
  { key: 'fired_at', header: 'Fired', render: r => when(r.fired_at), value: r => r.fired_at },
  { key: 'rule_name', header: 'Rule' },
  { key: 'metric_value', header: 'Metric value' },
  {
    key: 'resolved_at',
    header: 'State',
    render: r => (r.resolved_at ? <span className="text-status-success">Resolved</span> : <span className="text-status-error">Firing</span>),
    value: r => (r.resolved_at ? 'resolved' : 'firing'),
  },
]

const gatewayColumns: DataTableColumn<GatewayRequestLog>[] = [
  { key: 'created_at', header: 'Time', render: r => when(r.created_at), value: r => r.created_at },
  { key: 'model_requested', header: 'Requested', render: r => <span className="font-mono">{r.model_requested}</span> },
  { key: 'model_used', header: 'Used', render: r => <span className="font-mono">{r.model_used ?? '—'}</span>, value: r => r.model_used ?? '' },
  { key: 'status', header: 'Status', render: r => <span className={r.status === 'success' ? 'text-status-success' : 'text-status-error'}>{r.status}</span> },
  { key: 'cache_hit', header: 'Cache', value: r => (r.cache_hit ? 'hit' : 'miss') },
  { key: 'latency_ms', header: 'Latency', value: r => (r.latency_ms != null ? `${r.latency_ms} ms` : '') },
  { key: 'decision_reason', header: 'Why', value: r => r.decision_reason ?? '', className: 'max-w-[260px] truncate' },
]

/**
 * Monitoring: security events, alert firings and gateway requests. Time range, type
 * filters, search and paging are applied by the API (`/analytics/monitoring/*`), so a
 * 30-day range really covers 30 days (review O-18). All state lives in the URL.
 */
function MonitoringInner() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()

  const tab = (TABS.some(t => t.id === params.get('tab')) ? params.get('tab') : 'events') as Tab
  const rawRange = params.get('range')
  const range: TimeRange = (TIME_RANGES as readonly string[]).includes(rawRange ?? '') ? (rawRange as TimeRange) : '7d'
  const kind = params.get('kind') ?? ''

  const setParam = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(params.toString())
      for (const [k, v] of Object.entries(patch)) {
        if (!v) next.delete(k)
        else next.set(k, v)
      }
      // Changing a filter returns every table to its first page.
      for (const key of Array.from(next.keys())) if (key.endsWith('page')) next.delete(key)
      router.replace(`${pathname}?${next.toString()}`, { scroll: false })
    },
    [params, pathname, router],
  )

  const windowFor = useCallback((q: DataTableQuery) => ({ ...rangeToWindow(range), q: q.q || undefined, limit: q.limit, offset: q.offset }), [range])

  const fetchEvents = useMemo(
    () => (q: DataTableQuery) => listMonitoringSecurityEvents(apiKey, { ...windowFor(q), event_type: kind || undefined }),
    [apiKey, windowFor, kind],
  )
  const fetchAlerts = useMemo(
    () => (q: DataTableQuery) =>
      listMonitoringAlerts(apiKey, { ...windowFor(q), state: kind === 'firing' || kind === 'resolved' ? kind : undefined }),
    [apiKey, windowFor, kind],
  )
  const fetchGateway = useMemo(
    () => (q: DataTableQuery) => listMonitoringGatewayRequests(apiKey, { ...windowFor(q), status: kind || undefined }),
    [apiKey, windowFor, kind],
  )

  return (
    <div className="space-y-3">
      <PageHeader
        title="Monitoring"
        description="Security events, alert firings and gateway routing decisions over a time range."
        actions={
          <div className="flex flex-wrap gap-1.5">
            {[
              { href: '/security', label: 'Security' },
              { href: '/alert-rules', label: 'Alert rules' },
              { href: '/gateway', label: 'Gateway' },
              { href: '/monitoring/telemetry', label: 'Telemetry' },
            ].map(nav => (
              <Link key={nav.href} href={nav.href} className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {nav.label}
              </Link>
            ))}
          </div>
        }
      />

      <div role="tablist" aria-label="Monitoring feeds" className="flex gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-800/50">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setParam({ tab: t.id, kind: null })}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium ${
              tab === t.id ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <TimeRangePicker value={range} onChange={r => setParam({ range: r })} />
        {tab === 'events' && (
          <input
            aria-label="Event type"
            placeholder="Event type (exact)"
            defaultValue={kind}
            onKeyDown={e => { if (e.key === 'Enter') setParam({ kind: (e.target as HTMLInputElement).value.trim() || null }) }}
            className={selectCls}
          />
        )}
        {tab === 'alerts' && (
          <select aria-label="Alert state" value={kind} onChange={e => setParam({ kind: e.target.value || null })} className={selectCls}>
            <option value="">Any state</option>
            <option value="firing">Firing</option>
            <option value="resolved">Resolved</option>
          </select>
        )}
        {tab === 'gateway' && (
          <select aria-label="Request status" value={kind} onChange={e => setParam({ kind: e.target.value || null })} className={selectCls}>
            <option value="">Any status</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
          </select>
        )}
      </div>

      {!apiKey ? null : tab === 'events' ? (
        <DataTable
          key={`events-${range}-${kind}`}
          label="Security events"
          urlPrefix="ev_"
          columns={eventColumns}
          rowKey={r => r.id}
          fetchPage={fetchEvents}
          searchPlaceholder="Search type, tool or user…"
          emptyTitle="No security events in this range"
          csvFileName="security-events.csv"
        />
      ) : tab === 'alerts' ? (
        <DataTable
          key={`alerts-${range}-${kind}`}
          label="Alert firings"
          urlPrefix="al_"
          columns={alertColumns}
          rowKey={r => r.id}
          fetchPage={fetchAlerts}
          searchPlaceholder="Search rule name…"
          emptyTitle="No alerts fired in this range"
          emptyDescription="Alert firings need an org admin role."
          csvFileName="alert-firings.csv"
        />
      ) : (
        <DataTable
          key={`gateway-${range}-${kind}`}
          label="Gateway requests"
          urlPrefix="gw_"
          columns={gatewayColumns}
          rowKey={r => r.id}
          fetchPage={fetchGateway}
          searchPlaceholder="Search model…"
          emptyTitle="No gateway requests in this range"
          emptyDescription="Gateway requests need an org admin role."
          csvFileName="gateway-requests.csv"
        />
      )}
    </div>
  )
}

export default function MonitoringPage() {
  return (
    <Suspense fallback={null}>
      <MonitoringInner />
    </Suspense>
  )
}
