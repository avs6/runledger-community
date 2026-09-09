'use client'

import Link from 'next/link'
import { useEffect, useState, useCallback, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  Activity, Shield, Bell, Building2, Network, RefreshCw,
  AlertTriangle, CheckCircle, Info, XCircle, Search, X, SlidersHorizontal, Wallet,
} from 'lucide-react'
import { getSecurityEvents, listAlertHistory, listGatewayRequests, getMonitoringFinopsPosture, getMonitoringOpsPosture } from '@/lib/api'
import type { SecurityEventResponse, AlertFiring, GatewayRequestLog, MonitoringFinopsPosture, MonitoringOpsPosture } from '@/types/api'

type Tab = 'events' | 'alerts' | 'gateway'
type TimePreset = 'all' | '1d' | '7d' | '30d'
const PAGE_SIZE = 20

const inputCls =
  'rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 px-2.5 py-1 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500'

function cutoff(preset: TimePreset): Date | null {
  if (preset === 'all') return null
  const d = new Date()
  if (preset === '1d') d.setDate(d.getDate() - 1)
  if (preset === '7d') d.setDate(d.getDate() - 7)
  if (preset === '30d') d.setDate(d.getDate() - 30)
  return d
}

function TimeToggle({ value, onChange }: { value: TimePreset; onChange: (v: TimePreset) => void }) {
  const opts: { v: TimePreset; label: string }[] = [
    { v: 'all', label: 'All' },
    { v: '1d', label: '1d' },
    { v: '7d', label: '7d' },
    { v: '30d', label: '30d' },
  ]
  return (
    <div className="flex overflow-hidden rounded-lg border border-slate-200 text-[11px] dark:border-slate-700">
      {opts.map(({ v, label }) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={`px-2.5 py-1 transition-colors ${
            value === v
              ? 'bg-slate-800 font-medium text-white dark:bg-slate-200 dark:text-slate-900'
              : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

function FilterBar({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/50">
      <div className="flex flex-wrap items-center gap-2">
        <SlidersHorizontal className="h-3 w-3 text-slate-400" />
        {children}
      </div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { cls: string; icon: React.ReactNode }> = {
    critical: { cls: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300', icon: <XCircle className="h-3 w-3" /> },
    high: { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300', icon: <AlertTriangle className="h-3 w-3" /> },
    medium: { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300', icon: <AlertTriangle className="h-3 w-3" /> },
    low: { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300', icon: <Info className="h-3 w-3" /> },
    info: { cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300', icon: <Info className="h-3 w-3" /> },
  }
  const { cls, icon } = map[severity?.toLowerCase()] ?? map.info
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${cls}`}>
      {icon} {severity}
    </span>
  )
}

function StatusDot({ status }: { status: string }) {
  const map: Record<string, string> = { success: 'bg-emerald-500', cache_hit: 'bg-blue-500', error: 'bg-red-500' }
  return (
    <span className="flex items-center gap-1">
      <span className={`h-1.5 w-1.5 rounded-full ${map[status] ?? 'bg-slate-400'}`} />
      <span className={`text-[11px] font-medium ${
        status === 'success' ? 'text-emerald-700 dark:text-emerald-400' :
        status === 'cache_hit' ? 'text-blue-700 dark:text-blue-400' :
        'text-red-700 dark:text-red-400'
      }`}>{status}</span>
    </span>
  )
}

function SkeletonRows({ cols, rows = 5 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-3 py-1.5">
              <div className="h-3 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function ResultCount({ filtered, total }: { filtered: number; total: number }) {
  if (filtered === total) return <span className="text-[10px] text-slate-400">{total}</span>
  return <span className="text-[10px] font-medium text-violet-600 dark:text-violet-400">{filtered}/{total}</span>
}

const TH = 'px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-slate-400'

function Pagination({ page, totalPages, total, pageSize, onPageChange }: { page: number; totalPages: number; total: number; pageSize: number; onPageChange: (p: number) => void }) {
  if (totalPages <= 1) return null
  const from = page * pageSize + 1
  const to = Math.min((page + 1) * pageSize, total)
  return (
    <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-[10px] text-slate-400 dark:border-slate-700">
      <span>{from}–{to} of {total}</span>
      <div className="flex gap-1.5">
        <button type="button" disabled={page === 0} onClick={() => onPageChange(page - 1)}
          className="rounded border border-slate-300 px-2 py-0.5 font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300">Prev</button>
        <button type="button" disabled={page >= totalPages - 1} onClick={() => onPageChange(page + 1)}
          className="rounded border border-slate-300 px-2 py-0.5 font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300">Next</button>
      </div>
    </div>
  )
}

function SecurityEventsTab({ events, loading }: { events: SecurityEventResponse[]; loading: boolean }) {
  const [timePreset, setTimePreset] = useState<TimePreset>('all')
  const [typeFilter, setTypeFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)

  const eventTypes = useMemo(() => Array.from(new Set(events.map((e) => e.event_type))).sort(), [events])

  const afterFilters = useMemo(() => {
    let rows = events
    const since = cutoff(timePreset)
    if (since) rows = rows.filter((e) => new Date(e.detected_at) >= since)
    if (typeFilter) rows = rows.filter((e) => e.event_type === typeFilter)
    return rows
  }, [events, timePreset, typeFilter])

  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (e) => e.event_type.toLowerCase().includes(q) || (e.tool_name ?? '').toLowerCase().includes(q) || JSON.stringify(e.details ?? {}).toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  useEffect(() => { setPage(0) }, [timePreset, typeFilter, search])

  return (
    <div className="space-y-2">
      <FilterBar>
        <TimeToggle value={timePreset} onChange={setTimePreset} />
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className={inputCls}>
          <option value="">All types</option>
          {eventTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search…" className={`${inputCls} w-full pl-7`} />
        </div>
        <ResultCount filtered={filtered.length} total={events.length} />
        {(timePreset !== 'all' || typeFilter || search) && (
          <button onClick={() => { setTimePreset('all'); setTypeFilter(''); setSearch('') }} className="text-[10px] text-slate-400 hover:text-slate-600"><X className="h-3 w-3" /></button>
        )}
      </FilterBar>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/60">
              <th className={TH}>Time</th>
              <th className={TH}>Event Type</th>
              <th className={TH}>Tool / Source</th>
              <th className={TH}>Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             paged.length === 0 ? (
              <tr><td colSpan={4} className="px-3 py-8 text-center text-xs text-slate-400">
                {events.length === 0 ? 'No security events — system is clean.' : 'No events match your filters.'}
              </td></tr>
            ) : paged.map((ev) => (
              <tr key={ev.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">{new Date(ev.detected_at).toLocaleString()}</td>
                <td className="px-3 py-1.5 font-mono text-slate-700 dark:text-slate-300">{ev.event_type}</td>
                <td className="px-3 py-1.5">
                  <span className="rounded bg-orange-100 px-1.5 py-0.5 text-[10px] text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">{ev.tool_name ?? 'system'}</span>
                </td>
                <td className="max-w-[200px] truncate px-3 py-1.5 text-slate-500" title={JSON.stringify(ev.details)}>{ev.details ? JSON.stringify(ev.details) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} totalPages={totalPages} total={filtered.length} pageSize={PAGE_SIZE} onPageChange={setPage} />
      </div>
    </div>
  )
}

function AlertsTab({ alerts, loading }: { alerts: AlertFiring[]; loading: boolean }) {
  const [timePreset, setTimePreset] = useState<TimePreset>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'resolved'>('all')
  const [ruleFilter, setRuleFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)

  const ruleNames = useMemo(() => Array.from(new Set(alerts.map((a) => a.rule_name).filter(Boolean))).sort() as string[], [alerts])

  const afterFilters = useMemo(() => {
    let rows = alerts
    const since = cutoff(timePreset)
    if (since) rows = rows.filter((a) => new Date(a.fired_at) >= since)
    if (statusFilter === 'active') rows = rows.filter((a) => !a.resolved_at)
    if (statusFilter === 'resolved') rows = rows.filter((a) => !!a.resolved_at)
    if (ruleFilter) rows = rows.filter((a) => a.rule_name === ruleFilter)
    return rows
  }, [alerts, timePreset, statusFilter, ruleFilter])

  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (a) => (a.rule_name ?? '').toLowerCase().includes(q) || (a.rule_id ?? '').toLowerCase().includes(q) || String(a.metric_value ?? '').toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  useEffect(() => { setPage(0) }, [timePreset, statusFilter, ruleFilter, search])

  return (
    <div className="space-y-2">
      <FilterBar>
        <TimeToggle value={timePreset} onChange={setTimePreset} />
        <div className="flex overflow-hidden rounded-lg border border-slate-200 text-[11px] dark:border-slate-700">
          {(['all', 'active', 'resolved'] as const).map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-2.5 py-1 capitalize transition-colors ${statusFilter === s ? 'bg-slate-800 font-medium text-white dark:bg-slate-200 dark:text-slate-900' : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-400'}`}>
              {s}
            </button>
          ))}
        </div>
        <select value={ruleFilter} onChange={(e) => setRuleFilter(e.target.value)} className={inputCls}>
          <option value="">All rules</option>
          {ruleNames.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search…" className={`${inputCls} w-full pl-7`} />
        </div>
        <ResultCount filtered={filtered.length} total={alerts.length} />
        {(timePreset !== 'all' || statusFilter !== 'all' || ruleFilter || search) && (
          <button onClick={() => { setTimePreset('all'); setStatusFilter('all'); setRuleFilter(''); setSearch('') }} className="text-[10px] text-slate-400 hover:text-slate-600"><X className="h-3 w-3" /></button>
        )}
      </FilterBar>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/60">
              <th className={TH}>Time</th>
              <th className={TH}>Rule</th>
              <th className={TH}>Metric / Value</th>
              <th className={TH}>Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             paged.length === 0 ? (
              <tr><td colSpan={4} className="px-3 py-8 text-center text-xs text-slate-400">
                {alerts.length === 0 ? 'No alert firings — all rules healthy.' : 'No alerts match your filters.'}
              </td></tr>
            ) : paged.map((a) => (
              <tr key={a.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">{new Date(a.fired_at).toLocaleString()}</td>
                <td className="px-3 py-1.5 font-medium text-slate-800 dark:text-slate-200">
                  {a.rule_name ?? <span className="font-mono text-slate-400">{a.rule_id?.slice(0, 8)}</span>}
                </td>
                <td className="px-3 py-1.5">
                  {a.metric_value !== undefined ? <span className="font-mono text-orange-600 dark:text-orange-400">{String(a.metric_value)}</span> : '—'}
                </td>
                <td className="px-3 py-1.5">
                  {a.resolved_at ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                      <CheckCircle className="h-2.5 w-2.5" /> resolved
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700 dark:bg-red-950 dark:text-red-300">
                      <AlertTriangle className="h-2.5 w-2.5" /> active
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} totalPages={totalPages} total={filtered.length} pageSize={PAGE_SIZE} onPageChange={setPage} />
      </div>
    </div>
  )
}

function GatewayTab({ requests, loading }: { requests: GatewayRequestLog[]; loading: boolean }) {
  const [timePreset, setTimePreset] = useState<TimePreset>('all')
  const [statusFilter, setStatusFilter] = useState('')
  const [modelFilter, setModelFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)

  const statuses = useMemo(() => Array.from(new Set(requests.map((r) => r.status))).sort(), [requests])
  const models = useMemo(() => Array.from(new Set(requests.map((r) => r.model_requested).filter(Boolean))).sort() as string[], [requests])

  const afterFilters = useMemo(() => {
    let rows = requests
    const since = cutoff(timePreset)
    if (since) rows = rows.filter((r) => new Date(r.created_at) >= since)
    if (statusFilter) rows = rows.filter((r) => r.status === statusFilter)
    if (modelFilter) rows = rows.filter((r) => r.model_requested === modelFilter)
    return rows
  }, [requests, timePreset, statusFilter, modelFilter])

  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (r) => (r.model_requested ?? '').toLowerCase().includes(q) || (r.model_used ?? '').toLowerCase().includes(q) || (r.decision_reason ?? '').toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  useEffect(() => { setPage(0) }, [timePreset, statusFilter, modelFilter, search])

  return (
    <div className="space-y-2">
      <FilterBar>
        <TimeToggle value={timePreset} onChange={setTimePreset} />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className={inputCls}>
          <option value="">All statuses</option>
          {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={modelFilter} onChange={(e) => setModelFilter(e.target.value)} className={inputCls}>
          <option value="">All models</option>
          {models.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search…" className={`${inputCls} w-full pl-7`} />
        </div>
        <ResultCount filtered={filtered.length} total={requests.length} />
        {(timePreset !== 'all' || statusFilter || modelFilter || search) && (
          <button onClick={() => { setTimePreset('all'); setStatusFilter(''); setModelFilter(''); setSearch('') }} className="text-[10px] text-slate-400 hover:text-slate-600"><X className="h-3 w-3" /></button>
        )}
      </FilterBar>

      <div className="overflow-x-auto overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/60">
              <th className={TH}>Time</th>
              <th className={TH}>Alias / Model</th>
              <th className={TH}>Model Used</th>
              <th className={TH}>Latency</th>
              <th className={TH}>Status</th>
              <th className={TH}>Decision</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={6} /> :
             paged.length === 0 ? (
              <tr><td colSpan={6} className="px-3 py-8 text-center text-xs text-slate-400">
                {requests.length === 0 ? 'No gateway requests yet.' : 'No requests match your filters.'}
              </td></tr>
            ) : paged.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">{new Date(r.created_at).toLocaleString()}</td>
                <td className="px-3 py-1.5 font-mono text-slate-700 dark:text-slate-300">{r.model_requested}</td>
                <td className="px-3 py-1.5 font-mono text-slate-500">{r.model_used ?? '—'}</td>
                <td className="px-3 py-1.5 text-slate-600 dark:text-slate-300">{r.latency_ms != null ? `${r.latency_ms}ms` : '—'}</td>
                <td className="px-3 py-1.5"><StatusDot status={r.status} /></td>
                <td className="max-w-[180px] truncate px-3 py-1.5 font-mono text-indigo-600 dark:text-indigo-400" title={r.decision_reason ?? ''}>{r.decision_reason ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={page} totalPages={totalPages} total={filtered.length} pageSize={PAGE_SIZE} onPageChange={setPage} />
      </div>
    </div>
  )
}

export default function MonitoringPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [tab, setTab] = useState<Tab>('events')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const [securityEvents, setSecurityEvents] = useState<SecurityEventResponse[]>([])
  const [alertFirings, setAlertFirings] = useState<AlertFiring[]>([])
  const [gatewayRequests, setGatewayRequests] = useState<GatewayRequestLog[]>([])
  const [finopsPosture, setFinopsPosture] = useState<MonitoringFinopsPosture | null>(null)
  const [opsPosture, setOpsPosture] = useState<MonitoringOpsPosture | null>(null)

  const load = useCallback(async (isRefresh = false) => {
    if (!apiKey) return
    isRefresh ? setRefreshing(true) : setLoading(true)
    try {
      const [evts, alerts, gw] = await Promise.all([
        getSecurityEvents(apiKey),
        listAlertHistory(apiKey, 100),
        listGatewayRequests(apiKey, { limit: 100 }),
      ])
      setSecurityEvents(evts.items.slice(0, 100))
      setAlertFirings(alerts.items)
      setGatewayRequests(gw.items)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load monitoring data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [apiKey])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!apiKey) return
    getMonitoringFinopsPosture(apiKey).then(setFinopsPosture).catch(() => {})
    getMonitoringOpsPosture(apiKey).then(setOpsPosture).catch(() => {})
  }, [apiKey])

  const activeAlerts = alertFirings.filter((a) => !a.resolved_at).length
  const gatewayErrors = gatewayRequests.filter((r) => r.status === 'error').length

  const tabs: { id: Tab; label: string; icon: React.ReactNode; badge?: number }[] = [
    { id: 'events', label: 'Security', icon: <Shield className="h-3.5 w-3.5" />, badge: securityEvents.length },
    { id: 'alerts', label: 'Alerts', icon: <Bell className="h-3.5 w-3.5" />, badge: activeAlerts },
    { id: 'gateway', label: 'Gateway', icon: <Network className="h-3.5 w-3.5" />, badge: gatewayErrors },
  ]

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-bold text-slate-950 dark:text-white">Monitoring</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">Security events, alerts, gateway routing, and ops health.</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { href: '/security', label: 'Security' },
            { href: '/alert-rules', label: 'Alert Rules' },
            { href: '/gateway', label: 'Gateway' },
            { href: '/monitoring/telemetry', label: 'Telemetry' },
          ].map(nav => (
            <Link key={nav.label} href={nav.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {nav.label}
            </Link>
          ))}
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <RefreshCw className={`h-3 w-3 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-3 gap-2">
        {[
          {
            label: 'Security Events', value: securityEvents.length,
            color: securityEvents.length > 0 ? 'border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30' : 'border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/30',
            textColor: securityEvents.length > 0 ? 'text-red-700 dark:text-red-300' : 'text-emerald-700 dark:text-emerald-300',
          },
          {
            label: 'Active Alerts', value: activeAlerts,
            color: activeAlerts > 0 ? 'border-orange-200 dark:border-orange-900 bg-orange-50 dark:bg-orange-950/30' : 'border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/30',
            textColor: activeAlerts > 0 ? 'text-orange-700 dark:text-orange-300' : 'text-emerald-700 dark:text-emerald-300',
          },
          {
            label: 'Gateway Errors', value: gatewayErrors,
            color: gatewayErrors > 0 ? 'border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30' : 'border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/30',
            textColor: gatewayErrors > 0 ? 'text-red-700 dark:text-red-300' : 'text-emerald-700 dark:text-emerald-300',
          },
        ].map((s) => (
          <div key={s.label} className={`rounded-xl border p-2.5 ${s.color}`}>
            <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{s.label}</p>
            <p className={`mt-0.5 text-lg font-bold ${s.textColor}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Posture chips */}
      {finopsPosture && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <Wallet className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">FinOps Context</span>
            </div>
            <div className="flex gap-1.5">
              {[{ href: '/budgets', l: 'Budgets' }, { href: '/billing', l: 'Billing' }, { href: '/chargeback', l: 'Chargeback' }, { href: '/ledger', l: 'Ledger' }].map(x => (
                <Link key={x.l} href={x.href} className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">{x.l}</Link>
              ))}
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {[
              { l: 'Budgets', v: `${finopsPosture.budget_context.active_budgets}/${finopsPosture.budget_context.budgets}` },
              { l: 'Breaches', v: `${finopsPosture.budget_context.breach_count}` },
              { l: 'Overrides', v: `${finopsPosture.budget_context.active_overrides}/${finopsPosture.budget_context.overrides}` },
              { l: 'Notifications', v: `${finopsPosture.notification_context.active_notifications}/${finopsPosture.notification_context.notifications}` },
              { l: 'Billing', v: `${finopsPosture.billing_context.open_billing_periods}/${finopsPosture.billing_context.billing_periods}` },
              { l: 'Snapshots', v: `${finopsPosture.ledger_context.ledger_snapshots}` },
            ].map(c => (
              <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {opsPosture && (
        <div className="grid gap-2 lg:grid-cols-3">
          {/* Gateway ops */}
          <div className="rounded-xl border border-violet-300 bg-violet-50 p-3 dark:border-violet-800/40 dark:bg-violet-950/20">
            <div className="mb-2 flex items-center gap-1.5">
              <Network className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
              <span className="text-xs font-semibold text-violet-700 dark:text-violet-300">Gateway Ops</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { l: 'Providers', v: opsPosture.gateway_context.distinct_providers },
                { l: 'Routes', v: opsPosture.gateway_context.active_routes },
                { l: 'Guardrails', v: opsPosture.gateway_context.guardrail_rules },
                { l: 'Events 30d', v: opsPosture.gateway_context.guardrail_events_30d },
                { l: 'Cache', v: opsPosture.gateway_context.cache_configs },
                { l: 'RPM', v: opsPosture.gateway_context.rate_limit_routes },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] dark:border-violet-800 dark:bg-violet-950/40">
                  <span className="font-medium text-violet-500 dark:text-violet-400">{c.l}</span>
                  <span className="font-bold text-violet-700 dark:text-violet-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Governance ops */}
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 dark:border-amber-800/40 dark:bg-amber-950/20">
            <div className="mb-2 flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
              <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">Governance Ops</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { l: 'Tools', v: opsPosture.governance_context.tool_registry },
                { l: 'Policies', v: opsPosture.governance_context.tool_policies },
                { l: 'Capture', v: opsPosture.governance_context.capture_policies },
                { l: 'Audit 30d', v: opsPosture.governance_context.audit_events_30d },
                { l: 'Approvals', v: opsPosture.governance_context.approvals },
                { l: 'Tags', v: opsPosture.governance_context.tags },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] dark:border-amber-800 dark:bg-amber-950/40">
                  <span className="font-medium text-amber-500 dark:text-amber-400">{c.l}</span>
                  <span className="font-bold text-amber-700 dark:text-amber-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Org & investigation */}
          <div className="rounded-xl border border-blue-300 bg-blue-50 p-3 dark:border-blue-800/40 dark:bg-blue-950/20">
            <div className="mb-2 flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Org & Investigation</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { l: 'Users', v: opsPosture.org_context.workspace_users },
                { l: 'MCP', v: `${opsPosture.org_context.active_mcp_servers}/${opsPosture.org_context.mcp_servers}` },
                { l: 'Runs 30d', v: opsPosture.investigation_context.runs_30d },
                { l: 'GW Reqs 30d', v: opsPosture.investigation_context.gateway_requests_30d },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] dark:border-blue-800 dark:bg-blue-950/40">
                  <span className="font-medium text-blue-500 dark:text-blue-400">{c.l}</span>
                  <span className="font-bold text-blue-700 dark:text-blue-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-800/50">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
              tab === t.id
                ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-white'
                : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
            }`}
          >
            {t.icon}
            {t.label}
            {!!t.badge && t.badge > 0 && (
              <span className={`rounded-full px-1.5 py-px text-[9px] font-semibold ${
                tab === t.id ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300' : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
              }`}>{t.badge}</span>
            )}
          </button>
        ))}
      </div>

      {tab === 'events' && <SecurityEventsTab events={securityEvents} loading={loading} />}
      {tab === 'alerts' && <AlertsTab alerts={alertFirings} loading={loading} />}
      {tab === 'gateway' && <GatewayTab requests={gatewayRequests} loading={loading} />}
    </div>
  )
}
