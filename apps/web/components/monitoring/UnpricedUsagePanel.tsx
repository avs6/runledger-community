'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { apiErrorMessage, getUnpricedUsage } from '@/lib/api'
import type { UnpricedUsage } from '@/types/api'

/**
 * Model calls that enrichment could not price (no pricing for the model). They carry
 * tokens but no cost, so spend, budgets and chargeback undercount them until pricing
 * is added; adding it prices them on the next enrichment sweep.
 *
 * `compact` renders a single headline card (Telemetry ingest health); the full view
 * lists each model (provider pricing page).
 */
export default function UnpricedUsagePanel({
  apiKey,
  days = 30,
  compact = false,
}: {
  apiKey: string
  days?: number
  compact?: boolean
}) {
  const [data, setData] = useState<UnpricedUsage | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getUnpricedUsage(apiKey, days)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err) => {
        if (!cancelled) setError(apiErrorMessage(err, 'Failed to load unpriced usage'))
      })
    return () => {
      cancelled = true
    }
  }, [apiKey, days])

  if (compact) {
    const value = error ? '—' : data ? data.unpriced_calls.toLocaleString() : '…'
    const warn = (data?.unpriced_calls ?? 0) > 0
    return (
      <Link
        href="/provider-profiles"
        title="Model calls with no price — add pricing to count their cost"
        className={`block rounded-xl border px-3 py-2 ${warn ? 'border-amber-300 bg-amber-50/80 dark:border-amber-700 dark:bg-amber-950/30' : 'border-slate-200 bg-white/90 dark:border-slate-700 dark:bg-slate-900'}`}
      >
        <p className="text-[10px] uppercase tracking-widest text-slate-400">Unpriced calls ({days}d)</p>
        <p className={`text-sm font-semibold ${warn ? 'text-amber-700 dark:text-amber-300' : 'text-slate-800 dark:text-slate-100'}`}>
          {value}
          {data && data.unpriced_calls > 0 && (
            <span className="ml-1 text-[10px] font-normal">· {data.unpriced_tokens.toLocaleString()} tokens</span>
          )}
        </p>
      </Link>
    )
  }

  if (error) {
    return <p className="text-xs text-rose-600">{error}</p>
  }
  if (!data || data.unpriced_calls === 0) return null

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50/80 p-3 dark:border-amber-700 dark:bg-amber-950/30">
      <p className="text-xs font-semibold text-amber-800 dark:text-amber-200">
        {data.unpriced_calls.toLocaleString()} model calls in the last {data.days} days have no price ({data.unpriced_pct}% of calls,{' '}
        {data.unpriced_tokens.toLocaleString()} tokens)
      </p>
      <p className="mb-2 text-[11px] text-amber-700 dark:text-amber-300">
        Their cost is missing from spend, budgets and chargeback. Add pricing for these models below; existing calls are priced on the next enrichment run.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              {['Provider', 'Model', 'Calls', 'Input tokens', 'Output tokens', 'Last seen'].map((h) => (
                <th key={h} className="px-2 py-1 text-left text-[10px] font-semibold uppercase tracking-widest text-amber-700/70 dark:text-amber-300/70">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.items.map((m) => (
              <tr key={`${m.provider}/${m.model}`} className="border-t border-amber-200/70 dark:border-amber-800/50">
                <td className="px-2 py-1">{m.provider}</td>
                <td className="px-2 py-1 font-mono text-[11px]">{m.model}</td>
                <td className="px-2 py-1 tabular-nums">{m.calls.toLocaleString()}</td>
                <td className="px-2 py-1 tabular-nums">{m.input_tokens.toLocaleString()}</td>
                <td className="px-2 py-1 tabular-nums">{m.output_tokens.toLocaleString()}</td>
                <td className="px-2 py-1">{new Date(m.last_seen).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
