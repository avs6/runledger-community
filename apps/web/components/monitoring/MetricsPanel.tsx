'use client'

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { apiErrorMessage, getOtlpMetricUsage, listOtlpMetricSeries } from '@/lib/api'
import type { OtlpMetricSeries, OtlpMetricUsage } from '@/types/api'

const WINDOWS = [1, 7, 30] as const

function fmt(n: number | null | undefined, digits = 0): string {
  if (n == null) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: digits })
}

function attrText(attrs: OtlpMetricSeries['attributes']): string {
  const entries = Object.entries(attrs)
  if (entries.length === 0) return '—'
  return entries.map(([k, v]) => `${k}=${v}`).join(', ')
}

/**
 * OTLP metrics, rolled up per series per day, plus GenAI usage reported by metrics
 * (gen_ai.client.token.usage, claude_code.token.usage / cost.usage) compared with the
 * usage RunLedger recorded. A low coverage figure means a client exports metrics but
 * its calls are not reaching RunLedger as traces, logs or events.
 */
export default function MetricsPanel({ apiKey }: { apiKey: string }) {
  const [days, setDays] = useState<(typeof WINDOWS)[number]>(7)
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [series, setSeries] = useState<OtlpMetricSeries[]>([])
  const [total, setTotal] = useState(0)
  const [usage, setUsage] = useState<OtlpMetricUsage | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [list, use] = await Promise.all([
        listOtlpMetricSeries(apiKey, days, search || undefined, 50),
        getOtlpMetricUsage(apiKey, days),
      ])
      setSeries(list.items)
      setTotal(list.total)
      setUsage(use)
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to load metrics'))
    } finally {
      setLoading(false)
    }
  }, [apiKey, days, search])

  useEffect(() => {
    void load()
  }, [load])

  const reported = usage?.reported
  return (
    <div className="rounded-xl border border-slate-200 bg-white/90 p-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Metrics</p>
          <p className="text-[10px] text-slate-400">
            OTLP metrics rolled up per series per day. Counters show the increase in the window; gauges show the latest value.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              setSearch(query.trim())
            }}
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by name"
              aria-label="Filter metrics by name"
              className="w-36 rounded border border-slate-300 bg-transparent px-2 py-0.5 text-[11px] dark:border-slate-700"
            />
          </form>
          <div className="flex rounded border border-slate-300 dark:border-slate-700">
            {WINDOWS.map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays(d)}
                className={`px-2 py-0.5 text-[10px] font-semibold ${days === d ? 'bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900' : 'text-slate-500'}`}
              >
                {d === 1 ? '24h' : `${d}d`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {reported?.reported && usage && (
        <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            ['Tokens reported by metrics', fmt(reported.input_tokens + reported.output_tokens)],
            ['Tokens recorded by RunLedger', fmt(usage.recorded.input_tokens + usage.recorded.output_tokens)],
            ['Token coverage', usage.token_coverage_pct == null ? '—' : `${usage.token_coverage_pct}%`],
            [
              'Cost reported / recorded',
              `$${fmt(reported.cost_usd, 2)} / $${fmt(usage.recorded.cost_usd, 2)}`,
            ],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
              <p className="text-[10px] uppercase tracking-widest text-slate-400">{label}</p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{value}</p>
            </div>
          ))}
        </div>
      )}

      {loading && series.length === 0 ? (
        <div className="h-6 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
      ) : series.length === 0 ? (
        <div className="rounded border border-dashed border-slate-300 py-4 text-center text-[11px] text-slate-400 dark:border-slate-700">
          No metrics in this window. Send OTLP metrics to /v1/metrics with an ingest key.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                {['Metric', 'Service', 'Attributes', 'Kind', 'Points', 'Total', 'Last', 'Unit'].map((h) => (
                  <th key={h} className="px-2 py-1 text-left text-[10px] font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {series.map((s) => (
                <tr key={s.series_key} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="px-2 py-1 font-mono text-[11px] text-slate-700 dark:text-slate-200">{s.name}</td>
                  <td className="px-2 py-1 text-slate-500">{s.service_name ?? '—'}</td>
                  <td className="max-w-[16rem] truncate px-2 py-1 text-[10px] text-slate-500" title={attrText(s.attributes)}>
                    {attrText(s.attributes)}
                  </td>
                  <td className="px-2 py-1 text-slate-500">
                    {s.kind}
                    {s.temporality ? ` · ${s.temporality}` : ''}
                  </td>
                  <td className="px-2 py-1 tabular-nums">{fmt(s.points)}</td>
                  <td className="px-2 py-1 tabular-nums">{fmt(s.total, 2)}</td>
                  <td className="px-2 py-1 tabular-nums">{fmt(s.last, 2)}</td>
                  <td className="px-2 py-1 text-slate-500">{s.unit ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > series.length && (
            <p className="mt-1 text-[10px] text-slate-400">
              Showing the {series.length} busiest of {total} series. Filter by name to narrow it down.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
