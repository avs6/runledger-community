'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import { ArrowLeft, ChevronLeft, ChevronRight, Filter, ShieldAlert } from 'lucide-react'
import { listGuardrailEvents } from '@/lib/api'
import type { GuardrailEventResponse } from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

const decisionColors: Record<string, string> = {
  allow: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  block: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300',
  modify: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
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

  useEffect(() => {
    setPage(1)
  }, [query, decision, mode, falsePositiveFilter, violationsOnly, pageSize])

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
          false_positive:
            falsePositiveFilter === 'all'
              ? undefined
              : falsePositiveFilter === 'only',
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
    return <div className="p-8 text-slate-500">Sign in to view guardrail violations.</div>
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6 md:p-10">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link
            href="/guardrails"
            className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Guardrails
          </Link>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Guardrail Violations Log
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Filterable, paginated enforcement history for guardrail blocks, modifications,
            and related event outcomes in{' '}
            <strong>{workspaceName ?? 'the current workspace'}</strong>.
          </p>
        </div>
      </div>

      <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <Filter className="h-4 w-4" />
          Filters
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-300 xl:col-span-2">
            Guardrail name
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by guardrail name..."
              className={`${inputCls} mt-1`}
            />
          </label>

          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Decision
            <select
              value={decision}
              onChange={(e) => setDecision(e.target.value as typeof decision)}
              className={`${inputCls} mt-1`}
            >
              <option value="all">All</option>
              <option value="block">Block</option>
              <option value="modify">Modify</option>
              <option value="allow">Allow</option>
            </select>
          </label>

          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Mode
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as typeof mode)}
              className={`${inputCls} mt-1`}
            >
              <option value="all">All</option>
              <option value="pre_call">pre_call</option>
              <option value="post_call">post_call</option>
              <option value="during_call">during_call</option>
              <option value="both">both</option>
            </select>
          </label>

          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
            False positive
            <select
              value={falsePositiveFilter}
              onChange={(e) => setFalsePositiveFilter(e.target.value as FalsePositiveFilter)}
              className={`${inputCls} mt-1`}
            >
              <option value="all">All</option>
              <option value="only">Only false positives</option>
              <option value="exclude">Exclude false positives</option>
            </select>
          </label>

          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Page size
            <select
              value={String(pageSize)}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className={`${inputCls} mt-1`}
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={() => setViolationsOnly((current) => !current)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              violationsOnly
                ? 'bg-rose-600 text-white hover:bg-rose-700'
                : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            {violationsOnly ? 'Showing only violations' : 'Showing all evaluations'}
          </button>
          <div className="text-sm text-slate-500">
            Total results: <strong>{total.toLocaleString()}</strong>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-800 dark:bg-slate-900/85">
        <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Enforcement Events
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Every logged guardrail evaluation is workspace-scoped and recorded here for review.
              </p>
            </div>
            <div className="text-sm text-slate-500">
              Page {page} of {totalPages}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">Loading violations log...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">
            No events matched the current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:bg-slate-800/60">
                <tr>
                  <th className="px-4 py-3">Guardrail</th>
                  <th className="px-4 py-3">Decision</th>
                  <th className="px-4 py-3">Workspace</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Reason</th>
                  <th className="px-4 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {items.map((event) => (
                  <tr key={event.id} className="align-top">
                    <td className="px-4 py-4">
                      <div className="font-medium text-slate-900 dark:text-white">
                        {event.guardrail_name}
                      </div>
                      {event.is_false_positive && (
                        <div className="mt-1 inline-flex rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-700 dark:bg-violet-950 dark:text-violet-300">
                          false positive
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${
                          decisionColors[event.decision] || decisionColors.allow
                        }`}
                      >
                        {event.decision}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      <div>{workspaceName ?? 'Current workspace'}</div>
                      <div className="mt-1 font-mono text-xs text-slate-400">{event.workspace_id}</div>
                    </td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">{event.mode}</td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">{event.model || '--'}</td>
                    <td className="px-4 py-4 text-slate-600 dark:text-slate-300">
                      {event.latency_ms.toFixed(1)} ms
                    </td>
                    <td className="max-w-md px-4 py-4 text-slate-600 dark:text-slate-300">
                      <div>{event.reason || 'No reason recorded'}</div>
                      {event.error && (
                        <div className="mt-2 rounded-xl bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-950/50 dark:text-rose-300">
                          Error: {event.error}
                        </div>
                      )}
                      {event.feedback_reason && (
                        <div className="mt-2 rounded-xl bg-violet-50 px-3 py-2 text-xs text-violet-700 dark:bg-violet-950/50 dark:text-violet-300">
                          Feedback: {event.feedback_reason}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4 font-mono text-xs text-slate-500">
                      {new Date(event.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-col gap-3 border-t border-slate-200 px-6 py-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-500">
            Showing {items.length === 0 ? 0 : (page - 1) * pageSize + 1}-
            {Math.min(page * pageSize, total)} of {total.toLocaleString()}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page === 1}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <button
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-slate-50/70 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950/40">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-5 w-5 text-slate-500 dark:text-slate-300" />
          <div className="text-sm text-slate-600 dark:text-slate-300">
            This log is backed by the real guardrail event stream from runtime enforcement.
            When a guardrail allows, blocks, or modifies traffic, the backend writes a
            `GuardrailEvent` that is filterable here by decision, mode, false-positive state,
            and guardrail name.
          </div>
        </div>
      </section>
    </div>
  )
}
