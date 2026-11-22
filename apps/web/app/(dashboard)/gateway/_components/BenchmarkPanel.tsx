'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { BarChart2 } from 'lucide-react'
import { getGatewayBenchmarkComparison } from '@/lib/api'
import type { GatewayBenchmarkComparisonItem } from '@/types/api'
import { inputCls } from './shared'

export function BenchmarkPanel({ apiKey }: { apiKey: string }) {
  const [days, setDays] = useState('7')
  const [items, setItems] = useState<GatewayBenchmarkComparisonItem[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getGatewayBenchmarkComparison(apiKey, { days: parseInt(days, 10) || 7 })
      setItems(data.items)
    } catch {
      toast.error('Failed to load benchmark comparison')
    } finally {
      setLoading(false)
    }
  }, [apiKey, days])

  useEffect(() => { void load() }, [load])

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold dark:text-white">Performance And Benchmarking</h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Gateway overhead, throughput, and direct-provider comparison by alias over a rolling window.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select value={days} onChange={(e) => setDays(e.target.value)} className={inputCls}>
            <option value="1">Last 24h</option>
            <option value="7">Last 7d</option>
            <option value="30">Last 30d</option>
          </select>
          <button
            onClick={() => void load()}
            disabled={loading}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 py-8 text-center text-sm text-slate-400">
          No benchmark data yet. Drive traffic through one or more aliases to populate overhead and throughput metrics.
        </div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {items.map((item) => (
            <div key={item.alias} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800/40">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <BarChart2 className="h-4 w-4 text-indigo-500" />
                    <span className="font-mono text-sm text-slate-800 dark:text-slate-100">{item.alias}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {item.request_count} requests in the last {days === '1' ? '24 hours' : `${days} days`}
                  </p>
                </div>
                <div className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                  {item.throughput_rpm ? `${parseFloat(item.throughput_rpm).toFixed(2)} rpm` : '0 rpm'}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-3">
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">P50 overhead</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.p50_gateway_overhead_ms ? `${parseFloat(item.p50_gateway_overhead_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">P95 overhead</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.p95_gateway_overhead_ms ? `${parseFloat(item.p95_gateway_overhead_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">P99 overhead</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.p99_gateway_overhead_ms ? `${parseFloat(item.p99_gateway_overhead_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">Provider latency</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.avg_provider_latency_ms ? `${parseFloat(item.avg_provider_latency_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">End-to-end</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.avg_end_to_end_latency_ms ? `${parseFloat(item.avg_end_to_end_latency_ms).toFixed(0)}ms` : '—'}
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-900/30">
                  <p className="text-slate-400">Overhead vs provider</p>
                  <p className="font-semibold text-slate-700 dark:text-slate-100">
                    {item.overhead_vs_provider_pct ? `${(parseFloat(item.overhead_vs_provider_pct) * 100).toFixed(1)}%` : '—'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
