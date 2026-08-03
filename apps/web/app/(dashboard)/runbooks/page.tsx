'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { BookOpen, ChevronDown, ChevronUp, AlertTriangle, AlertCircle, Info } from 'lucide-react'
import { listRunbooks } from '@/lib/api'
import type { RunbookResponse } from '@/types/api'

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
  const [loading, setLoading] = useState(true)
  const [severity, setSeverity] = useState<string>('all')
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    if (!apiKey) return
    setLoading(true)
    listRunbooks(apiKey, { severity: severity === 'all' ? undefined : severity, limit: 100 })
      .then((res) => setRunbooks(res.items))
      .catch((err) => toast.error(err.message ?? 'Failed to load runbooks'))
      .finally(() => setLoading(false))
  }, [apiKey, severity])

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <BookOpen className="h-7 w-7 text-slate-600 dark:text-slate-400" />
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
            Agent Runbooks
          </h1>
          <p className="text-sm text-slate-500">Auto-generated post-mortem summaries for agent runs</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Severity</label>
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
    </div>
  )
}
