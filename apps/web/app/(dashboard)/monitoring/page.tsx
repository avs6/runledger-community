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

// ── Helpers ───────────────────────────────────────────────────────────────────

const inputCls =
  'rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500'

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
    { v: 'all', label: 'All time' },
    { v: '1d', label: 'Today' },
    { v: '7d', label: '7 days' },
    { v: '30d', label: '30 days' },
  ]
  return (
    <div className="flex rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden text-sm shrink-0">
      {opts.map(({ v, label }) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={`px-3 py-1.5 transition-colors ${
            value === v
              ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 font-medium'
              : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
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
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-3 space-y-3">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
      </div>
      {children}
    </div>
  )
}

// ── Badges / helpers ──────────────────────────────────────────────────────────

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
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {icon} {severity}
    </span>
  )
}

function StatusDot({ status }: { status: string }) {
  const map: Record<string, string> = {
    success: 'bg-emerald-500',
    cache_hit: 'bg-blue-500',
    error: 'bg-red-500',
  }
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${map[status] ?? 'bg-slate-400'}`} />
      <span className={`text-xs font-medium ${
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
            <td key={j} className="px-4 py-3">
              <div className="h-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function ResultCount({ filtered, total }: { filtered: number; total: number }) {
  if (filtered === total) return <span className="text-xs text-slate-400">{total} items</span>
  return <span className="text-xs font-medium text-violet-600 dark:text-violet-400">{filtered} of {total} shown</span>
}

const TABLE_HEAD = 'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400'

// ── Security Events tab ───────────────────────────────────────────────────────

function SecurityEventsTab({ events, loading }: { events: SecurityEventResponse[]; loading: boolean }) {
  const [timePreset, setTimePreset] = useState<TimePreset>('all')
  const [typeFilter, setTypeFilter] = useState('')
  const [search, setSearch] = useState('')

  const eventTypes = useMemo(
    () => Array.from(new Set(events.map((e) => e.event_type))).sort(),
    [events]
  )

  // Step 1: apply hard filters
  const afterFilters = useMemo(() => {
    let rows = events
    const since = cutoff(timePreset)
    if (since) rows = rows.filter((e) => new Date(e.detected_at) >= since)
    if (typeFilter) rows = rows.filter((e) => e.event_type === typeFilter)
    return rows
  }, [events, timePreset, typeFilter])

  // Step 2: apply search on top of filtered
  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (e) =>
        e.event_type.toLowerCase().includes(q) ||
        (e.tool_name ?? '').toLowerCase().includes(q) ||
        JSON.stringify(e.details ?? {}).toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  const hasFilters = timePreset !== 'all' || typeFilter
  const hasSearch = !!search.trim()

  function clearAll() { setTimePreset('all'); setTypeFilter(''); setSearch('') }

  return (
    <div className="space-y-3">
      {/* Filter panel */}
      <FilterBar>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Time range</span>
            <TimeToggle value={timePreset} onChange={setTimePreset} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Event type</span>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className={inputCls}>
              <option value="">All types</option>
              {eventTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          {hasFilters && (
            <button onClick={() => { setTimePreset('all'); setTypeFilter('') }}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white ml-auto">
              <X className="h-3.5 w-3.5" /> Clear filters
            </button>
          )}
        </div>
      </FilterBar>

      {/* Search on filtered results */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search within ${afterFilters.length} filtered events…`}
            className={`${inputCls} pl-8 w-full`}
          />
          {hasSearch && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <ResultCount filtered={filtered.length} total={events.length} />
        {(hasFilters || hasSearch) && (
          <button onClick={clearAll} className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 whitespace-nowrap">
            Reset all
          </button>
        )}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className={TABLE_HEAD}>Time</th>
              <th className={TABLE_HEAD}>Event Type</th>
              <th className={TABLE_HEAD}>Tool / Source</th>
              <th className={TABLE_HEAD}>Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center">
                  <CheckCircle className="mx-auto mb-2 h-8 w-8 text-emerald-400" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {events.length === 0 ? 'No security events — system is clean.' :
                     hasSearch ? 'No events match your search.' : 'No events match your filters.'}
                  </p>
                </td>
              </tr>
            ) : filtered.map((ev) => (
              <tr key={ev.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                  {new Date(ev.detected_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">{ev.event_type}</td>
                <td className="px-4 py-3">
                  <span className="rounded bg-orange-100 px-2 py-0.5 text-xs text-orange-700 dark:bg-orange-900/40 dark:text-orange-300">
                    {ev.tool_name ?? 'system'}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400 max-w-sm truncate" title={JSON.stringify(ev.details)}>
                  {ev.details ? JSON.stringify(ev.details) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Alert Firings tab ─────────────────────────────────────────────────────────

function AlertsTab({ alerts, loading }: { alerts: AlertFiring[]; loading: boolean }) {
  const [timePreset, setTimePreset] = useState<TimePreset>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'resolved'>('all')
  const [ruleFilter, setRuleFilter] = useState('')
  const [search, setSearch] = useState('')

  const ruleNames = useMemo(
    () => Array.from(new Set(alerts.map((a) => a.rule_name).filter(Boolean))).sort() as string[],
    [alerts]
  )

  // Step 1: apply hard filters
  const afterFilters = useMemo(() => {
    let rows = alerts
    const since = cutoff(timePreset)
    if (since) rows = rows.filter((a) => new Date(a.fired_at) >= since)
    if (statusFilter === 'active') rows = rows.filter((a) => !a.resolved_at)
    if (statusFilter === 'resolved') rows = rows.filter((a) => !!a.resolved_at)
    if (ruleFilter) rows = rows.filter((a) => a.rule_name === ruleFilter)
    return rows
  }, [alerts, timePreset, statusFilter, ruleFilter])

  // Step 2: search on top
  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (a) =>
        (a.rule_name ?? '').toLowerCase().includes(q) ||
        (a.rule_id ?? '').toLowerCase().includes(q) ||
        String(a.metric_value ?? '').toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  const hasFilters = timePreset !== 'all' || statusFilter !== 'all' || ruleFilter
  const hasSearch = !!search.trim()

  function clearFilters() { setTimePreset('all'); setStatusFilter('all'); setRuleFilter('') }
  function clearAll() { clearFilters(); setSearch('') }

  return (
    <div className="space-y-3">
      {/* Filter panel */}
      <FilterBar>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Time range</span>
            <TimeToggle value={timePreset} onChange={setTimePreset} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Status</span>
            <div className="flex rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden text-sm">
              {(['all', 'active', 'resolved'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1.5 capitalize transition-colors ${
                    statusFilter === s
                      ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 font-medium'
                      : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Rule</span>
            <select value={ruleFilter} onChange={(e) => setRuleFilter(e.target.value)} className={inputCls}>
              <option value="">All rules</option>
              {ruleNames.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          {hasFilters && (
            <button onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white ml-auto">
              <X className="h-3.5 w-3.5" /> Clear filters
            </button>
          )}
        </div>
      </FilterBar>

      {/* Search on filtered results */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search within ${afterFilters.length} filtered alerts…`}
            className={`${inputCls} pl-8 w-full`}
          />
          {hasSearch && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <ResultCount filtered={filtered.length} total={alerts.length} />
        {(hasFilters || hasSearch) && (
          <button onClick={clearAll} className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 whitespace-nowrap">
            Reset all
          </button>
        )}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className={TABLE_HEAD}>Time</th>
              <th className={TABLE_HEAD}>Rule</th>
              <th className={TABLE_HEAD}>Metric / Value</th>
              <th className={TABLE_HEAD}>Resolved</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={4} /> :
             filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center">
                  <CheckCircle className="mx-auto mb-2 h-8 w-8 text-emerald-400" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {alerts.length === 0 ? 'No alert firings — all rules are healthy.' :
                     hasSearch ? 'No alerts match your search.' : 'No alerts match your filters.'}
                  </p>
                </td>
              </tr>
            ) : filtered.map((a) => (
              <tr key={a.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                  {new Date(a.fired_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-slate-200">
                  {a.rule_name ?? <span className="text-slate-400 font-mono text-xs">{a.rule_id?.slice(0, 8)}</span>}
                </td>
                <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                  {a.metric_value !== undefined ? (
                    <span className="font-mono text-orange-600 dark:text-orange-400">{String(a.metric_value)}</span>
                  ) : '—'}
                </td>
                <td className="px-4 py-3">
                  {a.resolved_at ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                      <CheckCircle className="h-3 w-3" /> resolved
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 dark:bg-red-950 px-2 py-0.5 text-xs font-medium text-red-700 dark:text-red-300">
                      <AlertTriangle className="h-3 w-3" /> active
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Gateway routing log tab ───────────────────────────────────────────────────

function GatewayTab({ requests, loading }: { requests: GatewayRequestLog[]; loading: boolean }) {
  const [timePreset, setTimePreset] = useState<TimePreset>('all')
  const [statusFilter, setStatusFilter] = useState('')
  const [modelFilter, setModelFilter] = useState('')
  const [search, setSearch] = useState('')

  const statuses = useMemo(
    () => Array.from(new Set(requests.map((r) => r.status))).sort(),
    [requests]
  )
  const models = useMemo(
    () => Array.from(new Set(requests.map((r) => r.model_requested).filter(Boolean))).sort() as string[],
    [requests]
  )

  // Step 1: apply hard filters
  const afterFilters = useMemo(() => {
    let rows = requests
    const since = cutoff(timePreset)
    if (since) rows = rows.filter((r) => new Date(r.created_at) >= since)
    if (statusFilter) rows = rows.filter((r) => r.status === statusFilter)
    if (modelFilter) rows = rows.filter((r) => r.model_requested === modelFilter)
    return rows
  }, [requests, timePreset, statusFilter, modelFilter])

  // Step 2: search on top
  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (r) =>
        (r.model_requested ?? '').toLowerCase().includes(q) ||
        (r.model_used ?? '').toLowerCase().includes(q) ||
        (r.decision_reason ?? '').toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  const hasFilters = timePreset !== 'all' || statusFilter || modelFilter
  const hasSearch = !!search.trim()

  function clearFilters() { setTimePreset('all'); setStatusFilter(''); setModelFilter('') }
  function clearAll() { clearFilters(); setSearch('') }

  return (
    <div className="space-y-3">
      {/* Filter panel */}
      <FilterBar>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Time range</span>
            <TimeToggle value={timePreset} onChange={setTimePreset} />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Status</span>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className={inputCls}>
              <option value="">All statuses</option>
              {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Model</span>
            <select value={modelFilter} onChange={(e) => setModelFilter(e.target.value)} className={inputCls}>
              <option value="">All models</option>
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          {hasFilters && (
            <button onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white ml-auto">
              <X className="h-3.5 w-3.5" /> Clear filters
            </button>
          )}
        </div>
      </FilterBar>

      {/* Search on filtered results */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search within ${afterFilters.length} filtered requests…`}
            className={`${inputCls} pl-8 w-full`}
          />
          {hasSearch && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <ResultCount filtered={filtered.length} total={requests.length} />
        {(hasFilters || hasSearch) && (
          <button onClick={clearAll} className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 whitespace-nowrap">
            Reset all
          </button>
        )}
      </div>

      <div className="overflow-x-auto overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
              <th className={TABLE_HEAD}>Time</th>
              <th className={TABLE_HEAD}>Alias / Model</th>
              <th className={TABLE_HEAD}>Model Used</th>
              <th className={TABLE_HEAD}>Latency</th>
              <th className={TABLE_HEAD}>Status</th>
              <th className={TABLE_HEAD}>Decision Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? <SkeletonRows cols={6} /> :
             filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center">
                  <Network className="mx-auto mb-2 h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {requests.length === 0
                      ? 'No gateway requests yet. Route traffic through the Model Gateway to see logs here.'
                      : hasSearch ? 'No requests match your search.' : 'No requests match your filters.'}
                  </p>
                </td>
              </tr>
            ) : filtered.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                  {new Date(r.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">{r.model_requested}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500 dark:text-slate-400">{r.model_used ?? '—'}</td>
                <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-300">
                  {r.latency_ms != null ? `${r.latency_ms}ms` : '—'}
                </td>
                <td className="px-4 py-3"><StatusDot status={r.status} /></td>
                <td className="px-4 py-3 font-mono text-xs text-indigo-600 dark:text-indigo-400 max-w-xs truncate" title={r.decision_reason ?? ''}>
                  {r.decision_reason ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

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
    { id: 'events', label: 'Security Events', icon: <Shield className="h-4 w-4" />, badge: securityEvents.length },
    { id: 'alerts', label: 'Alert Firings', icon: <Bell className="h-4 w-4" />, badge: activeAlerts },
    { id: 'gateway', label: 'Gateway Log', icon: <Network className="h-4 w-4" />, badge: gatewayErrors },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Monitoring</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Security events, alert firings, gateway routing decisions, and telemetry ingest health across your workspace.
          </p>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            OTLP traces, metrics, logs, and batch drill-in now live in{' '}
            <Link href="/monitoring/telemetry" className="font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300">
              Telemetry
            </Link>
            .
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link href="/security" className="rounded-full border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:border-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
              Open Security
            </Link>
            <Link href="/alert-rules" className="rounded-full border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:border-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
              Alert Rules
            </Link>
            <Link href="/gateway" className="rounded-full border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:border-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
              Gateway
            </Link>
            <Link href="/monitoring/telemetry" className="rounded-full border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:border-blue-300 hover:text-blue-700 dark:hover:text-blue-300">
              Telemetry
            </Link>
          </div>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {finopsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2 mb-3">
            <Wallet className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-base font-semibold text-emerald-900 dark:text-emerald-100">FinOps Monitoring Context</h2>
          </div>
          <p className="text-sm text-emerald-800/80 dark:text-emerald-300/70 mb-4">
            {finopsPosture.budget_context.active_budgets} active budget{finopsPosture.budget_context.active_budgets !== 1 ? 's' : ''} ·{' '}
            {finopsPosture.budget_context.breach_count} breach{finopsPosture.budget_context.breach_count !== 1 ? 'es' : ''} ·{' '}
            {finopsPosture.budget_context.active_overrides} active override{finopsPosture.budget_context.active_overrides !== 1 ? 's' : ''} ·{' '}
            {finopsPosture.notification_context.active_notifications} active notification{finopsPosture.notification_context.active_notifications !== 1 ? 's' : ''} ·{' '}
            {finopsPosture.ledger_context.ledger_snapshots} ledger snapshot{finopsPosture.ledger_context.ledger_snapshots !== 1 ? 's' : ''}
          </p>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 mb-4">
            {[
              { label: 'Budgets', value: `${finopsPosture.budget_context.active_budgets}/${finopsPosture.budget_context.budgets}` },
              { label: 'Overrides', value: `${finopsPosture.budget_context.active_overrides}/${finopsPosture.budget_context.overrides}` },
              { label: 'Notifications', value: `${finopsPosture.notification_context.active_notifications}/${finopsPosture.notification_context.notifications}` },
              { label: 'Billing Periods', value: `${finopsPosture.billing_context.open_billing_periods}/${finopsPosture.billing_context.billing_periods}` },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-600 dark:text-emerald-400">{label}</p>
                <p className="mt-1 text-lg font-semibold text-emerald-900 dark:text-emerald-100">{value}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { label: 'Budgets', href: '/budgets' },
              { label: 'Budget Detail', href: '/budgets' },
              { label: 'Budget Overrides', href: '/budgets?tab=overrides' },
              { label: 'Notifications', href: '/budgets?tab=notifications' },
              { label: 'Billing Periods', href: '/billing' },
              { label: 'Chargeback', href: '/chargeback' },
              { label: 'Ledger', href: '/ledger' },
            ].map(({ label, href }) => (
              <Link key={label} href={href} className="rounded-lg border border-emerald-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 dark:border-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 dark:hover:bg-emerald-800/50">
                {label}
              </Link>
            ))}
          </div>
        </div>
      )}

      {opsPosture && (
        <div className="space-y-4">
          {/* Gateway ops context */}
          <div className="rounded-2xl border border-violet-200 bg-violet-50/60 p-5 shadow-sm dark:border-violet-800 dark:bg-violet-950/30">
            <div className="flex items-center gap-2 mb-3">
              <Network className="h-5 w-5 text-violet-600 dark:text-violet-400" />
              <h2 className="text-base font-semibold text-violet-900 dark:text-violet-100">Gateway Ops Context</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 mb-4">
              {[
                { label: 'Providers', value: String(opsPosture.gateway_context.distinct_providers) },
                { label: 'Routes', value: String(opsPosture.gateway_context.active_routes) },
                { label: 'Guardrails', value: String(opsPosture.gateway_context.guardrail_rules) },
                { label: 'Guardrail Events 30d', value: String(opsPosture.gateway_context.guardrail_events_30d) },
                { label: 'Cache Configs', value: String(opsPosture.gateway_context.cache_configs) },
                { label: 'Rate Limit Routes', value: String(opsPosture.gateway_context.rate_limit_routes) },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-violet-600 dark:text-violet-400">{label}</p>
                  <p className="mt-1 text-lg font-semibold text-violet-900 dark:text-violet-100">{value}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { label: 'Provider Profiles', href: '/provider-profiles' },
                { label: 'Model Gateway', href: '/gateway' },
                { label: 'Guardrails', href: '/guardrails' },
                { label: 'Response Cache', href: '/cache' },
                { label: 'Rate Limits', href: '/rate-limits' },
              ].map(({ label, href }) => (
                <Link key={label} href={href} className="rounded-lg border border-violet-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-violet-700 hover:bg-violet-100 dark:border-violet-700 dark:bg-violet-900/40 dark:text-violet-300 dark:hover:bg-violet-800/50">
                  {label}
                </Link>
              ))}
            </div>
          </div>

          {/* Governance ops context */}
          <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5 shadow-sm dark:border-amber-800 dark:bg-amber-950/30">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              <h2 className="text-base font-semibold text-amber-900 dark:text-amber-100">Governance Ops Context</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 mb-4">
              {[
                { label: 'Tool Registry', value: String(opsPosture.governance_context.tool_registry) },
                { label: 'Tool Policies', value: String(opsPosture.governance_context.tool_policies) },
                { label: 'Capture Policies', value: String(opsPosture.governance_context.capture_policies) },
                { label: 'Audit Events 30d', value: String(opsPosture.governance_context.audit_events_30d) },
                { label: 'Approvals', value: String(opsPosture.governance_context.approvals) },
                { label: 'Tags', value: String(opsPosture.governance_context.tags) },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-600 dark:text-amber-400">{label}</p>
                  <p className="mt-1 text-lg font-semibold text-amber-900 dark:text-amber-100">{value}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { label: 'Tool Registry', href: '/tool-registry' },
                { label: 'Tool Policies', href: '/tool-policies' },
                { label: 'Approvals', href: '/approvals' },
                { label: 'Data Capture', href: '/data-capture' },
                { label: 'Audit Log', href: '/audit' },
                { label: 'Governance Pack', href: '/governance-pack' },
              ].map(({ label, href }) => (
                <Link key={label} href={href} className="rounded-lg border border-amber-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-100 dark:border-amber-700 dark:bg-amber-900/40 dark:text-amber-300 dark:hover:bg-amber-800/50">
                  {label}
                </Link>
              ))}
            </div>
          </div>

          {/* Org & investigation context */}
          <div className="rounded-2xl border border-blue-200 bg-blue-50/60 p-5 shadow-sm dark:border-blue-800 dark:bg-blue-950/30">
            <div className="flex items-center gap-2 mb-3">
              <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <h2 className="text-base font-semibold text-blue-900 dark:text-blue-100">Org & Investigation Context</h2>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5 mb-4">
              {[
                { label: 'Users', value: String(opsPosture.org_context.workspace_users) },
                { label: 'MCP Servers', value: `${opsPosture.org_context.active_mcp_servers}/${opsPosture.org_context.mcp_servers}` },
                { label: 'Runs 30d', value: String(opsPosture.investigation_context.runs_30d) },
                { label: 'Gateway Reqs 30d', value: String(opsPosture.investigation_context.gateway_requests_30d) },
              ].map(({ label, value }) => (
                <div key={label} className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-blue-600 dark:text-blue-400">{label}</p>
                  <p className="mt-1 text-lg font-semibold text-blue-900 dark:text-blue-100">{value}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { label: 'Organization', href: '/organization' },
                { label: 'Onboarding', href: '/onboarding' },
                { label: 'Workspaces', href: '/workspaces' },
                { label: 'API Keys', href: '/api-keys' },
                { label: 'MCP Registry', href: '/mcp-registry' },
                { label: 'Analytics Overview', href: '/analytics' },
                { label: 'Runs', href: '/runs' },
                { label: 'Request Flow', href: '/request-flow' },
                { label: 'Request Explorer', href: '/request-explorer' },
              ].map(({ label, href }) => (
                <Link key={label} href={href} className="rounded-lg border border-blue-200 bg-white/80 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-900/40 dark:text-blue-300 dark:hover:bg-blue-800/50">
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-3">
        {[
          {
            label: 'Security Events', value: securityEvents.length,
            color: securityEvents.length > 0 ? 'border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40' : 'border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/40',
            textColor: securityEvents.length > 0 ? 'text-red-700 dark:text-red-300' : 'text-emerald-700 dark:text-emerald-300',
          },
          {
            label: 'Active Alerts', value: activeAlerts,
            color: activeAlerts > 0 ? 'border-orange-200 dark:border-orange-900 bg-orange-50 dark:bg-orange-950/40' : 'border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/40',
            textColor: activeAlerts > 0 ? 'text-orange-700 dark:text-orange-300' : 'text-emerald-700 dark:text-emerald-300',
          },
          {
            label: 'Gateway Errors', value: gatewayErrors,
            color: gatewayErrors > 0 ? 'border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40' : 'border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/40',
            textColor: gatewayErrors > 0 ? 'text-red-700 dark:text-red-300' : 'text-emerald-700 dark:text-emerald-300',
          },
        ].map((s) => (
          <div key={s.label} className={`rounded-xl border ${s.color} px-4 py-3`}>
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{s.label}</p>
            <p className={`text-2xl font-bold ${s.textColor}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              tab === t.id
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {t.icon}
            {t.label}
            {!!t.badge && t.badge > 0 && (
              <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${
                tab === t.id ? 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
              }`}>
                {t.badge}
              </span>
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
