'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { toast } from 'sonner'
import {
  BarChart2, Users, Layers, TrendingDown, TrendingUp,
  RefreshCw, Download, SlidersHorizontal, ArrowUpRight,
} from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import {
  getAnalyticsSummary, getSpendOverTime, getSpendByModel,
  getSpendByFeature, getSpendByUser,
} from '@/lib/api'
import type {
  AnalyticsSummary, SpendOverTime, SpendByModel,
  SpendByUser, SpendByFeature,
} from '@/types/api'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'

// ── Helpers ────────────────────────────────────────────────────────────────────

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

const COLORS = [
  '#0d9488', '#7c3aed', '#2563eb', '#d97706',
  '#db2777', '#16a34a', '#ea580c', '#9333ea',
]

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

// ── Sub-components ─────────────────────────────────────────────────────────────

function KpiStrip({ summary, prev }: { summary: AnalyticsSummary; prev?: AnalyticsSummary }) {
  const totalTokens = summary.total_input_tokens + summary.total_output_tokens
  const delta = summary.cost_delta_pct !== null ? parseFloat(summary.cost_delta_pct ?? '0') : null

  const cards = [
    {
      label: 'Total Spend',
      value: fmt$(summary.total_cost_usd),
      delta,
      sub: prev ? `prev: ${fmt$(prev.total_cost_usd)}` : undefined,
      color: 'teal',
    },
    { label: 'Runs', value: summary.run_count.toLocaleString(), color: 'violet' },
    { label: 'LLM Calls', value: summary.call_count.toLocaleString(), color: 'blue' },
    { label: 'Tokens', value: fmtTokens(totalTokens), color: 'cyan' },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map(c => (
        <div
          key={c.label}
          className={`rounded-xl border border-${c.color}-200/60 dark:border-${c.color}-800/40 bg-${c.color}-50/50 dark:bg-${c.color}-950/20 p-4`}
        >
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">{c.label}</p>
          <p className="mt-1.5 text-2xl font-bold text-slate-900 dark:text-white">{c.value}</p>
          {c.sub && <p className="mt-0.5 text-xs text-slate-400">{c.sub}</p>}
          {c.delta !== undefined && c.delta !== null && (
            <div className={`mt-1 flex items-center gap-1 text-xs font-medium ${c.delta >= 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
              {c.delta >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {c.delta >= 0 ? '+' : ''}{c.delta.toFixed(1)}% vs prior period
            </div>
          )}
        </div>
      ))}
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
    tokens: p.input_tokens + p.output_tokens,
    calls: p.call_count,
  }))
  if (points.length === 0) return <EmptyState label="No spend data for this period" />
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={points} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#0d9488" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-700" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `$${v}`} />
        <Tooltip formatter={(v, name) => [name === 'cost' ? `$${Number(v).toFixed(4)}` : Number(v).toLocaleString(), name === 'cost' ? 'Cost' : 'Calls']} />
        <Area type="monotone" dataKey="cost" stroke="#0d9488" strokeWidth={2} fill="url(#g1)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function ModelChart({ data }: { data: SpendByModel }) {
  if (data.items.length === 0) return <EmptyState label="No model data" />
  const pie = data.items.map(m => ({
    name: `${m.provider}/${m.model}`,
    value: parseFloat(m.cost_usd),
    tokens: m.input_tokens + m.output_tokens,
    calls: m.call_count,
  }))
  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }: { name?: string; percent?: number }) => `${(name ?? '').split('/')[1] ?? name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
            {pie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip formatter={(v) => fmt$(Number(v))} />
        </PieChart>
      </ResponsiveContainer>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-100 dark:border-slate-700 text-slate-400">
            <th className="pb-1.5 text-left font-medium">Model</th>
            <th className="pb-1.5 text-right font-medium">Cost</th>
            <th className="pb-1.5 text-right font-medium">Tokens</th>
            <th className="pb-1.5 text-right font-medium">Calls</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
          {data.items.map((m, i) => (
            <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
              <td className="py-1.5 font-mono flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                {m.model}
              </td>
              <td className="py-1.5 text-right font-medium">{fmt$(m.cost_usd)}</td>
              <td className="py-1.5 text-right text-slate-400">{fmtTokens(m.input_tokens + m.output_tokens)}</td>
              <td className="py-1.5 text-right text-slate-400">{m.call_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FeatureChart({ data }: { data: SpendByFeature }) {
  if (data.items.length === 0) return <EmptyState label="No feature data" />
  const bars = data.items
    .filter(f => f.feature_tag)
    .map(f => ({ name: f.feature_tag!, cost: parseFloat(f.cost_usd), runs: f.run_count }))
  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={bars} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="currentColor" className="text-slate-200 dark:text-slate-700" />
          <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={v => `$${v}`} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={110} />
          <Tooltip formatter={(v) => [fmt$(Number(v)), 'Cost']} />
          <Bar dataKey="cost" fill="#7c3aed" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function UserTable({ data }: { data: SpendByUser }) {
  if (data.items.length === 0) return <EmptyState label="No user data for this period" />
  return (
    <table className="w-full text-sm">
      <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <tr>
          <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">User</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Spend</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Runs</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Avg/Run</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Calls</th>
          <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Last Active</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
        {data.items.map((u, i) => (
          <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
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

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-slate-400 dark:text-slate-500">{label}</div>
  )
}

function Card({ title, sub, children, action }: {
  title: string; sub?: string; children: React.ReactNode; action?: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden">
      <div className="flex items-start justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-800">
        <div>
          <p className="text-sm font-semibold text-slate-900 dark:text-white">{title}</p>
          {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
        </div>
        {action}
      </div>
      <div className="px-5 py-4">{children}</div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey

  const [preset, setPreset] = useState<Preset>('24h')
  const [loading, setLoading] = useState(true)

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [spendTime, setSpendTime] = useState<SpendOverTime | null>(null)
  const [byModel, setByModel] = useState<SpendByModel | null>(null)
  const [byFeature, setByFeature] = useState<SpendByFeature | null>(null)
  const [byUser, setByUser] = useState<SpendByUser | null>(null)

  const load = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    const win = presetWindow(preset)
    const gran = presetGranularity(preset)
    try {
      const [s, t, m, f, u] = await Promise.all([
        getAnalyticsSummary(apiKey, win),
        getSpendOverTime(apiKey, gran, win),
        getSpendByModel(apiKey, win),
        getSpendByFeature(apiKey, win),
        getSpendByUser(apiKey, 20, win),
      ])
      setSummary(s); setSpendTime(t); setByModel(m); setByFeature(f); setByUser(u)
    } catch {
      toast.error('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [apiKey, preset])

  useEffect(() => { load() }, [load])

  const PRESETS: { v: Preset; label: string }[] = [
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
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <BarChart2 className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-950 dark:text-white">Analytics</h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Spend breakdown, model usage, and per-user attribution for this workspace.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={load}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <div className="relative group">
            <button className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
              <Download className="h-3.5 w-3.5" /> Export
            </button>
            <div className="absolute right-0 top-full mt-1 hidden group-hover:flex flex-col z-10 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-lg overflow-hidden text-sm min-w-[100px]">
              <button onClick={() => handleExport('csv')} className="px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-700 text-left">CSV</button>
              <button onClick={() => handleExport('json')} className="px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-700 text-left">JSON</button>
            </div>
          </div>
        </div>
      </div>

      {/* Time range selector */}
      <div className="flex flex-wrap items-center gap-2">
        <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />
        <span className="text-xs text-slate-400 font-medium uppercase tracking-wide mr-1">Period</span>
        <div className="flex flex-wrap overflow-hidden rounded-lg border border-slate-200 bg-white text-sm shadow-sm dark:border-slate-700 dark:bg-slate-900">
          {PRESETS.map(({ v, label }) => (
            <button
              key={v}
              onClick={() => setPreset(v)}
              className={`px-3 py-1.5 transition-colors ${
                preset === v
                  ? 'bg-blue-600 text-white font-medium'
                  : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI strip */}
      {loading && !summary ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
      ) : summary ? (
        <KpiStrip summary={summary} />
      ) : null}

      {/* Spend over time */}
      <Card
        title="Spend Over Time"
        sub={presetSubtitle(preset, presetGranularity(preset))}
        action={
          <ArrowUpRight className="h-4 w-4 text-slate-300 dark:text-slate-600" />
        }
      >
        {spendTime ? <SpendChart data={spendTime} /> : <Skeleton className="h-[240px] w-full rounded-lg" />}
      </Card>

      {/* Model + Feature row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Spend by Model" sub="Cost attribution across providers">
          {byModel ? <ModelChart data={byModel} /> : <Skeleton className="h-[200px] w-full rounded-lg" />}
        </Card>
        <Card title="Spend by Feature Tag" sub="Top features by cost">
          {byFeature ? <FeatureChart data={byFeature} /> : <Skeleton className="h-[200px] w-full rounded-lg" />}
        </Card>
      </div>

      {/* Per-user spend */}
      <Card
        title="Spend by End User"
        sub="Attribution per end_user_id — top 20"
        action={<Users className="h-4 w-4 text-slate-300 dark:text-slate-600" />}
      >
        {byUser ? <UserTable data={byUser} /> : <div className="space-y-2">{[0,1,2,3,4].map(i => <Skeleton key={i} className="h-10 w-full rounded-md" />)}</div>}
      </Card>

      {/* Model breakdown full table */}
      <Card
        title="Model Breakdown"
        sub="Full cost, token, and call detail per model"
        action={<Layers className="h-4 w-4 text-slate-300 dark:text-slate-600" />}
      >
        {byModel && byModel.items.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Provider</th>
                <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Model</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Cost</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Input Tokens</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Output Tokens</th>
                <th className="px-4 py-2.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Calls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {byModel.items.map((m, i) => (
                <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{m.provider}</td>
                  <td className="px-4 py-2.5 font-mono text-sm font-medium dark:text-slate-200">{m.model}</td>
                  <td className="px-4 py-2.5 text-right font-mono font-semibold text-violet-700 dark:text-violet-400">{fmt$(m.cost_usd)}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{m.input_tokens.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{m.output_tokens.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{m.call_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState label="No model data for this period" />}
      </Card>
    </div>
  )
}
