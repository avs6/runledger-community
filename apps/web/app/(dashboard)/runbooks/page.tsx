'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  AlertCircle,
  Info,
  Download,
  FileJson,
  FileText,
  Network,
  Plus,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Shield,
} from 'lucide-react'
import { listRunbooks, generateRunbook, exportRunbook, getBudgetControlBuildPosture, getRunbooksRemediationPosture } from '@/lib/api'
import type { RunbookResponse, BudgetControlBuildPosture, RunbooksRemediationPosture } from '@/types/api'

const PAGE_SIZE = 20

const SEVERITY_STYLE: Record<string, string> = {
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

const SEVERITY_ICON: Record<string, typeof Info> = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertCircle,
}

function parseSummary(raw: Record<string, unknown>) {
  return {
    what_happened: (raw.what_happened as string) ?? '',
    recommendations: (raw.recommendations as string[]) ?? [],
    models_used: (raw.models_used as string[]) ?? [],
    providers_used: (raw.providers_used as string[]) ?? [],
    tools_used: (raw.tools_used as string[]) ?? [],
    total_cost_usd: (raw.total_cost_usd as string) ?? '0.00',
    error_details: (raw.error_details as string | null) ?? null,
  }
}

export default function RunbooksPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''

  const [runbooks, setRunbooks] = useState<RunbookResponse[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [severity, setSeverity] = useState<string>('all')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [page, setPage] = useState(0)

  // Generate form state
  const [showGenerate, setShowGenerate] = useState(false)
  const [generateRunId, setGenerateRunId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [budgetControlBuildPosture, setBudgetControlBuildPosture] = useState<BudgetControlBuildPosture | null>(null)
  const [remediationPosture, setRemediationPosture] = useState<RunbooksRemediationPosture | null>(null)

  useEffect(() => {
    if (apiKey) {
      getBudgetControlBuildPosture(apiKey).then(setBudgetControlBuildPosture).catch(() => {})
      getRunbooksRemediationPosture(apiKey).then(setRemediationPosture).catch(() => {})
    }
  }, [apiKey])

  useEffect(() => {
    if (!apiKey) return
    setLoading(true)
    listRunbooks(apiKey, {
      severity: severity === 'all' ? undefined : severity,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((res) => {
        setRunbooks(res.items)
        setTotal(res.total)
      })
      .catch((err) => toast.error(err.message ?? 'Failed to load runbooks'))
      .finally(() => setLoading(false))
  }, [apiKey, severity, page])

  // Reset page when severity filter changes
  useEffect(() => {
    setPage(0)
  }, [severity])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // Severity breakdown from current data
  const severityCounts = runbooks.reduce<Record<string, number>>((acc, rb) => {
    acc[rb.severity] = (acc[rb.severity] ?? 0) + 1
    return acc
  }, {})

  async function handleGenerate() {
    if (!generateRunId.trim()) {
      toast.error('Please enter a run ID')
      return
    }
    setGenerating(true)
    try {
      const newRb = await generateRunbook(apiKey, generateRunId.trim())
      setRunbooks((prev) => [newRb, ...prev])
      setTotal((prev) => prev + 1)
      setGenerateRunId('')
      setShowGenerate(false)
      toast.success('Runbook generated')
    } catch (err: unknown) {
      toast.error((err as Error).message ?? 'Failed to generate runbook')
    } finally {
      setGenerating(false)
    }
  }

  async function handleExport(rb: RunbookResponse, format: 'markdown' | 'json') {
    try {
      const content = await exportRunbook(apiKey, rb.id, format)
      const ext = format === 'json' ? 'json' : 'md'
      const mimeType = format === 'json' ? 'application/json' : 'text/markdown'
      const blob = new Blob([content], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `runbook-${rb.run_id.slice(0, 8)}-${new Date(rb.generated_at).toISOString().slice(0, 10)}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Runbook exported as ${format.toUpperCase()}`)
    } catch (err: unknown) {
      toast.error((err as Error).message ?? 'Export failed')
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <BookOpen className="h-7 w-7 text-slate-600 dark:text-slate-400" />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
              Agent Runbooks
            </h1>
            <p className="text-sm text-slate-500">Auto-generated post-mortem summaries for agent runs</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowGenerate(!showGenerate)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <Plus className="h-4 w-4" />
          Generate Runbook
        </button>
      </div>

      {budgetControlBuildPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget Control — Build Posture</p>
          </div>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetControlBuildPosture.budget_policy.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetControlBuildPosture.budget_policy.breached_budgets > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetControlBuildPosture.budget_policy.breached_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Avg Utilization</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{budgetControlBuildPosture.budget_policy.avg_utilization_pct.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Scope Types</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{Object.keys(budgetControlBuildPosture.scope_context).length}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?tab=overrides" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Overrides</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing</Link>
          </div>
        </div>
      )}

      {remediationPosture && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Observe, Alert &amp; Cost Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Runs 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{remediationPosture.observe_context.runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Alert Rules</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{remediationPosture.alert_context.alert_rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Alert Firings 30d</p>
              <p className={`mt-1 text-lg font-semibold ${remediationPosture.alert_context.alert_firings_30d > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{remediationPosture.alert_context.alert_firings_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-amber-600 dark:text-amber-400">${remediationPosture.cost_context.cost_30d.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{remediationPosture.optimization_context.eval_experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
            <Link href="/runs" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Runs</Link>
            <Link href="/alerts" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Alert Rules</Link>
            <Link href="/billing" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Billing Periods</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Cost &amp; Savings</Link>
            <Link href="/optimization-opportunities" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Optimization</Link>
          </div>
        </div>
      )}

      {/* Gateway & audit context bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-2.5 dark:border-slate-700 dark:bg-slate-800/50">
        <div className="flex items-center gap-2">
          <Network className="h-4 w-4 text-violet-600 dark:text-violet-400" />
          <p className="text-sm text-slate-600 dark:text-slate-300">Runbooks summarize gateway traffic, model decisions, and tool calls from agent runs.</p>
        </div>
        <div className="ml-auto flex gap-2">
          {[
            { label: 'Model Gateway', href: '/gateway', cls: 'border-violet-200 text-violet-700 hover:bg-violet-100 dark:border-violet-700 dark:text-violet-300 dark:hover:bg-violet-800/50' },
            { label: 'Audit Log', href: '/audit', cls: 'border-amber-200 text-amber-700 hover:bg-amber-100 dark:border-amber-700 dark:text-amber-300 dark:hover:bg-amber-800/50' },
            { label: 'Runs', href: '/runs', cls: 'border-blue-200 text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-800/50' },
          ].map(({ label, href, cls }) => (
            <Link key={label} href={href} className={`rounded-full border bg-white/80 px-3 py-1 text-xs font-semibold transition-colors dark:bg-slate-900/40 ${cls}`}>
              {label}
            </Link>
          ))}
        </div>
      </div>

      {/* Generate form */}
      {showGenerate && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label htmlFor="run-id-input" className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">
                Run ID
              </label>
              <input
                id="run-id-input"
                type="text"
                value={generateRunId}
                onChange={(e) => setGenerateRunId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                placeholder="Enter run ID..."
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              />
            </div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={generating}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            >
              {generating ? 'Generating...' : 'Generate'}
            </button>
            <button
              type="button"
              onClick={() => setShowGenerate(false)}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Summary stats and severity filter */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
          {total} runbook{total !== 1 ? 's' : ''}
        </span>
        <span className="text-slate-300 dark:text-slate-600">|</span>
        {['info', 'warning', 'critical'].map((sev) => (
          <span
            key={sev}
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLE[sev]}`}
          >
            {sev}: {severityCounts[sev] ?? 0}
          </span>
        ))}
        <span className="text-slate-300 dark:text-slate-600">|</span>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Filter</label>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
        >
          <option value="all">All</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      {/* Runbook list */}
      {loading ? (
        <div className="py-12 text-center text-sm text-slate-500">Loading runbooks...</div>
      ) : runbooks.length === 0 ? (
        <div className="py-12 text-center text-sm text-slate-500">No runbooks found.</div>
      ) : (
        <div className="space-y-3">
          {runbooks.map((rb) => {
            const s = parseSummary(rb.summary)
            const isOpen = expanded === rb.id
            const SevIcon = SEVERITY_ICON[rb.severity] ?? Info

            return (
              <div
                key={rb.id}
                className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
              >
                <button
                  type="button"
                  onClick={() => setExpanded(isOpen ? null : rb.id)}
                  className="flex w-full items-start justify-between gap-4 text-left"
                >
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${SEVERITY_STYLE[rb.severity] ?? SEVERITY_STYLE.info}`}
                      >
                        <SevIcon className="h-3 w-3" />
                        {rb.severity}
                      </span>
                      <code className="truncate text-xs text-slate-500 font-mono">
                        {rb.run_id.slice(0, 12)}...
                      </code>
                      <span className="text-xs text-slate-400">
                        {new Date(rb.generated_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <p className="truncate text-sm text-slate-700 dark:text-slate-300">
                      {s.what_happened}
                    </p>
                  </div>
                  {isOpen ? (
                    <ChevronUp className="mt-1 h-4 w-4 shrink-0 text-slate-400" />
                  ) : (
                    <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-slate-400" />
                  )}
                </button>

                {isOpen && (
                  <div className="mt-4 space-y-4 border-t border-slate-100 pt-4 dark:border-slate-800">
                    {/* Action bar: export + view run */}
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleExport(rb, 'markdown')}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
                        title="Export as Markdown"
                      >
                        <FileText className="h-3.5 w-3.5" />
                        Markdown
                      </button>
                      <button
                        type="button"
                        onClick={() => handleExport(rb, 'json')}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
                        title="Export as JSON"
                      >
                        <FileJson className="h-3.5 w-3.5" />
                        JSON
                      </button>
                      <Link
                        href={`/runs/${rb.run_id}`}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-blue-600 transition-colors hover:bg-blue-50 dark:border-slate-700 dark:text-blue-400 dark:hover:bg-blue-900/20"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        View Run
                      </Link>
                    </div>

                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        What Happened
                      </h3>
                      <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">
                        {s.what_happened}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-4">
                      {[
                        { label: 'Models', items: s.models_used },
                        { label: 'Providers', items: s.providers_used },
                        { label: 'Tools', items: s.tools_used },
                      ].map((group) => (
                        <div key={group.label}>
                          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            {group.label}
                          </h3>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {group.items.length > 0 ? (
                              group.items.map((item) => (
                                <span
                                  key={item}
                                  className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                                >
                                  {item}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-400">-</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Total Cost
                      </h3>
                      <p className="mt-1 text-sm font-medium text-slate-700 dark:text-slate-300">
                        ${s.total_cost_usd}
                      </p>
                    </div>

                    {s.error_details && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-red-500">
                          Error Details
                        </h3>
                        <p className="mt-1 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
                          {s.error_details}
                        </p>
                      </div>
                    )}

                    {s.recommendations.length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Recommendations
                        </h3>
                        <ol className="mt-1 list-inside list-decimal space-y-1 text-sm text-slate-700 dark:text-slate-300">
                          {s.recommendations.map((rec, i) => (
                            <li key={i}>{rec}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-slate-100 pt-4 dark:border-slate-800">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </button>
          <span className="text-sm text-slate-500">
            Page {page + 1} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}
