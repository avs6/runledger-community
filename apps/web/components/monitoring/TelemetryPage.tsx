'use client'

import { useSession } from 'next-auth/react'
import { useState, useEffect, useCallback } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { toast } from 'sonner'
import { useRole } from '@/components/rbac/useRole'
import { getOtlpBatchDetail, getOtlpInsights, getOtlpStats, listOtlpBatches } from '@/lib/api'
import type {
  OtlpBatchDetail,
  OtlpBatchList,
  OtlpBatchResponse,
  OtlpInsights,
  OtlpStats,
} from '@/types/api'

const PAGE_SIZE = 20

function formatBatchTime(value: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

export default function TelemetryPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey
  const { canManageOrgSettings } = useRole()

  const [otlpStats, setOtlpStats] = useState<OtlpStats | null>(null)
  const [otlpBatches, setOtlpBatches] = useState<OtlpBatchList | null>(null)
  const [otlpInsights, setOtlpInsights] = useState<OtlpInsights | null>(null)
  const [selectedBatch, setSelectedBatch] = useState<OtlpBatchDetail | null>(null)
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [loadingBatchDetail, setLoadingBatchDetail] = useState(false)

  const load = useCallback(async () => {
    if (!apiKey || !canManageOrgSettings) return
    setLoading(true)
    try {
      const [stats, batches, insights] = await Promise.all([
        getOtlpStats(apiKey),
        listOtlpBatches(apiKey, PAGE_SIZE, offset),
        getOtlpInsights(apiKey),
      ])
      setOtlpStats(stats)
      setOtlpBatches(batches)
      setOtlpInsights(insights)
      if (selectedBatchId && !batches.items.some((item) => item.id === selectedBatchId)) {
        setSelectedBatchId(null)
        setSelectedBatch(null)
      }
    } catch (err) {
      console.error(err)
      toast.error('Failed to load telemetry data')
    } finally {
      setLoading(false)
    }
  }, [apiKey, canManageOrgSettings, offset, selectedBatchId])

  const inspectBatch = useCallback(async (batch: OtlpBatchResponse) => {
    if (!apiKey) return
    setSelectedBatchId(batch.id)
    setLoadingBatchDetail(true)
    try {
      const detail = await getOtlpBatchDetail(apiKey, batch.id)
      setSelectedBatch(detail)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load telemetry batch detail')
    } finally {
      setLoadingBatchDetail(false)
    }
  }, [apiKey])

  useEffect(() => {
    void load()
  }, [load])

  if (!canManageOrgSettings) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Telemetry</h1>
        <p className="mt-4 text-sm text-slate-500">Telemetry management is an organization-admin function.</p>
      </div>
    )
  }

  const hasPreviousPage = offset > 0
  const hasNextPage = Boolean(otlpBatches && offset + otlpBatches.items.length < otlpBatches.total)

  return (
    <div className="space-y-6 p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-600 dark:text-indigo-400">Observability</p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">Telemetry</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Monitor traces, metrics, and logs received via the OTLP/HTTP JSON endpoints from any OpenTelemetry-compatible sender.
        </p>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Use this page to verify ingest health, attribution quality, and batch-level payload shape before telemetry flows into Runs, Request Explorer, and the rest of the observability stack.
        </p>
      </div>

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
          <div key={stat.label} className="rounded-lg border border-gray-200 bg-white p-4 text-center dark:border-gray-700 dark:bg-gray-800">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
              {loading ? '...' : (stat.value ?? 0).toLocaleString()}
            </div>
            <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-3">
            <h3 className="text-sm font-medium dark:text-gray-200">Last 24h Signal Trend</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Hourly counts across traces, metrics, and logs.</p>
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

        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-3">
            <h3 className="text-sm font-medium dark:text-gray-200">Top Instrumented Services</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Most common OTEL `service.name` values in recent resource payloads.</p>
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
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-3">
            <h3 className="text-sm font-medium dark:text-gray-200">Attribution Coverage</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Resource-level semantic coverage across the last 7 days. Workspace attribution is enforced by the workspace API key; these fields improve session, feature, and deployment correlation.
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
              <div key={String(label)} className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                <div className="text-lg font-semibold text-slate-900 dark:text-white">{Number(value ?? 0).toFixed(1)}%</div>
                <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{label}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
            Resource maps analyzed: {(otlpInsights?.window.resource_maps_seen ?? 0).toLocaleString()} · Workspace scope: {otlpInsights?.window.workspace_name_hint ?? 'Current workspace'}
          </div>
        </div>

        <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div>
            <h3 className="text-sm font-medium dark:text-gray-200">Collector Semantics</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Recent semantic dimensions present after collector enrichment.</p>
          </div>
          <div className="space-y-2">
            {(otlpInsights?.semantic_dimensions ?? []).slice(0, 8).map((item) => (
              <div key={item.key} className="flex items-center justify-between rounded-md border border-gray-200 px-3 py-2 text-sm dark:border-gray-700">
                <span className="font-mono text-xs dark:text-gray-300">{item.key}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">{item.resource_count}</span>
              </div>
            ))}
            {(!otlpInsights || otlpInsights.semantic_dimensions.length === 0) && (
              <div className="rounded border border-dashed border-gray-300 px-3 py-6 text-center text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No semantic dimensions detected yet.
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50">
        <p className="mb-2 text-sm font-medium dark:text-gray-200">Quick start</p>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-gray-900 p-3 text-xs font-mono text-green-400">{`# Install the OTel SDK + RunLedger-compatible exporter
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
curl -X POST https://YOUR_API/v1/traces \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans": [...]}'`}</pre>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Full setup guidance lives in Onboarding. Use this page after setup to validate signal health and inspect the exact batches landing in RunLedger.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr,0.7fr]">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium dark:text-gray-200">Recent Ingest Batches</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Paginated batch history for traces, metrics, and logs.</p>
            </div>
            <button
              onClick={() => void load()}
              disabled={loading}
              className="text-xs text-indigo-600 hover:underline disabled:opacity-50 dark:text-indigo-400"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
          {loading && !otlpBatches ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-8 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
              ))}
            </div>
          ) : !otlpBatches || otlpBatches.items.length === 0 ? (
            <div className="rounded border border-dashed border-gray-300 py-8 text-center text-sm text-gray-500 dark:border-gray-600 dark:text-gray-400">
              No batches received yet. Send traces, metrics, or logs to get started.
            </div>
          ) : (
            <div className="overflow-x-auto rounded border border-gray-200 dark:border-gray-700">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                  <tr>
                    <th className="px-4 py-2 text-left">Time</th>
                    <th className="px-4 py-2 text-left">Signal</th>
                    <th className="px-4 py-2 text-right">Traces</th>
                    <th className="px-4 py-2 text-right">Spans</th>
                    <th className="px-4 py-2 text-right">Metrics</th>
                    <th className="px-4 py-2 text-right">Logs</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {otlpBatches.items.map((batch) => (
                    <tr
                      key={batch.id}
                      className={`${selectedBatchId === batch.id ? 'bg-indigo-50 dark:bg-indigo-950/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                    >
                      <td className="px-4 py-2 font-mono text-xs dark:text-gray-300">{formatBatchTime(batch.created_at)}</td>
                      <td className="px-4 py-2 text-xs font-medium uppercase dark:text-gray-300">{batch.signal_type}</td>
                      <td className="px-4 py-2 text-right dark:text-gray-300">{batch.trace_count}</td>
                      <td className="px-4 py-2 text-right dark:text-gray-300">{batch.span_count}</td>
                      <td className="px-4 py-2 text-right dark:text-gray-300">{batch.metric_count}</td>
                      <td className="px-4 py-2 text-right dark:text-gray-300">{batch.log_record_count}</td>
                      <td className="px-4 py-2">
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                          batch.status === 'accepted'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                            : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                        }`}>
                          {batch.status}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          onClick={() => void inspectBatch(batch)}
                          disabled={loadingBatchDetail && selectedBatchId === batch.id}
                          className="rounded border border-slate-300 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                        >
                          {loadingBatchDetail && selectedBatchId === batch.id ? 'Loading...' : 'Inspect'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3 text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
                <div>
                  Showing {offset + 1}-{Math.min(offset + (otlpBatches?.items.length ?? 0), otlpBatches?.total ?? 0)} of {otlpBatches?.total ?? 0} batches
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={!hasPreviousPage || loading}
                    onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
                    className="rounded border border-slate-300 px-3 py-1 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={!hasNextPage || loading}
                    onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                    className="rounded border border-slate-300 px-3 py-1 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="mb-3">
            <h3 className="text-sm font-medium dark:text-gray-200">Batch Drill-In</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Inspect signal mix, resource maps, and raw payload preview for a selected ingest batch.</p>
          </div>
          {!selectedBatch ? (
            <div className="rounded border border-dashed border-gray-300 px-3 py-10 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
              Select a batch from the table to inspect it.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                {[
                  ['Time', formatBatchTime(selectedBatch.created_at)],
                  ['Signal', selectedBatch.signal_type.toUpperCase()],
                  ['Status', selectedBatch.status],
                  ['Content type', selectedBatch.content_type],
                  ['Encoding', selectedBatch.encoding ?? 'none'],
                  ['Payload bytes', selectedBatch.raw_payload_bytes.toLocaleString()],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500 dark:text-gray-400">{label}</div>
                    <div className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{value}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-4 gap-3">
                {[
                  ['Traces', selectedBatch.trace_count],
                  ['Spans', selectedBatch.span_count],
                  ['Metrics', selectedBatch.metric_count],
                  ['Logs', selectedBatch.log_record_count],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-lg border border-gray-200 bg-white p-3 text-center dark:border-gray-700 dark:bg-gray-800/40">
                    <div className="text-lg font-semibold text-slate-900 dark:text-white">{Number(value).toLocaleString()}</div>
                    <div className="text-[11px] uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">{label}</div>
                  </div>
                ))}
              </div>

              {selectedBatch.error && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
                  {selectedBatch.error}
                </div>
              )}

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500 dark:text-gray-400">Resource maps</h4>
                  <span className="text-xs text-gray-500 dark:text-gray-400">{selectedBatch.resource_map_count} detected</span>
                </div>
                <div className="space-y-2">
                  {selectedBatch.resource_maps.length === 0 ? (
                    <div className="rounded border border-dashed border-gray-300 px-3 py-5 text-center text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
                      No resource maps parsed from this batch.
                    </div>
                  ) : (
                    selectedBatch.resource_maps.map((resourceMap, index) => (
                      <div key={`${resourceMap.service_name ?? 'unknown'}-${index}`} className="rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/60">
                        <div className="text-sm font-medium text-slate-900 dark:text-white">{resourceMap.service_name ?? 'Unknown service'}</div>
                        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{resourceMap.attribute_count} attributes</div>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {resourceMap.attribute_keys.map((key) => (
                            <span key={key} className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                              {key}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-gray-500 dark:text-gray-400">Payload preview</h4>
                <pre className="max-h-[26rem] overflow-auto rounded-lg bg-gray-950 p-3 text-xs text-green-300">
                  {selectedBatch.raw_payload_preview ?? 'No payload preview available.'}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
