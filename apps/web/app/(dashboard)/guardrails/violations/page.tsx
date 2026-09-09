'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { ArrowLeft, ChevronLeft, ChevronRight, ShieldAlert, Search, X } from 'lucide-react'
import { listGuardrailEvents } from '@/lib/api'
import type { GuardrailEventResponse } from '@/types/api'
import { num } from '@/lib/utils'

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500'

const decisionColors: Record<string, string> = {
  allow: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  block: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  modify: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
}

type FalsePositiveFilter = 'all' | 'only' | 'exclude'

export default function GuardrailViolationsPage() {
  const { data: session } = useSession()
  const apiKey = (session as Record<string, unknown> | null)?.apiKey as string | undefined
  const workspaceName =
    (session as Record<string, unknown> | null)?.workspaceName as string | undefined

  const [items, setItems] = useState<GuardrailEventResponse[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const [query, setQuery] = useState('')
  const [decision, setDecision] = useState<'all' | 'block' | 'modify' | 'allow'>('all')
  const [mode, setMode] = useState<'all' | 'pre_call' | 'post_call' | 'during_call' | 'both'>('all')
  const [falsePositiveFilter, setFalsePositiveFilter] = useState<FalsePositiveFilter>('all')
  const [violationsOnly, setViolationsOnly] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize])

  useEffect(() => { setPage(1) }, [query, decision, mode, falsePositiveFilter, violationsOnly, pageSize])

  useEffect(() => {
    async function load() {
      if (!apiKey) return
      setLoading(true)
      try {
        const result = await listGuardrailEvents(apiKey, {
          guardrail_name: query.trim() || undefined,
          decision: decision === 'all' ? undefined : decision,
          mode: mode === 'all' ? undefined : mode,
          violations_only: violationsOnly,
          false_positive: falsePositiveFilter === 'all' ? undefined : falsePositiveFilter === 'only',
          limit: pageSize,
          offset: (page - 1) * pageSize,
        })
        setItems(result.items)
        setTotal(result.total)
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [apiKey, query, decision, mode, falsePositiveFilter, violationsOnly, page, pageSize])

  if (!apiKey) {
    return <div className="p-8 text-xs text-slate-500">Sign in to view guardrail violations.</div>
  }

  return (
    <div className="space-y-3">
      {/* ── Header ───────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-rose-500 to-red-600 shadow-lg shadow-rose-500/25">
            <ShieldAlert className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Link href="/guardrails" className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 flex items-center gap-1">
                <ArrowLeft className="h-3 w-3" /> Guardrails
              </Link>
            </div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Violations Log</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Enforcement history for {workspaceName ?? 'the current workspace'} — blocks, modifications, and outcomes.
            </p>
          </div>
        </div>
      </div>

      {/* ── KPI strip ────────────────────────────── */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'Total Events', value: total.toLocaleString() },
          { label: 'Page', value: `${page} / ${totalPages}` },
          { label: 'Blocks', value: items.filter((e) => e.decision === 'block').length },
          { label: 'Modifications', value: items.filter((e) => e.decision === 'modify').length },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
            <p className="text-sm font-bold text-slate-900 dark:text-white">{value}</p>
          </div>
        ))}
      </div>

      {/* ── Filters ──────────────────────────────── */}
      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-7">
          <div className="xl:col-span-2 relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-400" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search guardrail name…" className={`pl-7 ${inputCls}`} />
            {query && <button onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"><X className="h-3 w-3" /></button>}
          </div>
          <select value={decision} onChange={(e) => setDecision(e.target.value as typeof decision)} className={inputCls}>
            <option value="all">All decisions</option>
            <option value="block">Block</option>
            <option value="modify">Modify</option>
            <option value="allow">Allow</option>
          </select>
          <select value={mode} onChange={(e) => setMode(e.target.value as typeof mode)} className={inputCls}>
            <option value="all">All modes</option>
            <option value="pre_call">pre_call</option>
            <option value="post_call">post_call</option>
            <option value="during_call">during_call</option>
            <option value="both">both</option>
          </select>
          <select value={falsePositiveFilter} onChange={(e) => setFalsePositiveFilter(e.target.value as FalsePositiveFilter)} className={inputCls}>
            <option value="all">All FP status</option>
            <option value="only">Only false positives</option>
            <option value="exclude">Exclude false positives</option>
          </select>
          <select value={String(pageSize)} onChange={(e) => setPageSize(Number(e.target.value))} className={inputCls}>
            <option value="25">25/page</option>
            <option value="50">50/page</option>
            <option value="100">100/page</option>
          </select>
          <button
            onClick={() => setViolationsOnly((c) => !c)}
            className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition ${violationsOnly ? 'bg-rose-600 text-white hover:bg-rose-700' : 'border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
          >
            {violationsOnly ? 'Violations only' : 'All evaluations'}
          </button>
        </div>
      </div>

      {/* ── Table ─────────────────────────────────── */}
      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400">Loading violations log...</div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">No events matched the current filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700/40 bg-slate-50/80 dark:bg-slate-800/60">
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Guardrail</th>
                  <th className="px-3 py-1.5 text-center text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Decision</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Mode</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Model</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Latency</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider max-w-xs">Reason</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/60 dark:divide-slate-700/30">
                {items.map((event) => (
                  <tr key={event.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors align-top">
                    <td className="px-3 py-1.5">
                      <span className="font-medium text-slate-900 dark:text-slate-100">{event.guardrail_name}</span>
                      {event.is_false_positive && (
                        <span className="ml-1.5 rounded-full bg-violet-100 dark:bg-violet-900/30 px-1.5 py-0.5 text-[9px] font-semibold text-violet-700 dark:text-violet-300">FP</span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${decisionColors[event.decision] || decisionColors.allow}`}>{event.decision}</span>
                    </td>
                    <td className="px-3 py-1.5 text-slate-600 dark:text-slate-300">{event.mode}</td>
                    <td className="px-3 py-1.5 font-mono text-slate-500">{event.model || '—'}</td>
                    <td className="px-3 py-1.5 text-right font-mono text-slate-500">{num(event.latency_ms).toFixed(1)}ms</td>
                    <td className="px-3 py-1.5 max-w-xs">
                      <span className="text-slate-600 dark:text-slate-300 line-clamp-2">{event.reason || '—'}</span>
                      {event.error && <div className="mt-1 rounded bg-rose-50 dark:bg-rose-900/20 px-1.5 py-0.5 text-[9px] text-rose-700 dark:text-rose-300 truncate">Error: {event.error}</div>}
                      {event.feedback_reason && <div className="mt-1 rounded bg-violet-50 dark:bg-violet-900/20 px-1.5 py-0.5 text-[9px] text-violet-700 dark:text-violet-300 truncate">Feedback: {event.feedback_reason}</div>}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-[10px] text-slate-400 whitespace-nowrap">{new Date(event.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        <div className="flex items-center justify-between border-t border-slate-200/60 dark:border-slate-700/40 px-3 py-2">
          <span className="text-[10px] text-slate-400">
            {items.length === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total.toLocaleString()}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage((c) => Math.max(1, c - 1))} disabled={page === 1} className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2 py-1 text-[10px] font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40">
              <ChevronLeft className="h-3 w-3" /> Prev
            </button>
            <button onClick={() => setPage((c) => Math.min(totalPages, c + 1))} disabled={page >= totalPages} className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 px-2 py-1 text-[10px] font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40">
              Next <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>

      {/* ── Quick nav ─────────────────────────────── */}
      <div className="flex flex-wrap gap-1.5">
        {[
          { label: 'Guardrails', href: '/guardrails' },
          { label: 'Gateway', href: '/gateway' },
          { label: 'Security', href: '/security' },
          { label: 'Audit Log', href: '/audit-log' },
          { label: 'Monitoring', href: '/monitoring' },
        ].map(({ label, href }) => (
          <Link key={label} href={href} className="rounded-full bg-rose-100 dark:bg-rose-900/30 px-2.5 py-1 text-[10px] font-semibold text-rose-700 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-800/40 transition-colors">{label}</Link>
        ))}
      </div>
    </div>
  )
}
