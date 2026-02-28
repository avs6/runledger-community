'use client'

import { useState } from 'react'
import { getVersionCompare } from '@/lib/api'
import type { VersionCompareResult } from '@/types/api'

interface DeltaCardProps {
  label: string
  value: string | null | undefined
}

function DeltaCard({ label, value }: DeltaCardProps) {
  if (value == null) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-base font-semibold text-gray-400">—</p>
      </div>
    )
  }
  const pct = parseFloat(value)
  const positive = pct > 0
  const colour = positive ? 'text-red-600' : 'text-green-600'
  const bg = positive ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
  return (
    <div className={`rounded-lg border px-4 py-3 ${bg}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-lg font-semibold tabular-nums ${colour}`}>
        {positive ? '+' : ''}{pct.toFixed(2)}%
      </p>
    </div>
  )
}

interface Props {
  apiKey: string
}

export default function ChangeImpactPanel({ apiKey }: Props) {
  const [baseline, setBaseline] = useState('')
  const [comparison, setComparison] = useState('')
  const [result, setResult] = useState<VersionCompareResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCompare() {
    if (!baseline.trim() || !comparison.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await getVersionCompare(apiKey, baseline.trim(), comparison.trim())
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Compare failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Inputs */}
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Baseline version</label>
          <input
            type="text"
            value={baseline}
            onChange={(e) => setBaseline(e.target.value)}
            placeholder="e.g. v1"
            className="h-9 rounded-md border border-gray-300 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Comparison version
          </label>
          <input
            type="text"
            value={comparison}
            onChange={(e) => setComparison(e.target.value)}
            placeholder="e.g. v2"
            className="h-9 rounded-md border border-gray-300 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <button
          onClick={handleCompare}
          disabled={loading || !baseline.trim() || !comparison.trim()}
          className="h-9 rounded-md bg-indigo-600 px-4 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Loading…' : 'Compare'}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result && (
        <div className="space-y-4">
          {/* Delta summary cards */}
          <div className="grid grid-cols-3 gap-3">
            <DeltaCard label="Cost Δ%" value={result.cost_delta_pct} />
            <DeltaCard label="Input Token Δ%" value={result.token_delta_pct} />
            <DeltaCard label="Latency Δ%" value={result.latency_delta_pct} />
          </div>

          {/* Version summaries */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {([result.baseline, result.comparison] as const).map((v) => (
              <div key={v.version} className="rounded-lg border border-gray-200 p-3">
                <p className="mb-1 font-semibold text-gray-700">{v.version}</p>
                <p className="text-gray-500">
                  {v.run_count} runs · ${parseFloat(v.avg_cost_usd).toFixed(6)} avg cost
                </p>
                {v.avg_latency_ms && (
                  <p className="text-gray-500">
                    {parseFloat(v.avg_latency_ms).toFixed(0)} ms avg latency
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Span-type breakdown table */}
          {result.by_span_type.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-gray-500">
                  <th className="pb-1 font-medium">Span type</th>
                  <th className="pb-1 text-right font-medium">Baseline cost</th>
                  <th className="pb-1 text-right font-medium">Comparison cost</th>
                  <th className="pb-1 text-right font-medium">Δ%</th>
                </tr>
              </thead>
              <tbody>
                {result.by_span_type.map((row) => {
                  const pct = row.delta_pct != null ? parseFloat(row.delta_pct) : null
                  return (
                    <tr key={row.span_type} className="border-b last:border-0">
                      <td className="py-1.5">{row.span_type}</td>
                      <td className="py-1.5 text-right tabular-nums">
                        ${parseFloat(row.baseline_cost).toFixed(6)}
                      </td>
                      <td className="py-1.5 text-right tabular-nums">
                        ${parseFloat(row.comparison_cost).toFixed(6)}
                      </td>
                      <td
                        className={`py-1.5 text-right tabular-nums font-medium ${
                          pct == null
                            ? 'text-gray-400'
                            : pct > 0
                            ? 'text-red-600'
                            : 'text-green-600'
                        }`}
                      >
                        {pct == null
                          ? '—'
                          : `${pct > 0 ? '+' : ''}${pct.toFixed(2)}%`}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
