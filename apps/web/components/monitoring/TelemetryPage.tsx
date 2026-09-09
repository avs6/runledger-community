'use client'

import Link from 'next/link'
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
import { Building2, Network, RefreshCw, Shield } from 'lucide-react'
import { getOtlpBatchDetail, getOtlpInsights, getOtlpStats, getTelemetryOpsPosture, listOtlpBatches } from '@/lib/api'
import type {
  OtlpBatchDetail,
  OtlpBatchList,
  OtlpBatchResponse,
  OtlpInsights,
  OtlpStats,
  TelemetryOpsPosture,
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
  const [opsPosture, setOpsPosture] = useState<TelemetryOpsPosture | null>(null)

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
      toast.error('Failed to load batch detail')
    } finally {
      setLoadingBatchDetail(false)
    }
  }, [apiKey])

  useEffect(() => {
    void load()
    if (apiKey) {
      getTelemetryOpsPosture(apiKey).then(setOpsPosture).catch(() => {})
    }
  }, [load, apiKey])

  if (!canManageOrgSettings) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">Telemetry</h1>
        <p className="mt-1 text-sm text-slate-500">Telemetry management is an organization-admin function.</p>
      </div>
    )
  }

  const hasPreviousPage = offset > 0
  const hasNextPage = Boolean(otlpBatches && offset + otlpBatches.items.length < otlpBatches.total)

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">Telemetry</h1>
          <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">OTLP traces, metrics, logs — ingest health, attribution, and batch inspection.</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { href: '/monitoring', label: 'Monitoring' },
            { href: '/gateway', label: 'Gateway' },
            { href: '/guardrails', label: 'Guardrails' },
            { href: '/alert-rules', label: 'Alerts' },
          ].map(nav => (
            <Link key={nav.label} href={nav.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {nav.label}
            </Link>
          ))}
          <button onClick={() => void load()} disabled={loading}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Posture chips */}
      {opsPosture && (
        <div className="grid gap-2 lg:grid-cols-3">
          <div className="rounded-xl border border-violet-200/60 bg-violet-50/30 p-3 dark:border-violet-800/40 dark:bg-violet-950/20">
            <div className="mb-2 flex items-center gap-1.5">
              <Network className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
              <span className="text-xs font-semibold text-violet-700 dark:text-violet-300">Gateway Context</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { l: 'Routes', v: opsPosture.gateway_context.active_routes },
                { l: 'Models', v: opsPosture.gateway_context.distinct_models },
                { l: 'GW Reqs 30d', v: opsPosture.gateway_context.gateway_requests_30d },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] dark:border-violet-800 dark:bg-violet-950/40">
                  <span className="font-medium text-violet-500 dark:text-violet-400">{c.l}</span>
                  <span className="font-bold text-violet-700 dark:text-violet-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-amber-200/60 bg-amber-50/30 p-3 dark:border-amber-800/40 dark:bg-amber-950/20">
            <div className="mb-2 flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
              <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">Governance</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { l: 'Capture', v: opsPosture.governance_context.capture_policies },
                { l: 'Security 30d', v: opsPosture.governance_context.security_events_30d },
                { l: 'Alerts', v: `${opsPosture.governance_context.active_alert_rules}/${opsPosture.governance_context.alert_rules}` },
                { l: 'Audit 30d', v: opsPosture.governance_context.audit_events_30d },
                { l: 'Approvals', v: opsPosture.governance_context.approvals },
                { l: 'Tags', v: opsPosture.governance_context.tags },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] dark:border-amber-800 dark:bg-amber-950/40">
                  <span className="font-medium text-amber-500 dark:text-amber-400">{c.l}</span>
                  <span className="font-bold text-amber-700 dark:text-amber-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-blue-200/60 bg-blue-50/30 p-3 dark:border-blue-800/40 dark:bg-blue-950/20">
            <div className="mb-2 flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Org & Investigation</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {[
                { l: 'Users', v: opsPosture.org_context.workspace_users },
                { l: 'Batches 30d', v: opsPosture.org_context.telemetry_batches_30d },
                { l: 'Runs 30d', v: opsPosture.investigation_context.runs_30d },
                { l: 'Calls 30d', v: opsPosture.investigation_context.provider_calls_30d },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] dark:border-blue-800 dark:bg-blue-950/40">
                  <span className="font-medium text-blue-500 dark:text-blue-400">{c.l}</span>
                  <span className="font-bold text-blue-700 dark:text-blue-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stats KPI strip */}
      <div className="grid grid-cols-5 gap-2 xl:grid-cols-10">
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
          <div key={stat.label} className="rounded-xl border border-slate-200 bg-white/90 p-2 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <p className="text-base font-bold text-indigo-600 dark:text-indigo-400">
              {loading ? '…' : (stat.value ?? 0).toLocaleString()}
            </p>
            <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="mb-2 text-xs font-semibold text-slate-700 dark:text-slate-300">24h Signal Trend</p>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={otlpInsights?.timeseries_24h ?? []} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                <XAxis dataKey="timestamp" tickFormatter={(v) => new Date(v).toLocaleTimeString([], { hour: 'numeric' })} minTickGap={24} tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
                <Tooltip labelFormatter={(v) => new Date(String(v)).toLocaleString()} />
                <Area type="monotone" dataKey="traces" stackId="1" stroke="#4f46e5" fill="#818cf8" fillOpacity={0.35} />
                <Area type="monotone" dataKey="metrics" stackId="1" stroke="#0f766e" fill="#2dd4bf" fillOpacity={0.3} />
                <Area type="monotone" dataKey="logs" stackId="1" stroke="#b45309" fill="#fbbf24" fillOpacity={0.25} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="mb-2 text-xs font-semibold text-slate-700 dark:text-slate-300">Top Services</p>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={otlpInsights?.top_services ?? []} layout="vertical" margin={{ top: 4, right: 8, left: 16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="service_name" width={100} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="resource_count" fill="#2563eb" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Attribution + Semantics */}
      <div className="grid gap-3 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="mb-2 text-xs font-semibold text-slate-700 dark:text-slate-300">Attribution Coverage (7d)</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ['Service', otlpInsights?.attribute_coverage.service_name_pct],
              ['Session', otlpInsights?.attribute_coverage.session_id_pct],
              ['End user', otlpInsights?.attribute_coverage.end_user_id_pct],
              ['Feature tag', otlpInsights?.attribute_coverage.feature_tag_pct],
              ['Deploy ver', otlpInsights?.attribute_coverage.deployment_version_pct],
              ['Workspace', otlpInsights?.attribute_coverage.workspace_name_pct],
              ['Org', otlpInsights?.attribute_coverage.organization_name_pct],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border border-slate-100 bg-slate-50/60 p-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-sm font-bold text-slate-900 dark:text-white">{Number(value ?? 0).toFixed(1)}%</p>
                <p className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{label}</p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] text-slate-400">
            {(otlpInsights?.window.resource_maps_seen ?? 0).toLocaleString()} resource maps · {otlpInsights?.window.workspace_name_hint ?? 'Current workspace'}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="mb-2 text-xs font-semibold text-slate-700 dark:text-slate-300">Collector Semantics</p>
          <div className="space-y-1">
            {(otlpInsights?.semantic_dimensions ?? []).slice(0, 8).map((item) => (
              <div key={item.key} className="flex items-center justify-between rounded-md border border-slate-100 px-2.5 py-1 text-xs dark:border-slate-700">
                <span className="font-mono text-[11px] text-slate-700 dark:text-slate-300">{item.key}</span>
                <span className="text-[10px] text-slate-400">{item.resource_count}</span>
              </div>
            ))}
            {(!otlpInsights || otlpInsights.semantic_dimensions.length === 0) && (
              <div className="rounded border border-dashed border-slate-300 px-3 py-4 text-center text-[11px] text-slate-400 dark:border-slate-700">
                No semantic dimensions detected yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick start */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-700 dark:bg-slate-800/50">
        <p className="mb-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">Quick start</p>
        <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-2.5 text-[11px] font-mono text-green-400">{`# Install OTel SDK + RunLedger-compatible exporter
pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

# Option A: localhost collector
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer YOUR_API_KEY"

# Option B: direct to RunLedger
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://YOUR_API/v1/traces
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer YOUR_API_KEY"`}</pre>
      </div>

      {/* Batch table — full width */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Recent Ingest Batches</p>
          <button onClick={() => void load()} disabled={loading} className="text-[10px] text-indigo-600 hover:underline disabled:opacity-50 dark:text-indigo-400">
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
        {loading && !otlpBatches ? (
          <div className="space-y-1.5">{[...Array(3)].map((_, i) => <div key={i} className="h-6 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />)}</div>
        ) : !otlpBatches || otlpBatches.items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 py-6 text-center text-xs text-slate-400 dark:border-slate-600">
            No batches received yet. Send traces, metrics, or logs to get started.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
            <table className="w-full text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                  {['Time', 'Signal', 'Traces', 'Spans', 'Metrics', 'Logs', 'Status', ''].map(h => (
                    <th key={h} className="px-3 py-1.5 text-left text-[10px] font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white dark:divide-slate-700 dark:bg-slate-900">
                {otlpBatches.items.map((batch) => (
                  <tr key={batch.id} className={`cursor-pointer ${selectedBatchId === batch.id ? 'bg-indigo-50 dark:bg-indigo-950/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800'}`} onClick={() => void inspectBatch(batch)}>
                    <td className="whitespace-nowrap px-3 py-1.5 font-mono text-slate-500">{formatBatchTime(batch.created_at)}</td>
                    <td className="px-3 py-1.5 font-medium uppercase text-slate-700 dark:text-slate-300">{batch.signal_type}</td>
                    <td className="px-3 py-1.5 text-right text-slate-600 dark:text-slate-300">{batch.trace_count}</td>
                    <td className="px-3 py-1.5 text-right text-slate-600 dark:text-slate-300">{batch.span_count}</td>
                    <td className="px-3 py-1.5 text-right text-slate-600 dark:text-slate-300">{batch.metric_count}</td>
                    <td className="px-3 py-1.5 text-right text-slate-600 dark:text-slate-300">{batch.log_record_count}</td>
                    <td className="px-3 py-1.5">
                      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${
                        batch.status === 'accepted'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300'
                          : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                      }`}>{batch.status}</span>
                    </td>
                    <td className="px-3 py-1.5">
                      <span className="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400">
                        {loadingBatchDetail && selectedBatchId === batch.id ? '…' : 'Inspect'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-[10px] text-slate-400 dark:border-slate-700">
              <span>{offset + 1}–{Math.min(offset + (otlpBatches?.items.length ?? 0), otlpBatches?.total ?? 0)} of {otlpBatches?.total ?? 0}</span>
              <div className="flex gap-1.5">
                <button type="button" disabled={!hasPreviousPage || loading} onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
                  className="rounded border border-slate-300 px-2 py-0.5 font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300">Prev</button>
                <button type="button" disabled={!hasNextPage || loading} onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                  className="rounded border border-slate-300 px-2 py-0.5 font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300">Next</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Drill-in — full width below table */}
      {selectedBatch && (
        <div className="rounded-xl border border-indigo-200/60 bg-white/90 p-4 shadow-sm dark:border-indigo-800/40 dark:bg-slate-900">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Batch Drill-In</p>
            <button onClick={() => { setSelectedBatch(null); setSelectedBatchId(null) }} className="rounded-md px-2 py-0.5 text-[10px] text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800">Close</button>
          </div>

          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 lg:grid-cols-10">
            {[
              ['Time', formatBatchTime(selectedBatch.created_at)],
              ['Signal', selectedBatch.signal_type.toUpperCase()],
              ['Status', selectedBatch.status],
              ['Content', selectedBatch.content_type],
              ['Encoding', selectedBatch.encoding ?? 'none'],
              ['Bytes', selectedBatch.raw_payload_bytes.toLocaleString()],
              ['Traces', selectedBatch.trace_count],
              ['Spans', selectedBatch.span_count],
              ['Metrics', selectedBatch.metric_count],
              ['Logs', selectedBatch.log_record_count],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-lg border border-slate-100 bg-slate-50/60 p-2 text-center dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-sm font-bold text-slate-900 dark:text-white">{typeof value === 'number' ? Number(value).toLocaleString() : value}</p>
                <p className="text-[8px] font-semibold uppercase tracking-widest text-slate-400">{label}</p>
              </div>
            ))}
          </div>

          {selectedBatch.error && (
            <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-[11px] text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
              {selectedBatch.error}
            </div>
          )}

          <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1fr]">
            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">
                Resource maps ({selectedBatch.resource_map_count})
              </p>
              {selectedBatch.resource_maps.length === 0 ? (
                <div className="rounded border border-dashed border-slate-300 px-3 py-4 text-center text-[11px] text-slate-400 dark:border-slate-700">
                  No resource maps parsed.
                </div>
              ) : (
                <div className="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                  {selectedBatch.resource_maps.map((rm, i) => (
                    <div key={`${rm.service_name ?? 'unknown'}-${i}`} className="rounded-lg border border-slate-100 bg-slate-50/60 p-2 dark:border-slate-700 dark:bg-slate-800/60">
                      <p className="text-[11px] font-semibold text-slate-800 dark:text-white">{rm.service_name ?? 'Unknown service'}</p>
                      <p className="text-[10px] text-slate-400">{rm.attribute_count} attributes</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {rm.attribute_keys.map((key) => (
                          <span key={key} className="rounded-full bg-white px-1.5 py-px text-[9px] text-slate-600 dark:bg-slate-900 dark:text-slate-300">{key}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">Payload preview</p>
              <pre className="max-h-60 overflow-auto rounded-lg bg-slate-950 p-2.5 text-[10px] text-green-300">
                {selectedBatch.raw_payload_preview ?? 'No preview available.'}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
