'use client'

import { useSession } from 'next-auth/react'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { MessageSquare, Search, X, SlidersHorizontal, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { listSessions } from '@/lib/api'
import type { SessionItem } from '@/types/api'
import { formatCost, formatDuration } from '@/lib/utils'

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

function ResultCount({ filtered, total }: { filtered: number; total: number }) {
  if (filtered === total)
    return <span className="text-xs text-slate-400">{total} session{total !== 1 ? 's' : ''}</span>
  return (
    <span className="text-xs font-medium text-violet-600 dark:text-violet-400">
      {filtered} of {total} sessions
    </span>
  )
}

function SkeletonRows({ cols }: { cols: number }) {
  return (
    <>
      {[0, 1, 2, 3, 4].map((i) => (
        <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SessionsPage() {
  const { data: authSession } = useSession()
  const router = useRouter()

  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  // Filters
  const [timePreset, setTimePreset] = useState<TimePreset>('all')
  const [userFilter, setUserFilter] = useState('')
  const [minTurns, setMinTurns] = useState('')
  const [minCost, setMinCost] = useState('')
  const [maxCost, setMaxCost] = useState('')

  // Search (applied on top of filters)
  const [search, setSearch] = useState('')

  const load = useCallback(async (isRefresh = false) => {
    if (!authSession?.apiKey) return
    isRefresh ? setRefreshing(true) : setLoading(true)
    try {
      const data = await listSessions(authSession.apiKey, { limit: 200 })
      setSessions(data.items)
    } catch {
      toast.error('Failed to load sessions')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [authSession?.apiKey])

  useEffect(() => { load() }, [load])

  // ── Step 1: filters ──────────────────────────────────────────────────────

  const afterFilters = useMemo(() => {
    let rows = sessions
    const since = cutoff(timePreset)
    if (since) rows = rows.filter((s) => new Date(s.started_at) >= since)
    if (userFilter.trim()) {
      const u = userFilter.toLowerCase()
      rows = rows.filter((s) => (s.end_user_id ?? '').toLowerCase().includes(u))
    }
    if (minTurns !== '') {
      const n = parseInt(minTurns, 10)
      if (!isNaN(n)) rows = rows.filter((s) => s.run_count >= n)
    }
    if (minCost !== '') {
      const n = parseFloat(minCost)
      if (!isNaN(n)) rows = rows.filter((s) => parseFloat(s.total_cost_usd ?? '0') >= n)
    }
    if (maxCost !== '') {
      const n = parseFloat(maxCost)
      if (!isNaN(n)) rows = rows.filter((s) => parseFloat(s.total_cost_usd ?? '0') <= n)
    }
    return rows
  }, [sessions, timePreset, userFilter, minTurns, minCost, maxCost])

  // ── Step 2: search on top ────────────────────────────────────────────────

  const filtered = useMemo(() => {
    if (!search.trim()) return afterFilters
    const q = search.toLowerCase()
    return afterFilters.filter(
      (s) =>
        s.session_id.toLowerCase().includes(q) ||
        (s.end_user_id ?? '').toLowerCase().includes(q)
    )
  }, [afterFilters, search])

  const hasFilters = timePreset !== 'all' || userFilter.trim() || minTurns || minCost || maxCost
  const hasSearch = !!search.trim()

  function clearFilters() {
    setTimePreset('all')
    setUserFilter('')
    setMinTurns('')
    setMinCost('')
    setMaxCost('')
  }

  function clearAll() {
    clearFilters()
    setSearch('')
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Sessions</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Multi-turn conversations grouped by session_id.
          </p>
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

      {/* Filter panel */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 px-4 py-3 space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
        </div>

        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {/* Time range */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Time range</span>
            <TimeToggle value={timePreset} onChange={setTimePreset} />
          </div>

          {/* End user */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">End user</span>
            <div className="relative">
              <input
                value={userFilter}
                onChange={(e) => setUserFilter(e.target.value)}
                placeholder="user ID…"
                className={`${inputCls} w-44`}
              />
              {userFilter && (
                <button onClick={() => setUserFilter('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Min turns */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Min turns</span>
            <input
              type="number"
              min={1}
              value={minTurns}
              onChange={(e) => setMinTurns(e.target.value)}
              placeholder="e.g. 3"
              className={`${inputCls} w-24`}
            />
          </div>

          {/* Cost range */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400 w-20 shrink-0">Cost ($)</span>
            <input
              type="number"
              min={0}
              step={0.0001}
              value={minCost}
              onChange={(e) => setMinCost(e.target.value)}
              placeholder="min"
              className={`${inputCls} w-24`}
            />
            <span className="text-xs text-slate-400">–</span>
            <input
              type="number"
              min={0}
              step={0.0001}
              value={maxCost}
              onChange={(e) => setMaxCost(e.target.value)}
              placeholder="max"
              className={`${inputCls} w-24`}
            />
          </div>
        </div>

        {hasFilters && (
          <div className="flex items-center pt-1">
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-white"
            >
              <X className="h-3.5 w-3.5" /> Clear filters
            </button>
            <span className="ml-3 text-xs text-slate-400">
              {afterFilters.length} of {sessions.length} sessions match
            </span>
          </div>
        )}
      </div>

      {/* Search bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search within ${afterFilters.length} filtered sessions by ID or user…`}
            className={`${inputCls} pl-8 w-full`}
          />
          {hasSearch && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <ResultCount filtered={filtered.length} total={sessions.length} />
        {(hasFilters || hasSearch) && (
          <button
            onClick={clearAll}
            className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 whitespace-nowrap"
          >
            Reset all
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60">
            <tr>
              {['Session ID', 'User', 'Turns', 'Total Cost', 'Duration', 'Avg Score', 'Started'].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? (
              <SkeletonRows cols={7} />
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-16 text-center">
                  <MessageSquare className="mx-auto h-10 w-10 text-slate-300 dark:text-slate-600" />
                  <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
                    {sessions.length === 0
                      ? <>No sessions yet. Tag runs with a <code className="font-mono">session_id</code> to group them here.</>
                      : hasSearch
                      ? 'No sessions match your search.'
                      : 'No sessions match your filters.'}
                  </p>
                  {(hasFilters || hasSearch) && (
                    <button onClick={clearAll} className="mt-2 text-xs text-violet-600 hover:underline">
                      Reset all filters
                    </button>
                  )}
                </td>
              </tr>
            ) : (
              filtered.map((s) => {
                const durationMs =
                  s.started_at && s.ended_at
                    ? new Date(s.ended_at).getTime() - new Date(s.started_at).getTime()
                    : null

                return (
                  <tr
                    key={s.session_id}
                    onClick={() => router.push(`/sessions/${encodeURIComponent(s.session_id)}`)}
                    className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">
                      <span title={s.session_id}>
                        {s.session_id.length > 16 ? s.session_id.slice(0, 16) + '…' : s.session_id}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                      {s.end_user_id ? (
                        <span className="rounded-full bg-indigo-50 dark:bg-indigo-950 px-2 py-0.5 text-xs font-mono text-indigo-700 dark:text-indigo-300">
                          {s.end_user_id}
                        </span>
                      ) : (
                        <span className="text-slate-400 dark:text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                      <span className="tabular-nums">{s.run_count}</span>
                      <span className="ml-1 text-xs text-slate-400">turn{s.run_count !== 1 ? 's' : ''}</span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">
                      {formatCost(s.total_cost_usd)}
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                      {durationMs != null ? formatDuration(durationMs) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {s.avg_score != null ? (
                        <span className="inline-flex items-center rounded-full bg-indigo-50 dark:bg-indigo-950 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:text-indigo-300">
                          {parseFloat(s.avg_score).toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-slate-400 dark:text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs whitespace-nowrap">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
