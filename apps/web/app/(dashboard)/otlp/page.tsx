'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { getOtlpStats, listOtlpBatches } from '@/lib/api'
import type { OtlpStats, OtlpBatchList } from '@/types/api'

export default function OtlpPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [otlpStats, setOtlpStats] = useState<OtlpStats | null>(null)
  const [otlpBatches, setOtlpBatches] = useState<OtlpBatchList | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    setLoading(true)
    try {
      const [stats, batches] = await Promise.all([
        getOtlpStats(apiKey),
        listOtlpBatches(apiKey, 20, 0),
      ])
      setOtlpStats(stats)
      setOtlpBatches(batches)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load OTLP data')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManageOrgSettings])

  useEffect(() => { load() }, [load])

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">OTLP Ingestion</h1>
        <p className="mt-4 text-sm text-slate-500">OTLP management is an organization-admin function.</p>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">OTLP Ingestion</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Monitor traces received via <code className="font-mono text-xs bg-gray-100 dark:bg-gray-800 px-1 rounded">POST /v1/traces</code> from any OpenTelemetry-compatible sender.
        </p>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {[
          { label: '24h Batches', value: otlpStats?.last_24h.batches },
          { label: '24h Traces', value: otlpStats?.last_24h.traces },
          { label: '24h Spans', value: otlpStats?.last_24h.spans },
          { label: '7d Batches', value: otlpStats?.last_7d.batches },
          { label: '7d Traces', value: otlpStats?.last_7d.traces },
          { label: '7d Spans', value: otlpStats?.last_7d.spans },
        ].map((stat) => (
          <div key={stat.label} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-center">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
              {loading ? '…' : (stat.value ?? 0).toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Quick-start */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4">
        <p className="text-sm font-medium dark:text-gray-200 mb-2">Quick start</p>
        <pre className="text-xs font-mono bg-gray-900 text-green-400 rounded p-3 overflow-x-auto whitespace-pre-wrap">{`# Install the OTel SDK + RunLedger-compatible exporter
pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

# Set the endpoint + auth header
export OTEL_EXPORTER_OTLP_ENDPOINT=https://YOUR_API/v1/traces
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer YOUR_API_KEY"

# Or send manually with curl
curl -X POST https://YOUR_API/v1/traces \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"resourceSpans": [...]}'`}</pre>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          See <a href="https://github.com/anthropics/runledger/blob/main/docs/otlp.md" className="text-indigo-500 hover:underline" target="_blank" rel="noreferrer">docs/otlp.md</a> for the full integration guide.
        </p>
      </div>

      {/* Batch history */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium dark:text-gray-200">Recent Ingest Batches</h3>
          <button
            onClick={load}
            disabled={loading}
            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
        {loading && !otlpBatches ? (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-8 rounded bg-gray-200 dark:bg-gray-700 animate-pulse" />
            ))}
          </div>
        ) : !otlpBatches || otlpBatches.items.length === 0 ? (
          <div className="rounded border border-dashed border-gray-300 dark:border-gray-600 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
            No batches received yet. Send a trace to get started.
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Time</th>
                  <th className="px-4 py-2 text-right">Traces</th>
                  <th className="px-4 py-2 text-right">Spans</th>
                  <th className="px-4 py-2 text-left">Status</th>
                  <th className="px-4 py-2 text-left">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-900">
                {otlpBatches.items.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">
                      {b.created_at ? new Date(b.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-2 text-right dark:text-gray-300">{b.trace_count}</td>
                    <td className="px-4 py-2 text-right dark:text-gray-300">{b.span_count}</td>
                    <td className="px-4 py-2">
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                        b.status === 'accepted'
                          ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                          : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300'
                      }`}>
                        {b.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs text-red-500 dark:text-red-400 max-w-xs truncate">
                      {b.error ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 py-2 text-xs text-gray-400 dark:text-gray-500 border-t border-gray-100 dark:border-gray-700">
              Showing {otlpBatches.items.length} of {otlpBatches.total} batches
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
