'use client'

import { useEffect, useState, useMemo } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import Link from 'next/link'
import {
  AlertCircle, AlertTriangle, BookOpen, ChevronDown, ChevronUp,
  Cpu, DollarSign, ExternalLink, FileJson, FileText, Info,
  Network, Plus, Shield, Terminal, Wrench, X, Zap,
} from 'lucide-react'
import { listRunbooks, generateRunbook, exportRunbook, getRunbooksRemediationPosture } from '@/lib/api'
import type { RunbookResponse, RunbooksRemediationPosture } from '@/types/api'
import { num } from '@/lib/utils'

const PAGE_SIZE = 20

const SEV_STYLE: Record<string, { cls: string; dot: string; icon: typeof Info }> = {
  info: { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300', dot: 'bg-blue-400', icon: Info },
  warning: { cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300', dot: 'bg-amber-400', icon: AlertTriangle },
  critical: { cls: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300', dot: 'bg-red-400', icon: AlertCircle },
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

  const [showGenerate, setShowGenerate] = useState(false)
  const [generateRunId, setGenerateRunId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [posture, setPosture] = useState<RunbooksRemediationPosture | null>(null)

  useEffect(() => {
    if (apiKey) getRunbooksRemediationPosture(apiKey).then(setPosture).catch(() => {})
  }, [apiKey])

  useEffect(() => {
    if (!apiKey) return
    setLoading(true)
    listRunbooks(apiKey, {
      severity: severity === 'all' ? undefined : severity,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((res) => { setRunbooks(res.items); setTotal(res.total) })
      .catch((err) => toast.error(err.message ?? 'Failed to load runbooks'))
      .finally(() => setLoading(false))
  }, [apiKey, severity, page])

  useEffect(() => { setPage(0) }, [severity])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const sevCounts = useMemo(() => {
    const acc: Record<string, number> = { info: 0, warning: 0, critical: 0 }
    runbooks.forEach(rb => { acc[rb.severity] = (acc[rb.severity] ?? 0) + 1 })
    return acc
  }, [runbooks])

  async function handleGenerate() {
    if (!generateRunId.trim()) { toast.error('Enter a run ID'); return }
    setGenerating(true)
    try {
      const newRb = await generateRunbook(apiKey, generateRunId.trim())
      setRunbooks(prev => [newRb, ...prev])
      setTotal(prev => prev + 1)
      setGenerateRunId('')
      setShowGenerate(false)
      toast.success('Runbook generated')
    } catch (err: unknown) {
      toast.error((err as Error).message ?? 'Failed to generate runbook')
    } finally { setGenerating(false) }
  }

  async function handleExport(rb: RunbookResponse, format: 'markdown' | 'json') {
    try {
      const content = await exportRunbook(apiKey, rb.id, format)
      const ext = format === 'json' ? 'json' : 'md'
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `runbook-${rb.run_id.slice(0, 8)}-${new Date(rb.generated_at).toISOString().slice(0, 10)}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Exported as ${format.toUpperCase()}`)
    } catch (err: unknown) {
      toast.error((err as Error).message ?? 'Export failed')
    }
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-500/25">
            <BookOpen className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-950 dark:text-white">Runbooks</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Auto-generated post-mortems for agent runs — models, tools, cost, and recommendations.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { href: '/runs', label: 'Runs', icon: Terminal },
            { href: '/monitoring', label: 'Monitoring', icon: Shield },
            { href: '/agents', label: 'Agents', icon: Zap },
            { href: '/gateway', label: 'Gateway', icon: Network },
          ].map(nav => (
            <Link key={nav.label} href={nav.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <nav.icon className="h-3 w-3" /> {nav.label}
            </Link>
          ))}
          <button
            type="button"
            onClick={() => setShowGenerate(!showGenerate)}
            className="inline-flex items-center gap-1 rounded-lg bg-gradient-to-r from-amber-500 to-orange-600 px-2.5 py-1 text-[11px] font-bold text-white shadow-sm hover:shadow-md"
          >
            <Plus className="h-3 w-3" /> Generate
          </button>
        </div>
      </div>

      {/* Generate form */}
      {showGenerate && (
        <div className="rounded-xl border border-amber-200/60 bg-amber-50/30 p-3 dark:border-amber-800/40 dark:bg-amber-950/20">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <label htmlFor="run-id-input" className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-slate-400">Run ID</label>
              <input
                id="run-id-input"
                type="text"
                value={generateRunId}
                onChange={(e) => setGenerateRunId(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                placeholder="Paste a run ID to generate a post-mortem..."
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-mono dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              />
            </div>
            <button type="button" onClick={handleGenerate} disabled={generating}
              className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900">
              {generating ? 'Generating...' : 'Generate'}
            </button>
            <button type="button" onClick={() => setShowGenerate(false)} className="text-[10px] text-slate-400 hover:text-slate-600">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* KPI strip + severity filter */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
        {[
          { label: 'Total', value: total, icon: BookOpen, color: 'text-amber-600 dark:text-amber-400' },
          { label: 'Info', value: sevCounts.info, icon: Info, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Warning', value: sevCounts.warning, icon: AlertTriangle, color: 'text-amber-600 dark:text-amber-400' },
          { label: 'Critical', value: sevCounts.critical, icon: AlertCircle, color: 'text-red-600 dark:text-red-400' },
          { label: 'Runs 30d', value: posture?.observe_context.runs_30d ?? 0, icon: Terminal, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Alerts 30d', value: posture?.alert_context.alert_firings_30d ?? 0, icon: Shield, color: posture && posture.alert_context.alert_firings_30d > 0 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400' },
          { label: 'Cost 30d', value: posture ? `$${num(posture.cost_context.cost_30d).toFixed(2)}` : '$0', icon: DollarSign, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: 'Experiments', value: posture?.optimization_context.eval_experiments ?? 0, icon: Wrench, color: 'text-violet-600 dark:text-violet-400' },
        ].map(kpi => (
          <div key={kpi.label} className="rounded-xl border border-slate-200 bg-white/90 p-2.5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-1">
              <kpi.icon className={`h-3 w-3 ${kpi.color}`} />
              <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{kpi.label}</span>
            </div>
            <p className="mt-1 text-base font-bold text-slate-950 dark:text-white">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/50">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Severity</span>
        <div className="flex overflow-hidden rounded-lg border border-slate-200 text-[11px] dark:border-slate-700">
          {(['all', 'info', 'warning', 'critical'] as const).map(s => (
            <button key={s} onClick={() => setSeverity(s)}
              className={`px-2.5 py-1 capitalize transition-colors ${severity === s
                ? 'bg-slate-800 font-medium text-white dark:bg-slate-200 dark:text-slate-900'
                : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-400'}`}>
              {s}
            </button>
          ))}
        </div>
        <span className="ml-auto text-[10px] text-slate-400">{total} runbook{total !== 1 ? 's' : ''}</span>
      </div>

      {/* Runbook list */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" />)}
        </div>
      ) : runbooks.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 py-10 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <BookOpen className="mx-auto h-6 w-6 text-slate-400" />
          <p className="mt-2 text-sm font-semibold text-slate-700 dark:text-white">No runbooks yet</p>
          <p className="mt-1 text-xs text-slate-500">Generate a runbook from any agent run to get a post-mortem analysis.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {runbooks.map(rb => {
            const s = parseSummary(rb.summary)
            const isOpen = expanded === rb.id
            const sev = SEV_STYLE[rb.severity] ?? SEV_STYLE.info
            const SevIcon = sev.icon

            return (
              <div key={rb.id} className="rounded-xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <button
                  type="button"
                  onClick={() => setExpanded(isOpen ? null : rb.id)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left"
                >
                  <span className={`h-2 w-2 shrink-0 rounded-full shadow-sm ${sev.dot}`} />
                  <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${sev.cls}`}>
                    <SevIcon className="h-2.5 w-2.5" /> {rb.severity}
                  </span>
                  <code className="shrink-0 text-[10px] font-mono text-slate-400">{rb.run_id.slice(0, 12)}</code>
                  <p className="min-w-0 flex-1 truncate text-xs font-medium text-slate-700 dark:text-slate-300">{s.what_happened}</p>
                  <span className="shrink-0 text-[10px] text-slate-400">{new Date(rb.generated_at).toLocaleDateString()}</span>
                  {isOpen ? <ChevronUp className="h-3.5 w-3.5 shrink-0 text-slate-400" /> : <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-400" />}
                </button>

                {isOpen && (
                  <div className="space-y-3 border-t border-slate-100 px-4 py-3 dark:border-slate-800">
                    {/* Actions */}
                    <div className="flex flex-wrap items-center gap-1.5">
                      <button type="button" onClick={() => handleExport(rb, 'markdown')}
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        <FileText className="h-2.5 w-2.5" /> Markdown
                      </button>
                      <button type="button" onClick={() => handleExport(rb, 'json')}
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                        <FileJson className="h-2.5 w-2.5" /> JSON
                      </button>
                      <Link href={`/runs/${rb.run_id}`}
                        className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300">
                        <ExternalLink className="h-2.5 w-2.5" /> View Run
                      </Link>
                    </div>

                    {/* What happened */}
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">What Happened</p>
                      <p className="mt-1 text-xs leading-relaxed text-slate-700 dark:text-slate-300">{s.what_happened}</p>
                    </div>

                    {/* Chips: models, providers, tools, cost */}
                    <div className="flex flex-wrap gap-3">
                      {[
                        { label: 'Models', items: s.models_used, icon: Cpu, color: 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-300' },
                        { label: 'Providers', items: s.providers_used, icon: Network, color: 'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-300' },
                        { label: 'Tools', items: s.tools_used, icon: Wrench, color: 'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-800 dark:bg-orange-950/40 dark:text-orange-300' },
                      ].map(g => g.items.length > 0 && (
                        <div key={g.label}>
                          <p className="mb-1 text-[9px] font-semibold uppercase tracking-widest text-slate-400">{g.label}</p>
                          <div className="flex flex-wrap gap-1">
                            {g.items.map(item => (
                              <span key={item} className={`inline-flex items-center gap-0.5 rounded-md border px-1.5 py-0.5 text-[10px] font-medium ${g.color}`}>
                                <g.icon className="h-2.5 w-2.5" /> {item}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                      <div>
                        <p className="mb-1 text-[9px] font-semibold uppercase tracking-widest text-slate-400">Cost</p>
                        <span className="inline-flex items-center gap-0.5 rounded-md border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
                          <DollarSign className="h-2.5 w-2.5" /> ${s.total_cost_usd}
                        </span>
                      </div>
                    </div>

                    {/* Error */}
                    {s.error_details && (
                      <div className="rounded-lg border border-red-200 bg-red-50/60 px-3 py-2 dark:border-red-800/40 dark:bg-red-950/20">
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-red-500">Error</p>
                        <p className="mt-0.5 text-xs text-red-700 dark:text-red-300">{s.error_details}</p>
                      </div>
                    )}

                    {/* Recommendations */}
                    {s.recommendations.length > 0 && (
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">Recommendations</p>
                        <ol className="mt-1 list-inside list-decimal space-y-0.5 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                          {s.recommendations.map((rec, i) => <li key={i}>{rec}</li>)}
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
        <div className="flex items-center justify-between border-t border-slate-100 pt-3 text-[10px] text-slate-400 dark:border-slate-700">
          <span>{page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}</span>
          <div className="flex gap-1.5">
            <button type="button" disabled={page === 0} onClick={() => setPage(p => p - 1)}
              className="rounded border border-slate-300 px-2 py-0.5 font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300">Prev</button>
            <button type="button" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}
              className="rounded border border-slate-300 px-2 py-0.5 font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300">Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
