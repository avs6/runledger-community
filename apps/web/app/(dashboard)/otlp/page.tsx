'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { getOtlpInsights, getOtlpStats, listOtlpBatches } from '@/lib/api'
import type { OtlpBatchList, OtlpInsights, OtlpStats } from '@/types/api'

export default function OtlpPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [otlpStats, setOtlpStats] = useState<OtlpStats | null>(null)
  const [otlpBatches, setOtlpBatches] = useState<OtlpBatchList | null>(null)
  const [otlpInsights, setOtlpInsights] = useState<OtlpInsights | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    setLoading(true)
    try {
      const [stats, batches, insights] = await Promise.all([
        getOtlpStats(apiKey),
        listOtlpBatches(apiKey, 20, 0),
        getOtlpInsights(apiKey),
      ])
      setOtlpStats(stats)
      setOtlpBatches(batches)
      setOtlpInsights(insights)
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
          Monitor traces, metrics, and logs received via the OTLP/HTTP JSON endpoints from any OpenTelemetry-compatible sender.
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          The shipped collector can require the same workspace API key used for upstream ingest, and the views below show how much semantic attribution your OTEL resource metadata is carrying into RunLedger.
        </p>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-10">
        {[
          { label: '24h Batches', value: otlpStats?.last_24h.batches },
          { label: '24h Traces', value: otlpStats?.last_24h.traces },
          { label: '24h Spans', value: otlpStats?.last_24h.spans },
          { label: '24h Metrics', value: otlpStats?.last_24h.metrics },
          { label: '24h Logs', value: otlpStats?.last_24h.logs },
          { label: '7d Batches', value: otlpStats?.last_7d.batches },
          { label: '7d Traces', value: otlpStats?.last_7d.traces },
          { label: '7d Spans', value: otlpStats?.last_7d.spans },
          { label: '7d Metrics', value: otlpStats?.last_7d.metrics },
          { label: '7d Logs', value: otlpStats?.last_7d.logs },
        ].map((stat) => (
          <div key={stat.label} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 text-center">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
              {loading ? '…' : (stat.value ?? 0).toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div className="mb-3">
            <h3 className="text-sm font-medium dark:text-gray-200">Last 24h Signal Trend</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">OTLP-derived hourly counts across traces, metrics, and logs.</p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={otlpInsights?.timeseries_24h ?? []} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: 'numeric' })}
                  minTickGap={24}
                />
                <YAxis allowDecimals={false} />
                <Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleString()} />
                <Area type="monotone" dataKey="traces" stackId="1" stroke="#4f46e5" fill="#818cf8" fillOpacity={0.35} />
                <Area type="monotone" dataKey="metrics" stackId="1" stroke="#0f766e" fill="#2dd4bf" fillOpacity={0.3} />
                <Area type="monotone" dataKey="logs" stackId="1" stroke="#b45309" fill="#fbbf24" fillOpacity={0.25} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div className="mb-3">
            <h3 className="text-sm font-medium dark:text-gray-200">Top Instrumented Services</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Most common OTEL `service.name` values observed in recent resource payloads.</p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={otlpInsights?.top_services ?? []} layout="vertical" margin={{ top: 8, right: 12, left: 24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                <XAxis type="number" allowDecimals={false} />
                <YAxis type="category" dataKey="service_name" width={120} />
                <Tooltip />
                <Bar dataKey="resource_count" fill="#2563eb" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr,0.8fr]">
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div className="mb-3">
            <h3 className="text-sm font-medium dark:text-gray-200">Attribution Coverage</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Resource-level semantic coverage across the last 7 days. Workspace attribution is enforced by the workspace API key; the fields below improve session, feature, and deployment correlation.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[
              ['Service', otlpInsights?.attribute_coverage.service_name_pct],
              ['Session', otlpInsights?.attribute_coverage.session_id_pct],
              ['End user', otlpInsights?.attribute_coverage.end_user_id_pct],
              ['Feature tag', otlpInsights?.attribute_coverage.feature_tag_pct],
              ['Deploy version', otlpInsights?.attribute_coverage.deployment_version_pct],
              ['Workspace label', otlpInsights?.attribute_coverage.workspace_name_pct],
              ['Org label', otlpInsights?.attribute_coverage.organization_name_pct],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 p-3">
                <div className="text-lg font-semibold text-slate-900 dark:text-white">{Number(value ?? 0).toFixed(1)}%</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{label}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
            Resource maps analyzed: {(otlpInsights?.window.resource_maps_seen ?? 0).toLocaleString()} · Workspace scope: {otlpInsights?.window.workspace_name_hint ?? 'Current workspace'}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-4">
          <div>
            <h3 className="text-sm font-medium dark:text-gray-200">Collector Semantics</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Recent resource dimensions present after collector enrichment.</p>
          </div>
          <div className="space-y-2">
            {(otlpInsights?.semantic_dimensions ?? []).slice(0, 8).map((item) => (
              <div key={item.key} className="flex items-center justify-between rounded-md border border-gray-200 dark:border-gray-700 px-3 py-2 text-sm">
                <span className="font-mono text-xs dark:text-gray-300">{item.key}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{item.resource_count}</span>
              </div>
            ))}
            {(!otlpInsights || otlpInsights.semantic_dimensions.length === 0) && (
              <div className="rounded border border-dashed border-gray-300 dark:border-gray-700 px-3 py-6 text-center text-xs text-gray-500 dark:text-gray-400">
                No semantic dimensions detected yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick-start */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4">
        <p className="text-sm font-medium dark:text-gray-200 mb-2">Quick start</p>
        <pre className="text-xs font-mono bg-gray-900 text-green-400 rounded p-3 overflow-x-auto whitespace-pre-wrap">{`# Install the OTel SDK + RunLedger-compatible exporter
pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

# Option A: send through the shipped collector on localhost
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer YOUR_API_KEY"

# Option B: send signals directly to RunLedger
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://YOUR_API/v1/traces
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://YOUR_API/v1/metrics
export OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://YOUR_API/v1/logs
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer YOUR_API_KEY"

# Or send a trace batch manually with curl
curl -X POST https://YOUR_API/v1/traces \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"resourceSpans": [...]}'`}</pre>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Full setup guidance also lives in the Integrations and Onboarding flows. The quick start above is enough to verify local OTLP ingestion against this stack.
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
            No batches received yet. Send traces, metrics, or logs to get started.
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Time</th>
                  <th className="px-4 py-2 text-left">Signal</th>
                  <th className="px-4 py-2 text-right">Traces</th>
                  <th className="px-4 py-2 text-right">Spans</th>
                  <th className="px-4 py-2 text-right">Metrics</th>
                  <th className="px-4 py-2 text-right">Logs</th>
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
                    <td className="px-4 py-2 text-xs font-medium uppercase dark:text-gray-300">{b.signal_type}</td>
                    <td className="px-4 py-2 text-right dark:text-gray-300">{b.trace_count}</td>
                    <td className="px-4 py-2 text-right dark:text-gray-300">{b.span_count}</td>
                    <td className="px-4 py-2 text-right dark:text-gray-300">{b.metric_count}</td>
                    <td className="px-4 py-2 text-right dark:text-gray-300">{b.log_record_count}</td>
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
