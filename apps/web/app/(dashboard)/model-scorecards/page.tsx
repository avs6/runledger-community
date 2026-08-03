'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import { Trophy, Star, ArrowUpDown } from 'lucide-react'
import { getModelScorecards } from '@/lib/api'
import type { ModelScorecard } from '@/types/api'

type SortKey = keyof ModelScorecard
type SortDir = 'asc' | 'desc'

function fmt(v: string | null | undefined, fallback = '—'): string {
  if (v == null || v === '') return fallback
  return v
}

function fmtUsd(v: string | number): string {
  return `$${Number(v).toFixed(2)}`
}

function fmtNum(v: string | number): string {
  return Number(v).toLocaleString()
}

function fmtPct(v: string | number): string {
  return `${(Number(v) * 100).toFixed(1)}%`
}

function sortValue(row: ModelScorecard, key: SortKey): number | string {
  const v = row[key]
  if (v == null || v === '') return -Infinity
  const n = Number(v)
  return isNaN(n) ? String(v).toLowerCase() : n
}

export default function ModelScorecardsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const [data, setData] = useState<ModelScorecard[]>([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('total_cost_usd')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  useEffect(() => {
    if (!apiKey) return
    setLoading(true)
    getModelScorecards(apiKey)
      .then(res => setData(res.items))
      .catch(() => toast.error('Failed to load model scorecards'))
      .finally(() => setLoading(false))
  }, [apiKey])

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sorted = [...data].sort((a, b) => {
    const av = sortValue(a, sortKey)
    const bv = sortValue(b, sortKey)
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'asc' ? cmp : -cmp
  })

  const thClass =
    'cursor-pointer select-none whitespace-nowrap px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100'

  function Th({ label, col }: { label: string; col: SortKey }) {
    return (
      <th className={thClass} onClick={() => toggleSort(col)}>
        <span className="inline-flex items-center gap-1">
          {label}
          <ArrowUpDown className="h-3 w-3 opacity-40" />
          {sortKey === col && (
            <span className="text-[10px]">{sortDir === 'asc' ? '▲' : '▼'}</span>
          )}
        </span>
      </th>
    )
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-900/30">
          <Trophy className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Model Quality Scorecards
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Compare models across cost, latency, quality, and reliability
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        {loading ? (
          <div className="flex items-center justify-center py-12 text-slate-400">Loading...</div>
        ) : sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <Trophy className="mb-3 h-8 w-8 opacity-40" />
            <p>No model data yet. Start sending requests through the gateway.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <Th label="Model" col="model" />
                  <Th label="Cost" col="total_cost_usd" />
                  <Th label="Calls" col="call_count" />
                  <Th label="Avg Cost/Call" col="avg_cost_per_call" />
                  <Th label="Avg Latency (ms)" col="avg_latency_ms" />
                  <Th label="P95 Latency (ms)" col="p95_latency_ms" />
                  <Th label="Error Rate" col="error_rate" />
                  <Th label="Cache Hit Rate" col="cache_hit_rate" />
                  <Th label="Quality Score" col="avg_quality_score" />
                  <Th label="Tokens" col="input_tokens" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {sorted.map(row => {
                  const errorRate = Number(row.error_rate ?? 0)
                  const cacheRate = Number(row.cache_hit_rate ?? 0)
                  const totalTokens = Number(row.input_tokens ?? 0) + Number(row.output_tokens ?? 0)

                  return (
                    <tr
                      key={row.model}
                      className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                    >
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {row.model}
                        </div>
                        {row.provider && (
                          <div className="text-xs text-slate-400">{row.provider}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-700 dark:text-slate-300">
                        {fmtUsd(row.total_cost_usd)}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {fmtNum(row.call_count)}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-700 dark:text-slate-300">
                        {fmtUsd(row.avg_cost_per_call)}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {fmt(row.avg_latency_ms)}
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {fmt(row.p95_latency_ms)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            errorRate > 0.05
                              ? 'font-medium text-red-600 dark:text-red-400'
                              : 'text-slate-700 dark:text-slate-300'
                          }
                        >
                          {fmtPct(row.error_rate)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            cacheRate > 0.5
                              ? 'font-medium text-green-600 dark:text-green-400'
                              : 'text-slate-700 dark:text-slate-300'
                          }
                        >
                          {row.cache_hit_rate != null ? fmtPct(row.cache_hit_rate) : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1 text-slate-700 dark:text-slate-300">
                          {row.avg_quality_score != null ? (
                            <>
                              <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                              {Number(row.avg_quality_score).toFixed(2)}
                            </>
                          ) : (
                            '—'
                          )}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                        {fmtNum(totalTokens)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
