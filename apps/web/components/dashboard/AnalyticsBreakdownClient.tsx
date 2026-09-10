'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { toast } from 'sonner'
import {
  BarChart2, Users, Layers, TrendingDown, TrendingUp,
  RefreshCw, Download, SlidersHorizontal, ArrowUpRight,
  Zap, Clock, Activity, PieChart as PieIcon,
  GitBranch, Target, Workflow, Grid3x3, Radio,
} from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import {
  getAnalyticsSummary, getSpendOverTime, getSpendByModel,
  getSpendByFeature, getSpendByUser, getRuns,
} from '@/lib/api'
import type {
  AnalyticsSummary, SpendOverTime, SpendByModel,
  SpendByUser, SpendByFeature, RunListItem,
} from '@/types/api'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  RadialBarChart, RadialBar, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'
import { modelColor } from '@/lib/modelColors'

function fmt$(v: string | number) {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '$0.00'
  if (n >= 1000) return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function fmtTokens(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function fmtDuration(ms: number | null | undefined) {
  if (!ms) return '--'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

type Preset = '5m' | '15m' | '30m' | '1h' | '3h' | '6h' | '12h' | '24h' | '7d' | '30d' | '90d'
type SpendGranularity = 'minute' | '5min' | 'hourly' | 'daily'

function presetWindow(p: Preset) {
  const now = new Date()
  const from = new Date(now)
  if (p === '5m') from.setMinutes(from.getMinutes() - 5)
  if (p === '15m') from.setMinutes(from.getMinutes() - 15)
  if (p === '30m') from.setMinutes(from.getMinutes() - 30)
  if (p === '1h') from.setHours(from.getHours() - 1)
  if (p === '3h') from.setHours(from.getHours() - 3)
  if (p === '6h') from.setHours(from.getHours() - 6)
  if (p === '12h') from.setHours(from.getHours() - 12)
  if (p === '24h') from.setHours(from.getHours() - 24)
  if (p === '7d') from.setDate(from.getDate() - 7)
  if (p === '30d') from.setDate(from.getDate() - 30)
  if (p === '90d') from.setDate(from.getDate() - 90)
  return { from: from.toISOString(), to: now.toISOString() }
}

function presetGranularity(p: Preset): SpendGranularity {
  if (['5m', '15m', '30m', '1h'].includes(p)) return 'minute'
  if (['3h', '6h', '12h'].includes(p)) return '5min'
  if (p === '24h') return 'hourly'
  return 'daily'
}

function presetSubtitle(p: Preset, granularity: SpendGranularity) {
  const labels: Record<SpendGranularity, string> = {
    minute: 'Minute',
    '5min': '5-minute',
    hourly: 'Hourly',
    daily: 'Daily',
  }
  return `${labels[granularity]} - last ${p}`
}

const kpiColorMap: Record<string, { border: string; bg: string }> = {
  teal: { border: 'border-teal-200/60 dark:border-teal-800/40', bg: 'bg-teal-50/50 dark:bg-teal-950/20' },
  violet: { border: 'border-violet-200/60 dark:border-violet-800/40', bg: 'bg-violet-50/50 dark:bg-violet-950/20' },
  blue: { border: 'border-blue-200/60 dark:border-blue-800/40', bg: 'bg-blue-50/50 dark:bg-blue-950/20' },
  cyan: { border: 'border-cyan-200/60 dark:border-cyan-800/40', bg: 'bg-cyan-50/50 dark:bg-cyan-950/20' },
  amber: { border: 'border-amber-200/60 dark:border-amber-800/40', bg: 'bg-amber-50/50 dark:bg-amber-950/20' },
  emerald: { border: 'border-emerald-200/60 dark:border-emerald-800/40', bg: 'bg-emerald-50/50 dark:bg-emerald-950/20' },
}

function KpiStrip({ summary, prev }: { summary: AnalyticsSummary; prev?: AnalyticsSummary }) {
  const totalTokens = summary.total_input_tokens + summary.total_output_tokens
  const delta = summary.cost_delta_pct !== null ? parseFloat(summary.cost_delta_pct ?? '0') : null
  const avgCost = summary.run_count > 0 ? parseFloat(summary.total_cost_usd) / summary.run_count : 0
  const ioRatio = summary.total_output_tokens > 0 ? (summary.total_input_tokens / summary.total_output_tokens).toFixed(1) : '--'

  const cards = [
    {
      label: 'Total Spend',
      value: fmt$(summary.total_cost_usd),
      delta,
      sub: prev ? `prev: ${fmt$(prev.total_cost_usd)}` : undefined,
      color: 'teal',
    },
    { label: 'Runs', value: summary.run_count.toLocaleString(), color: 'violet', sub: `${summary.call_count.toLocaleString()} LLM calls` },
    { label: 'Tokens', value: fmtTokens(totalTokens), color: 'blue', sub: `I/O ratio: ${ioRatio}:1` },
    { label: 'Avg Cost/Run', value: fmt$(avgCost), color: 'cyan' },
    { label: 'LLM Calls', value: summary.call_count.toLocaleString(), color: 'amber' },
    { label: 'Input Tokens', value: fmtTokens(summary.total_input_tokens), color: 'emerald', sub: `${fmtTokens(summary.total_output_tokens)} output` },
  ]

  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-3 xl:grid-cols-6">
      {cards.map(c => {
        const cm = kpiColorMap[c.color] ?? kpiColorMap.blue
        return (
          <div key={c.label} className={`rounded-xl border ${cm.border} ${cm.bg} p-3`}>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">{c.label}</p>
            <p className="mt-1 text-xl font-bold text-slate-900 dark:text-white">{c.value}</p>
            {c.sub && <p className="mt-0.5 text-[10px] text-slate-400">{c.sub}</p>}
            {'delta' in c && c.delta !== undefined && c.delta !== null && (
              <div className={`mt-1 flex items-center gap-1 text-[10px] font-medium ${c.delta >= 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                {c.delta >= 0 ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
                {c.delta >= 0 ? '+' : ''}{c.delta.toFixed(1)}%
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function SpendChart({ data }: { data: SpendOverTime }) {
  const formatter = new Intl.DateTimeFormat(
    undefined,
    data.granularity === 'daily'
      ? { month: 'short', day: 'numeric' }
      : { hour: 'numeric', minute: '2-digit' },
  )
  const points = data.points.map(p => ({
    date: formatter.format(new Date(p.period)),
    cost: parseFloat(p.cost_usd),
    calls: p.call_count,
    input: p.input_tokens,
    output: p.output_tokens,
  }))
  if (points.length === 0) return <EmptyState label="No spend data for this period" />
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0d9488" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-700" />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} />
        <YAxis yAxisId="cost" tick={{ fontSize: 10, fill: '#94a3b8' }} tickFormatter={v => `$${v}`} />
        <YAxis yAxisId="calls" orientation="right" tick={{ fontSize: 10, fill: '#94a3b8' }} />
        <Tooltip
          contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }}
          formatter={(v: unknown, name: unknown) => { const n = Number(v); return [String(name) === 'cost' ? `$${n.toFixed(4)}` : n.toLocaleString(), String(name) === 'cost' ? 'Cost' : 'LLM Calls'] }}
        />
        <Area yAxisId="cost" type="monotone" dataKey="cost" stroke="#0d9488" strokeWidth={2} fill="url(#g1)" />
        <Area yAxisId="calls" type="monotone" dataKey="calls" stroke="#7c3aed" strokeWidth={1.5} fill="url(#g2)" strokeDasharray="4 2" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function TokenChart({ data }: { data: SpendOverTime }) {
  const formatter = new Intl.DateTimeFormat(
    undefined,
    data.granularity === 'daily'
      ? { month: 'short', day: 'numeric' }
      : { hour: 'numeric', minute: '2-digit' },
  )
  const points = data.points.map(p => ({
    date: formatter.format(new Date(p.period)),
    input: p.input_tokens,
    output: p.output_tokens,
  }))
  if (points.length === 0) return <EmptyState label="No token data" />
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-700" />
        <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#94a3b8' }} />
        <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} tickFormatter={v => fmtTokens(v)} />
        <Tooltip
          contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }}
          formatter={(v: unknown, name: unknown) => [fmtTokens(Number(v)), String(name) === 'input' ? 'Input Tokens' : 'Output Tokens']}
        />
        <Bar dataKey="input" stackId="tok" fill="#2563eb" radius={[0, 0, 0, 0]} />
        <Bar dataKey="output" stackId="tok" fill="#06b6d4" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function ModelChart({ data }: { data: SpendByModel }) {
  if (data.items.length === 0) return <EmptyState label="No model data" />
  const pie = data.items.map(m => ({
    name: m.model,
    provider: m.provider,
    value: parseFloat(m.cost_usd),
    tokens: m.input_tokens + m.output_tokens,
    calls: m.call_count,
    color: modelColor(m.model),
  }))
  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={pie}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={85}
            paddingAngle={2}
            label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
            labelLine={false}
            style={{ fontSize: 10, fill: '#94a3b8' }}
          >
            {pie.map((entry, i) => <Cell key={i} fill={entry.color} stroke="none" />)}
          </Pie>
          <Tooltip
            contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }}
            formatter={(v: unknown) => fmt$(Number(v))}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-1.5">
        {pie.map((entry, i) => (
          <span key={i} className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
            {entry.name}
          </span>
        ))}
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-100 text-slate-400 dark:border-slate-700 dark:text-slate-500">
            <th className="pb-1.5 text-left font-medium">Model</th>
            <th className="pb-1.5 text-right font-medium">Cost</th>
            <th className="pb-1.5 text-right font-medium">Tokens</th>
            <th className="pb-1.5 text-right font-medium">Calls</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
          {data.items.map((m, i) => (
            <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
              <td className="flex items-center gap-1.5 py-1.5 font-mono text-slate-800 dark:text-slate-200">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: modelColor(m.model) }} />
                {m.model}
              </td>
              <td className="py-1.5 text-right font-medium text-slate-700 dark:text-slate-300">{fmt$(m.cost_usd)}</td>
              <td className="py-1.5 text-right text-slate-400 dark:text-slate-500">{fmtTokens(m.input_tokens + m.output_tokens)}</td>
              <td className="py-1.5 text-right text-slate-400 dark:text-slate-500">{m.call_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ModelCostBars({ data }: { data: SpendByModel }) {
  if (data.items.length === 0) return <EmptyState label="No model data" />
  const bars = data.items.map(m => ({
    name: m.model,
    cost: parseFloat(m.cost_usd),
    input: m.input_tokens,
    output: m.output_tokens,
    color: modelColor(m.model),
  }))
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, bars.length * 32)}>
      <BarChart data={bars} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="currentColor" className="text-slate-200 dark:text-slate-700" />
        <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} tickFormatter={v => `$${v}`} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} width={120} />
        <Tooltip
          contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }}
          formatter={(v: unknown) => [fmt$(Number(v)), 'Cost']}
        />
        <Bar dataKey="cost" radius={[0, 6, 6, 0]}>
          {bars.map((entry, i) => <Cell key={i} fill={entry.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function FeatureChart({ data }: { data: SpendByFeature }) {
  if (data.items.length === 0) return <EmptyState label="No feature data" />
  const bars = data.items
    .filter(f => f.feature_tag)
    .map(f => ({ name: f.feature_tag!, cost: parseFloat(f.cost_usd), runs: f.run_count }))
  return (
    <ResponsiveContainer width="100%" height={Math.max(160, bars.length * 28)}>
      <BarChart data={bars} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="currentColor" className="text-slate-200 dark:text-slate-700" />
        <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} tickFormatter={v => `$${v}`} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#94a3b8' }} width={120} />
        <Tooltip
          contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }}
          formatter={(v: unknown, name: unknown) => [String(name) === 'cost' ? fmt$(Number(v)) : Number(v).toLocaleString(), String(name) === 'cost' ? 'Cost' : 'Runs']}
        />
        <Bar dataKey="cost" fill="#7c3aed" radius={[0, 6, 6, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function LiveActivityBar({ runs }: { runs: RunListItem[] }) {
  const sorted = [...runs]
    .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime())
    .slice(-80)
  const models = Array.from(new Set(sorted.map(r => r.primary_model).filter(Boolean) as string[]))

  if (sorted.length === 0) {
    return <div className="flex h-full w-full items-center justify-center text-sm text-slate-500">No activity in this window.</div>
  }

  return (
    <div>
      <div className="flex h-36 items-end gap-[3px] rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-950/50">
        {sorted.map(run => {
          const tokenCount = (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)
          const height = Math.max(12, Math.min(120, 12 + tokenCount / 50))
          const failed = run.status === 'failed' || run.status === 'cancelled'
          return (
            <Link
              key={run.id}
              href={`/runs/${run.id}`}
              title={`${run.primary_model ?? 'Unknown'} / ${run.feature_tag ?? 'untagged'} / ${run.status}`}
              className="min-w-[4px] flex-1 rounded-t-sm transition hover:opacity-70"
              style={{
                height,
                background: failed
                  ? 'linear-gradient(180deg, #ef4444, #ef444499)'
                  : `linear-gradient(180deg, ${modelColor(run.primary_model)}, ${modelColor(run.primary_model)}88)`,
              }}
            />
          )
        })}
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {models.slice(0, 12).map(model => (
          <span key={model} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: modelColor(model) }} />
            {model}
          </span>
        ))}
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-600 dark:bg-red-950/30 dark:text-red-400">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          Failed
        </span>
      </div>
    </div>
  )
}

function StatusDonut({ runs }: { runs: RunListItem[] }) {
  const succeeded = runs.filter(r => r.status === 'succeeded').length
  const failed = runs.filter(r => r.status === 'failed').length
  const running = runs.filter(r => r.status === 'running').length
  const cancelled = runs.filter(r => r.status === 'cancelled').length
  const total = runs.length
  if (total === 0) return <EmptyState label="No runs" />

  const pie = [
    { name: 'Succeeded', value: succeeded, color: '#22c55e' },
    { name: 'Failed', value: failed, color: '#ef4444' },
    { name: 'Running', value: running, color: '#3b82f6' },
    { name: 'Cancelled', value: cancelled, color: '#94a3b8' },
  ].filter(s => s.value > 0)

  const successRate = total > 0 ? Math.round((succeeded / total) * 100) : 0

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <ResponsiveContainer width={180} height={180}>
          <PieChart>
            <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={75} paddingAngle={2} stroke="none">
              {pie.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-slate-900 dark:text-white">{successRate}%</span>
          <span className="text-[10px] text-slate-400">success</span>
        </div>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {pie.map(s => (
          <span key={s.name} className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-500 dark:text-slate-400">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
            {s.name} ({s.value})
          </span>
        ))}
      </div>
    </div>
  )
}

function LatencyDistribution({ runs }: { runs: RunListItem[] }) {
  const durations = runs.map(r => r.duration_ms).filter((d): d is number => d != null && d > 0)
  if (durations.length === 0) return <EmptyState label="No latency data" />

  const buckets = [
    { label: '<250ms', min: 0, max: 250 },
    { label: '250-500ms', min: 250, max: 500 },
    { label: '500ms-1s', min: 500, max: 1000 },
    { label: '1-2s', min: 1000, max: 2000 },
    { label: '2-5s', min: 2000, max: 5000 },
    { label: '5s+', min: 5000, max: Infinity },
  ]

  const data = buckets.map(b => ({
    name: b.label,
    count: durations.filter(d => d >= b.min && d < b.max).length,
  }))

  const p50 = durations.sort((a, b) => a - b)[Math.floor(durations.length * 0.5)]
  const p95 = durations.sort((a, b) => a - b)[Math.floor(durations.length * 0.95)]
  const p99 = durations.sort((a, b) => a - b)[Math.floor(durations.length * 0.99)]

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-700" />
          <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#94a3b8' }} />
          <YAxis tick={{ fontSize: 9, fill: '#94a3b8' }} />
          <Tooltip
            contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }}
          />
          <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-4 text-[10px]">
        <span className="text-slate-400">P50: <span className="font-bold text-slate-700 dark:text-slate-200">{fmtDuration(p50)}</span></span>
        <span className="text-slate-400">P95: <span className="font-bold text-amber-600 dark:text-amber-400">{fmtDuration(p95)}</span></span>
        <span className="text-slate-400">P99: <span className="font-bold text-red-600 dark:text-red-400">{fmtDuration(p99)}</span></span>
      </div>
    </div>
  )
}

function UserTable({ data }: { data: SpendByUser }) {
  if (data.items.length === 0) return <EmptyState label="No user data for this period" />
  return (
    <table className="w-full text-sm">
      <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
        <tr>
          <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">User</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Spend</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Runs</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Avg/Run</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Calls</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Last Active</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
        {data.items.map((u, i) => (
          <tr key={i} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40">
            <td className="px-4 py-2.5 font-mono text-sm font-medium dark:text-slate-200">{u.end_user_id}</td>
            <td className="px-4 py-2.5 text-right font-mono font-semibold text-violet-700 dark:text-violet-400">{fmt$(u.cost_usd)}</td>
            <td className="px-4 py-2.5 text-right text-slate-500">{u.run_count}</td>
            <td className="px-4 py-2.5 text-right text-slate-500">{fmt$(u.avg_cost_per_run)}</td>
            <td className="px-4 py-2.5 text-right text-slate-500">{u.call_count}</td>
            <td className="px-4 py-2.5 text-right text-xs text-slate-400">
              {u.last_active ? new Date(u.last_active).toLocaleDateString() : '—'}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/* ── Activity Heatmap: runs by hour × day of week ── */
function ActivityHeatmap({ runs }: { runs: RunListItem[] }) {
  if (runs.length === 0) return <EmptyState label="No activity data" />
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const hours = Array.from({ length: 24 }, (_, i) => i)
  const grid: number[][] = days.map(() => hours.map(() => 0))

  for (const r of runs) {
    const d = new Date(r.started_at)
    grid[d.getDay()][d.getHours()]++
  }

  const max = Math.max(1, ...grid.flat())

  function cellColor(v: number) {
    if (v === 0) return 'rgba(100,116,139,0.06)'
    const t = v / max
    if (t < 0.25) return 'rgba(34,197,94,0.25)'
    if (t < 0.5) return 'rgba(34,197,94,0.5)'
    if (t < 0.75) return 'rgba(34,197,94,0.75)'
    return 'rgba(34,197,94,1)'
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-start gap-1">
        <div className="flex w-8 shrink-0 flex-col gap-[3px] pt-5">
          {days.map(d => <div key={d} className="flex h-[18px] items-center text-[9px] text-slate-400">{d}</div>)}
        </div>
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-[2px]">
            {hours.map(h => (
              <div key={h} className="flex flex-col items-center gap-[3px]">
                <span className="text-[8px] text-slate-400">{h.toString().padStart(2, '0')}</span>
                {days.map((_, di) => (
                  <div
                    key={di}
                    title={`${days[di]} ${h}:00 — ${grid[di][h]} runs`}
                    className="h-[18px] w-[18px] rounded-[3px] transition-colors"
                    style={{ backgroundColor: cellColor(grid[di][h]) }}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="flex items-center justify-end gap-1.5 text-[9px] text-slate-400">
        <span>Less</span>
        {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
          <div key={i} className="h-3 w-3 rounded-[2px]" style={{ backgroundColor: cellColor(t * max) }} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}

/* ── Radar: model comparison across normalized dimensions ── */
function ModelRadar({ data, runs }: { data: SpendByModel; runs: RunListItem[] }) {
  if (data.items.length === 0) return <EmptyState label="No model data" />
  const top = data.items.slice(0, 6)
  const maxCost = Math.max(1, ...top.map(m => parseFloat(m.cost_usd)))
  const maxTokens = Math.max(1, ...top.map(m => m.input_tokens + m.output_tokens))
  const maxCalls = Math.max(1, ...top.map(m => m.call_count))
  const maxInput = Math.max(1, ...top.map(m => m.input_tokens))
  const maxOutput = Math.max(1, ...top.map(m => m.output_tokens))

  const modelRuns: Record<string, number[]> = {}
  for (const r of runs) {
    if (!r.primary_model || !r.duration_ms) continue
    const key = r.primary_model.toLowerCase()
    if (!modelRuns[key]) modelRuns[key] = []
    modelRuns[key].push(r.duration_ms)
  }

  const radarData = [
    { axis: 'Cost', ...Object.fromEntries(top.map(m => [m.model, Math.round((parseFloat(m.cost_usd) / maxCost) * 100)])) },
    { axis: 'Tokens', ...Object.fromEntries(top.map(m => [m.model, Math.round(((m.input_tokens + m.output_tokens) / maxTokens) * 100)])) },
    { axis: 'Calls', ...Object.fromEntries(top.map(m => [m.model, Math.round((m.call_count / maxCalls) * 100)])) },
    { axis: 'Input', ...Object.fromEntries(top.map(m => [m.model, Math.round((m.input_tokens / maxInput) * 100)])) },
    { axis: 'Output', ...Object.fromEntries(top.map(m => [m.model, Math.round((m.output_tokens / maxOutput) * 100)])) },
    { axis: 'Speed', ...Object.fromEntries(top.map(m => {
      const durations = modelRuns[m.model.toLowerCase()] ?? []
      const avg = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 5000
      return [m.model, Math.round(Math.max(0, (1 - avg / 10000)) * 100)]
    })) },
  ]

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
          <PolarGrid stroke="#475569" strokeOpacity={0.2} />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 10, fill: '#94a3b8' }} />
          <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 100]} />
          {top.map(m => (
            <Radar key={m.model} name={m.model} dataKey={m.model} stroke={modelColor(m.model)} fill={modelColor(m.model)} fillOpacity={0.12} strokeWidth={2} />
          ))}
          <Tooltip contentStyle={{ backgroundColor: 'rgba(15,23,42,0.95)', border: '1px solid rgba(100,116,139,0.3)', borderRadius: '10px', fontSize: '11px', color: '#e2e8f0' }} />
        </RadarChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap justify-center gap-1.5">
        {top.map(m => (
          <span key={m.model} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: modelColor(m.model) }} />
            {m.model}
          </span>
        ))}
      </div>
    </div>
  )
}

/* ── Sankey: Model → Feature cost flow (pure SVG) ── */
function SankeyChart({ modelData, featureData, runs }: { modelData: SpendByModel; featureData: SpendByFeature; runs: RunListItem[] }) {
  const models = modelData.items.slice(0, 6)
  const features = featureData.items.filter(f => f.feature_tag).slice(0, 6)
  if (models.length === 0 || features.length === 0) return <EmptyState label="Need model + feature data for flow" />

  const flowMap: Record<string, Record<string, number>> = {}
  for (const r of runs) {
    const m = r.primary_model ?? 'unknown'
    const f = r.feature_tag ?? 'untagged'
    if (!flowMap[m]) flowMap[m] = {}
    flowMap[m][f] = (flowMap[m][f] ?? 0) + parseFloat(r.total_cost_usd ?? '0')
  }

  const modelNames = models.map(m => m.model)
  const featureNames = features.map(f => f.feature_tag!)

  const totalModelCost = Object.fromEntries(modelNames.map(m => [m, models.find(x => x.model === m)!].map(x => typeof x === 'string' ? x : parseFloat(x.cost_usd)))) as Record<string, number>
  for (const m of models) totalModelCost[m.model] = parseFloat(m.cost_usd)
  const totalFeatureCost: Record<string, number> = {}
  for (const f of features) totalFeatureCost[f.feature_tag!] = parseFloat(f.cost_usd)

  const maxLeftTotal = Math.max(1, ...Object.values(totalModelCost))
  const maxRightTotal = Math.max(1, ...Object.values(totalFeatureCost))

  const W = 700, H = 320, padY = 16, nodeW = 12, gapLeft = 6, gapRight = 6
  const leftUsable = H - padY * 2 - gapLeft * (modelNames.length - 1)
  const rightUsable = H - padY * 2 - gapRight * (featureNames.length - 1)
  const leftTotal = Object.values(totalModelCost).reduce((a, b) => a + b, 0)
  const rightTotal = Object.values(totalFeatureCost).reduce((a, b) => a + b, 0)

  const leftNodes: { name: string; y: number; h: number; color: string }[] = []
  let ly = padY
  for (const name of modelNames) {
    const h = Math.max(8, (totalModelCost[name] / leftTotal) * leftUsable)
    leftNodes.push({ name, y: ly, h, color: modelColor(name) })
    ly += h + gapLeft
  }

  const rightNodes: { name: string; y: number; h: number }[] = []
  let ry = padY
  for (const name of featureNames) {
    const h = Math.max(8, (totalFeatureCost[name] / rightTotal) * rightUsable)
    rightNodes.push({ name, y: ry, h })
    ry += h + gapRight
  }

  type Flow = { from: string; to: string; value: number }
  const flows: Flow[] = []
  for (const m of modelNames) {
    for (const f of featureNames) {
      const v = flowMap[m]?.[f]
      if (v && v > 0.0001) flows.push({ from: m, to: f, value: v })
    }
  }

  const leftOffsets: Record<string, number> = Object.fromEntries(leftNodes.map(n => [n.name, 0]))
  const rightOffsets: Record<string, number> = Object.fromEntries(rightNodes.map(n => [n.name, 0]))

  const paths = flows.map(f => {
    const ln = leftNodes.find(n => n.name === f.from)!
    const rn = rightNodes.find(n => n.name === f.to)!
    const lFrac = f.value / totalModelCost[f.from]
    const rFrac = f.value / totalFeatureCost[f.to]
    const lh = lFrac * ln.h
    const rh = rFrac * rn.h

    const y0 = ln.y + leftOffsets[f.from]
    const y1 = rn.y + rightOffsets[f.to]
    leftOffsets[f.from] += lh
    rightOffsets[f.to] += rh

    const x0 = 140 + nodeW
    const x1 = W - 140
    return { d: `M${x0},${y0} C${(x0 + x1) / 2},${y0} ${(x0 + x1) / 2},${y1} ${x1},${y1} L${x1},${y1 + rh} C${(x0 + x1) / 2},${y1 + rh} ${(x0 + x1) / 2},${y0 + lh} ${x0},${y0 + lh} Z`, color: modelColor(f.from), value: f.value, from: f.from, to: f.to }
  })

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 320 }}>
      {paths.map((p, i) => (
        <path key={i} d={p.d} fill={p.color} fillOpacity={0.25} stroke={p.color} strokeWidth={0.5} strokeOpacity={0.4}>
          <title>{p.from} → {p.to}: {fmt$(p.value)}</title>
        </path>
      ))}
      {leftNodes.map(n => (
        <g key={`l-${n.name}`}>
          <rect x={140} y={n.y} width={nodeW} height={n.h} rx={3} fill={n.color} />
          <text x={136} y={n.y + n.h / 2} textAnchor="end" dominantBaseline="central" fontSize={10} fill="#94a3b8">{n.name}</text>
        </g>
      ))}
      {rightNodes.map(n => (
        <g key={`r-${n.name}`}>
          <rect x={W - 140} y={n.y} width={nodeW} height={n.h} rx={3} fill="#7c3aed" />
          <text x={W - 140 + nodeW + 4} y={n.y + n.h / 2} dominantBaseline="central" fontSize={10} fill="#94a3b8">{n.name}</text>
        </g>
      ))}
    </svg>
  )
}

/* ── Parallel Coordinates: model dimensions ── */
function ParallelCoordinates({ data, runs }: { data: SpendByModel; runs: RunListItem[] }) {
  const top = data.items.slice(0, 8)
  if (top.length === 0) return <EmptyState label="No model data" />

  const modelDurations: Record<string, number[]> = {}
  for (const r of runs) {
    if (!r.primary_model || !r.duration_ms) continue
    const key = r.primary_model.toLowerCase()
    if (!modelDurations[key]) modelDurations[key] = []
    modelDurations[key].push(r.duration_ms)
  }

  const axes = ['Cost', 'Input Tokens', 'Output Tokens', 'Calls', 'Avg Latency']
  const rawValues = top.map(m => {
    const durations = modelDurations[m.model.toLowerCase()] ?? []
    const avgLat = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0
    return [parseFloat(m.cost_usd), m.input_tokens, m.output_tokens, m.call_count, avgLat]
  })

  const mins = axes.map((_, ai) => Math.min(...rawValues.map(v => v[ai])))
  const maxs = axes.map((_, ai) => Math.max(...rawValues.map(v => v[ai])))

  const W = 700, H = 260, padX = 60, padY = 30
  const axisSpacing = (W - padX * 2) / (axes.length - 1)

  function norm(val: number, ai: number) {
    const range = maxs[ai] - mins[ai]
    if (range === 0) return 0.5
    return (val - mins[ai]) / range
  }

  function yPos(normalized: number) {
    return padY + (1 - normalized) * (H - padY * 2)
  }

  const formatAxis = (ai: number, val: number) => {
    if (ai === 0) return fmt$(val)
    if (ai === 4) return fmtDuration(val)
    return fmtTokens(val)
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 260 }}>
      {axes.map((label, ai) => {
        const x = padX + ai * axisSpacing
        return (
          <g key={label}>
            <line x1={x} y1={padY} x2={x} y2={H - padY} stroke="#475569" strokeWidth={1} strokeOpacity={0.3} />
            <text x={x} y={padY - 8} textAnchor="middle" fontSize={9} fill="#94a3b8">{label}</text>
            <text x={x} y={H - padY + 14} textAnchor="middle" fontSize={8} fill="#64748b">{formatAxis(ai, maxs[ai])}</text>
            <text x={x} y={H - 4} textAnchor="middle" fontSize={8} fill="#64748b">{formatAxis(ai, mins[ai])}</text>
          </g>
        )
      })}
      {top.map((m, mi) => {
        const points = rawValues[mi].map((v, ai) => {
          const x = padX + ai * axisSpacing
          const y = yPos(norm(v, ai))
          return `${x},${y}`
        }).join(' ')
        return (
          <polyline key={m.model} points={points} fill="none" stroke={modelColor(m.model)} strokeWidth={2} strokeOpacity={0.7}>
            <title>{m.model}</title>
          </polyline>
        )
      })}
      {top.map((m, mi) =>
        rawValues[mi].map((v, ai) => {
          const x = padX + ai * axisSpacing
          const y = yPos(norm(v, ai))
          return <circle key={`${mi}-${ai}`} cx={x} cy={y} r={3} fill={modelColor(m.model)} stroke="white" strokeWidth={1}>
            <title>{m.model}: {formatAxis(ai, v)}</title>
          </circle>
        }),
      )}
    </svg>
  )
}

/* ── Ridge Plot: latency distributions per model ── */
function RidgePlot({ runs }: { runs: RunListItem[] }) {
  const modelDurations: Record<string, number[]> = {}
  for (const r of runs) {
    if (!r.primary_model || !r.duration_ms) continue
    const key = r.primary_model
    if (!modelDurations[key]) modelDurations[key] = []
    modelDurations[key].push(r.duration_ms)
  }

  const models = Object.entries(modelDurations)
    .filter(([, d]) => d.length >= 3)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 6)

  if (models.length === 0) return <EmptyState label="Need 3+ runs per model for ridge plot" />

  const allDurations = models.flatMap(([, d]) => d)
  const globalMax = Math.max(...allDurations)
  const bucketCount = 30
  const bucketSize = Math.max(1, globalMax / bucketCount)

  function buildDensity(durations: number[]) {
    const counts = Array(bucketCount).fill(0)
    for (const d of durations) {
      const idx = Math.min(bucketCount - 1, Math.floor(d / bucketSize))
      counts[idx]++
    }
    const maxCount = Math.max(1, ...counts)
    return counts.map(c => c / maxCount)
  }

  const W = 700, rowH = 50, padX = 100, padTop = 10
  const H = padTop + models.length * rowH + 20

  return (
    <div className="space-y-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: Math.max(200, H) }}>
        {models.map(([model, durations], mi) => {
          const density = buildDensity(durations)
          const baseY = padTop + mi * rowH + rowH
          const areaW = W - padX - 20
          const points = density.map((d, i) => {
            const x = padX + (i / bucketCount) * areaW
            const y = baseY - d * (rowH - 8)
            return `${x},${y}`
          })
          const pathD = `M${padX},${baseY} L${points.join(' L')} L${padX + areaW},${baseY} Z`
          return (
            <g key={model}>
              <line x1={padX} y1={baseY} x2={W - 20} y2={baseY} stroke="#475569" strokeWidth={0.5} strokeOpacity={0.2} />
              <path d={pathD} fill={modelColor(model)} fillOpacity={0.35} stroke={modelColor(model)} strokeWidth={1.5} />
              <text x={padX - 6} y={baseY - rowH / 3} textAnchor="end" fontSize={10} fill="#94a3b8">{model}</text>
            </g>
          )
        })}
        {Array.from({ length: 6 }, (_, i) => {
          const v = (i / 5) * globalMax
          const x = padX + (i / 5) * (W - padX - 20)
          return (
            <text key={i} x={x} y={H - 4} textAnchor="middle" fontSize={8} fill="#64748b">{fmtDuration(v)}</text>
          )
        })}
      </svg>
      <div className="flex flex-wrap justify-center gap-1.5">
        {models.map(([model]) => (
          <span key={model} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: modelColor(model) }} />
            {model}
          </span>
        ))}
      </div>
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-slate-400 dark:text-slate-500">{label}</div>
  )
}

function Card({ title, sub, icon: Icon, children, action }: {
  title: string; sub?: string; icon?: React.ElementType; children: React.ReactNode; action?: React.ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-start justify-between border-b border-slate-100 px-5 py-3 dark:border-slate-800">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="h-4 w-4 text-blue-500 dark:text-blue-400" />}
          <div>
            <p className="text-sm font-semibold text-slate-900 dark:text-white">{title}</p>
            {sub && <p className="mt-0.5 text-[10px] text-slate-400">{sub}</p>}
          </div>
        </div>
        {action}
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  )
}

export default function AnalyticsBreakdownClient({ embedded }: { embedded?: boolean } = {}) {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey

  const [preset, setPreset] = useState<Preset>('24h')
  const [loading, setLoading] = useState(true)

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [spendTime, setSpendTime] = useState<SpendOverTime | null>(null)
  const [byModel, setByModel] = useState<SpendByModel | null>(null)
  const [byFeature, setByFeature] = useState<SpendByFeature | null>(null)
  const [byUser, setByUser] = useState<SpendByUser | null>(null)
  const [recentRuns, setRecentRuns] = useState<RunListItem[]>([])

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    const win = presetWindow(preset)
    const gran = presetGranularity(preset)
    try {
      const [s, t, m, f, u, runs] = await Promise.all([
        getAnalyticsSummary(apiKey, win),
        getSpendOverTime(apiKey, gran, win),
        getSpendByModel(apiKey, win),
        getSpendByFeature(apiKey, win),
        getSpendByUser(apiKey, 20, win),
        getRuns(apiKey, { limit: 80, from: win.from, to: win.to }),
      ])
      setSummary(s)
      setSpendTime(t)
      setByModel(m)
      setByFeature(f)
      setByUser(u)
      setRecentRuns(runs.items)
    } catch {
      toast.error('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [apiKey, preset])

  useEffect(() => { load() }, [load])

  const presets: { v: Preset; label: string }[] = [
    { v: '5m', label: '5m' },
    { v: '15m', label: '15m' },
    { v: '30m', label: '30m' },
    { v: '1h', label: '1h' },
    { v: '3h', label: '3h' },
    { v: '6h', label: '6h' },
    { v: '12h', label: '12h' },
    { v: '24h', label: '24h' },
    { v: '7d', label: '7d' },
    { v: '30d', label: '30d' },
    { v: '90d', label: '90d' },
  ]

  async function handleExport(format: 'csv' | 'json') {
    if (!apiKey) return
    const win = presetWindow(preset)
    const qs = new URLSearchParams({ format, from: win.from, to: win.to })
    const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
    const url = `${base}/analytics/export?${qs}`
    try {
      const r = await fetch(url, { headers: { Authorization: `Bearer ${apiKey}` } })
      if (!r.ok) throw new Error()
      const blob = await r.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `analytics-${preset}.${format}`
      a.click()
      toast.success(`Exported as ${format.toUpperCase()}`)
    } catch {
      toast.error('Export failed')
    }
  }

  return (
    <div className={embedded ? 'space-y-3' : 'max-w-7xl space-y-4'}>
      {!embedded && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-violet-600 dark:text-violet-400" />
              <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white">Analytics Breakdown</h1>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Cost, usage, and attribution charts — workspace-scoped.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={load}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
            <div className="group relative">
              <button className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700">
                <Download className="h-3.5 w-3.5" /> Export
              </button>
              <div className="absolute right-0 top-full z-10 mt-1 hidden min-w-[100px] flex-col overflow-hidden rounded-lg border border-slate-200 bg-white text-sm shadow-lg group-hover:flex dark:border-slate-700 dark:bg-slate-800">
                <button onClick={() => handleExport('csv')} className="px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-700">CSV</button>
                <button onClick={() => handleExport('json')} className="px-4 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-700">JSON</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Period selector */}
      <div className="flex flex-wrap items-center gap-2">
        {embedded && (
          <button
            onClick={load}
            className="mr-1 flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-500 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        )}
        <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />
        <span className="mr-1 text-xs font-medium uppercase tracking-wide text-slate-400">Period</span>
        <div className="flex flex-wrap overflow-hidden rounded-lg border border-slate-200 bg-white text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900">
          {presets.map(({ v, label }) => (
            <button
              key={v}
              onClick={() => setPreset(v)}
              className={`px-2.5 py-1 text-xs transition-colors ${
                preset === v
                  ? 'bg-blue-600 font-medium text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI strip */}
      {loading && !summary ? (
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-3 xl:grid-cols-6">
          {[0, 1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-20 rounded-xl" />)}
        </div>
      ) : summary ? (
        <KpiStrip summary={summary} />
      ) : null}

      {/* Live Activity Bar */}
      <Card title="Live Model Activity" sub="Recent runs colored by model — bar height = token count" icon={Activity} action={
        <Link href="/runs" className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-[10px] font-semibold text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-950/50 dark:text-blue-300">
          All runs
        </Link>
      }>
        {recentRuns.length > 0 ? <LiveActivityBar runs={recentRuns} /> : loading ? <Skeleton className="h-44 w-full rounded-lg" /> : <EmptyState label="No recent runs" />}
      </Card>

      {/* Spend over time + Token breakdown */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Card title="Spend Over Time" sub={presetSubtitle(preset, presetGranularity(preset))} icon={TrendingUp} action={<ArrowUpRight className="h-4 w-4 text-slate-300 dark:text-slate-600" />}>
          {spendTime ? <SpendChart data={spendTime} /> : <Skeleton className="h-[260px] w-full rounded-lg" />}
        </Card>
        <Card title="Token Volume" sub="Input vs Output tokens stacked over time" icon={Zap}>
          {spendTime ? <TokenChart data={spendTime} /> : <Skeleton className="h-[200px] w-full rounded-lg" />}
        </Card>
      </div>

      {/* Model pie + Cost bars + Status donut + Latency */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-4">
        <Card title="Spend by Model" sub="Cost distribution" icon={PieIcon}>
          {byModel ? <ModelChart data={byModel} /> : <Skeleton className="h-[220px] w-full rounded-lg" />}
        </Card>
        <Card title="Model Cost Ranking" sub="Horizontal cost comparison" icon={BarChart2}>
          {byModel ? <ModelCostBars data={byModel} /> : <Skeleton className="h-[200px] w-full rounded-lg" />}
        </Card>
        <Card title="Run Status" sub="Success / failure breakdown" icon={Activity}>
          {recentRuns.length > 0 ? <StatusDonut runs={recentRuns} /> : loading ? <Skeleton className="h-[200px] w-full rounded-lg" /> : <EmptyState label="No runs" />}
        </Card>
        <Card title="Latency Distribution" sub="Response time histogram" icon={Clock}>
          {recentRuns.length > 0 ? <LatencyDistribution runs={recentRuns} /> : loading ? <Skeleton className="h-[160px] w-full rounded-lg" /> : <EmptyState label="No data" />}
        </Card>
      </div>

      {/* Feature tags */}
      <Card title="Spend by Feature Tag" sub="Top features by cost" icon={Layers}>
        {byFeature ? <FeatureChart data={byFeature} /> : <Skeleton className="h-[200px] w-full rounded-lg" />}
      </Card>

      {/* Activity Heatmap + Radar */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Card title="Activity Heatmap" sub="Runs by hour × day of week — darker = more runs" icon={Grid3x3}>
          {recentRuns.length > 0 ? <ActivityHeatmap runs={recentRuns} /> : loading ? <Skeleton className="h-[200px] w-full rounded-lg" /> : <EmptyState label="No activity data" />}
        </Card>
        <Card title="Model Radar" sub="Normalized comparison across cost, tokens, calls, speed" icon={Target}>
          {byModel && recentRuns.length > 0 ? <ModelRadar data={byModel} runs={recentRuns} /> : loading ? <Skeleton className="h-[280px] w-full rounded-lg" /> : <EmptyState label="No model data" />}
        </Card>
      </div>

      {/* Sankey: Model → Feature cost flow */}
      <Card title="Cost Flow: Model → Feature" sub="Sankey diagram showing how model spend distributes across features" icon={Workflow}>
        {byModel && byFeature && recentRuns.length > 0 ? (
          <SankeyChart modelData={byModel} featureData={byFeature} runs={recentRuns} />
        ) : loading ? <Skeleton className="h-[320px] w-full rounded-lg" /> : <EmptyState label="Need model + feature data" />}
      </Card>

      {/* Parallel Coordinates + Ridge Plot */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <Card title="Parallel Coordinates" sub="Compare models across cost, tokens, calls, latency" icon={GitBranch}>
          {byModel && recentRuns.length > 0 ? <ParallelCoordinates data={byModel} runs={recentRuns} /> : loading ? <Skeleton className="h-[260px] w-full rounded-lg" /> : <EmptyState label="No model data" />}
        </Card>
        <Card title="Latency Ridge Plot" sub="Distribution shape per model — peaks show typical response time" icon={Radio}>
          {recentRuns.length > 0 ? <RidgePlot runs={recentRuns} /> : loading ? <Skeleton className="h-[260px] w-full rounded-lg" /> : <EmptyState label="No runs" />}
        </Card>
      </div>

      {/* User spend table */}
      <Card title="Spend by End User" sub="Attribution per end_user_id — top 20" icon={Users} action={<Users className="h-4 w-4 text-slate-300 dark:text-slate-600" />}>
        {byUser ? <UserTable data={byUser} /> : <div className="space-y-2">{[0, 1, 2, 3, 4].map(i => <Skeleton key={i} className="h-10 w-full rounded-md" />)}</div>}
      </Card>

      {/* Full model breakdown table (non-embedded only) */}
      {!embedded && byModel && byModel.items.length > 0 && (
        <Card title="Model Breakdown" sub="Full cost, token, and call detail per model" icon={Layers}>
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Provider</th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Model</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Cost</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Input Tokens</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Output Tokens</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Calls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {byModel.items.map((m, i) => (
                <tr key={i} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{m.provider}</td>
                  <td className="px-4 py-2.5 font-mono text-sm font-medium dark:text-slate-200">
                    <span className="mr-1.5 inline-block h-2 w-2 rounded-full" style={{ backgroundColor: modelColor(m.model) }} />
                    {m.model}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono font-semibold text-violet-700 dark:text-violet-400">{fmt$(m.cost_usd)}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{m.input_tokens.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{m.output_tokens.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{m.call_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
