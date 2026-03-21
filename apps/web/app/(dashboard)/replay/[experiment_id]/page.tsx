'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getExperimentResults } from '@/lib/api'
import type { ExperimentResults } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronLeft, Loader2 } from 'lucide-react'

export default function ExperimentResultsPage() {
  const { data: session } = useSession()
  const params = useParams()
  const experimentId = params.experiment_id as string
  const [results, setResults] = useState<ExperimentResults | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!session?.apiKey || !experimentId) return
    getExperimentResults(session.apiKey as string, experimentId)
      .then((r) => {
        setResults(r)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [session?.apiKey, experimentId])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading…
      </div>
    )
  }

  if (!results) {
    return <p className="text-sm text-gray-400">Experiment not found.</p>
  }

  if (results.status !== 'completed') {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="text-sm font-medium text-gray-700">
          Experiment in progress — results will appear when complete.
        </p>
        <p className="text-xs text-gray-400">Status: {results.status}</p>
        <Link href="/replay" className="text-xs text-blue-600 hover:underline">
          ← Back to Replay
        </Link>
      </div>
    )
  }

  const lowestCostConfig = [...results.configs].sort(
    (a, b) => parseFloat(a.projected_cost_usd) - parseFloat(b.projected_cost_usd)
  )[0]

  const firstDelta =
    results.deltas.length > 0 ? results.deltas[0] : null

  const chartData = results.configs.map((c) => ({
    name: c.label ?? c.model,
    cost: parseFloat(c.projected_cost_usd),
  }))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link
          href="/replay"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        >
          <ChevronLeft className="h-4 w-4" />
          Replay
        </Link>
        <span className="text-sm text-gray-400">/</span>
        <h1 className="text-xl font-semibold">{results.experiment_name}</h1>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-gray-500">Dataset runs</p>
            <p className="text-2xl font-semibold">{results.dataset_run_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-gray-500">Configs compared</p>
            <p className="text-2xl font-semibold">{results.configs.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-gray-500">Lowest cost config</p>
            <p className="text-sm font-semibold truncate">
              {lowestCostConfig ? (lowestCostConfig.label ?? lowestCostConfig.model) : '—'}
            </p>
            {lowestCostConfig && (
              <p className="text-xs text-gray-400">
                ${parseFloat(lowestCostConfig.projected_cost_usd).toFixed(4)}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-gray-500">Cost delta</p>
            {firstDelta?.cost_delta_pct != null ? (
              <p
                className={`text-2xl font-semibold ${
                  parseFloat(firstDelta.cost_delta_pct) < 0
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}
              >
                {parseFloat(firstDelta.cost_delta_pct).toFixed(1)}%
              </p>
            ) : (
              <p className="text-2xl font-semibold text-gray-400">—</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Config table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Config Results</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs font-medium text-gray-500">
                <th className="pb-2 pr-3">Model</th>
                <th className="pb-2 pr-3">Prompt</th>
                <th className="pb-2 pr-3">Runs</th>
                <th className="pb-2 pr-3">Input tokens</th>
                <th className="pb-2 pr-3">Output tokens</th>
                <th className="pb-2 pr-3">Avg cost/run</th>
                <th className="pb-2 pr-3">Total cost</th>
                <th className="pb-2">Pricing</th>
              </tr>
            </thead>
            <tbody>
              {results.configs.map((c, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-2 pr-3 font-mono text-xs">
                    {c.model}
                    {c.label && <span className="ml-1 text-gray-400">({c.label})</span>}
                  </td>
                  <td className="py-2 pr-3">
                    {c.prompt_name ? (
                      <div>
                        <span className="rounded-full bg-teal-100 px-2 py-0.5 text-xs text-teal-700 font-mono">
                          {c.prompt_name}{c.prompt_version != null ? `@v${c.prompt_version}` : ''}
                        </span>
                        {c.prompt_content_preview && (
                          <p className="mt-1 max-w-[200px] truncate text-[10px] text-gray-400" title={c.prompt_content_preview}>
                            {c.prompt_content_preview}
                          </p>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-400 text-xs">all runs</span>
                    )}
                  </td>
                  <td className="py-2 pr-3">{c.run_count.toLocaleString()}</td>
                  <td className="py-2 pr-3">{c.total_input_tokens.toLocaleString()}</td>
                  <td className="py-2 pr-3">{c.total_output_tokens.toLocaleString()}</td>
                  <td className="py-2 pr-3">${parseFloat(c.avg_cost_per_run).toFixed(6)}</td>
                  <td className="py-2 pr-3">${parseFloat(c.projected_cost_usd).toFixed(4)}</td>
                  <td className="py-2">
                    {c.pricing_found ? (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                        ✓ Found
                      </span>
                    ) : (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                        ⚠ No pricing data
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Delta table */}
      {results.deltas.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Cost Deltas</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs font-medium text-gray-500">
                  <th className="pb-2 pr-3">Baseline</th>
                  <th className="pb-2 pr-3">Comparison</th>
                  <th className="pb-2">Delta %</th>
                </tr>
              </thead>
              <tbody>
                {results.deltas.map((d, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 pr-3 font-mono text-xs">{d.config_a}</td>
                    <td className="py-2 pr-3 font-mono text-xs">{d.config_b}</td>
                    <td className="py-2">
                      {d.cost_delta_pct != null ? (
                        <span
                          className={
                            parseFloat(d.cost_delta_pct) < 0
                              ? 'font-semibold text-green-600'
                              : 'font-semibold text-red-600'
                          }
                        >
                          {parseFloat(d.cost_delta_pct).toFixed(1)}%
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Bar chart */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Projected Cost by Config</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${v.toFixed(3)}`} />
                <Tooltip formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(6)}`, 'Projected cost']} />
                <Bar dataKey="cost" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {results.completed_at && (
        <p className="text-xs text-gray-400">
          Completed {new Date(results.completed_at).toLocaleString()}
        </p>
      )}
    </div>
  )
}
