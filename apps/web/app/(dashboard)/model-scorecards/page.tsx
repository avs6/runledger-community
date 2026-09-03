'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { toast } from 'sonner'
import { Trophy, Star, ArrowUpDown, ChevronDown, ChevronRight, Lightbulb, AlertTriangle, Building2 } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { getModelScorecards, getModelScoreTrends, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getOptimizationOrgGatewayPosture, getOptimizationObservePosture, getOptimizationFinOpsPosture, getBuildInternalPosture, getModelScorecardsIntelPosture } from '@/lib/api'
import { getDashboardWindow } from '@/components/dashboard/DashboardScopeBar'
import type { ModelScorecard, ModelScoreTrend, BudgetDetailBuildPosture, BudgetControlBuildPosture, OptimizationOrgGatewayPosture, OptimizationObservePosture, OptimizationFinOpsPosture, BuildInternalPosture, ModelScorecardsIntelPosture } from '@/types/api'

type SortKey = keyof ModelScorecard
type SortDir = 'asc' | 'desc'
type RangeKey = '7d' | '30d' | '90d'

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
  const [range, setRange] = useState<RangeKey>('7d')
  const [expandedModel, setExpandedModel] = useState<string | null>(null)
  const [trendData, setTrendData] = useState<ModelScoreTrend[]>([])
  const [trendLoading, setTrendLoading] = useState(false)
  const [budgetBuildPosture, setBudgetBuildPosture] = useState<BudgetDetailBuildPosture | null>(null)
  const [budgetControlBuildPosture, setBudgetControlBuildPosture] = useState<BudgetControlBuildPosture | null>(null)
  const [orgGatewayPosture, setOrgGatewayPosture] = useState<OptimizationOrgGatewayPosture | null>(null)
  const [observePosture, setObservePosture] = useState<OptimizationObservePosture | null>(null)
  const [finOpsPosture, setFinOpsPosture] = useState<OptimizationFinOpsPosture | null>(null)
  const [buildPosture, setBuildPosture] = useState<BuildInternalPosture | null>(null)
  const [intelPosture, setIntelPosture] = useState<ModelScorecardsIntelPosture | null>(null)

  const fetchScorecards = useCallback(() => {
    if (!apiKey) return
    setLoading(true)
    const win = getDashboardWindow(range)
    getModelScorecards(apiKey, { from: win.from, to: win.to })
      .then(res => setData(res.items))
      .catch(() => toast.error('Failed to load model scorecards'))
      .finally(() => setLoading(false))
  }, [apiKey, range])

  useEffect(() => {
    fetchScorecards()
    if (apiKey) { getBudgetDetailBuildPosture(apiKey).then(setBudgetBuildPosture).catch(() => {}); getBudgetControlBuildPosture(apiKey).then(setBudgetControlBuildPosture).catch(() => {}); getOptimizationOrgGatewayPosture(apiKey).then(setOrgGatewayPosture).catch(() => {}); getOptimizationObservePosture(apiKey).then(setObservePosture).catch(() => {}); getOptimizationFinOpsPosture(apiKey).then(setFinOpsPosture).catch(() => {}); getBuildInternalPosture(apiKey).then(setBuildPosture).catch(() => {}); getModelScorecardsIntelPosture(apiKey).then(setIntelPosture).catch(() => {}) }
  }, [fetchScorecards])

  useEffect(() => {
    if (!expandedModel || !apiKey) {
      setTrendData([])
      return
    }
    setTrendLoading(true)
    const win = getDashboardWindow(range)
    getModelScoreTrends(apiKey, expandedModel, { from: win.from, to: win.to })
      .then(res => setTrendData(res.items))
      .catch(() => toast.error('Failed to load trend data'))
      .finally(() => setTrendLoading(false))
  }, [expandedModel, apiKey, range])

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  function toggleExpand(model: string) {
    setExpandedModel(prev => (prev === model ? null : model))
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

  const totalColumns = 15

  const chartData = trendData.map(t => ({
    date: t.date.slice(0, 10),
    quality: t.avg_quality_score != null ? Number(t.avg_quality_score) : null,
    errorRate: Number(t.error_rate) * 100,
  }))

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

      {budgetBuildPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget &amp; Build Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetBuildPosture.budget_context.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">30d Spend</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${budgetBuildPosture.spend_context.total_spend_30d.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Models Used</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetBuildPosture.spend_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetBuildPosture.budget_context.breach_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetBuildPosture.budget_context.breach_count}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?scope=feature_tag" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Feature Budgets</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Economics</Link>
            <Link href="/model-scorecards" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Model Scorecards</Link>
          </div>
        </div>
      )}

      {budgetControlBuildPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget Control — Build Posture</p>
          </div>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetControlBuildPosture.budget_policy.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
              <p className={`mt-1 text-lg font-semibold ${budgetControlBuildPosture.budget_policy.breached_budgets > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetControlBuildPosture.budget_policy.breached_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Avg Utilization</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">{budgetControlBuildPosture.budget_policy.avg_utilization_pct.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Scope Types</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{Object.keys(budgetControlBuildPosture.scope_context).length}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/budgets?tab=overrides" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Overrides</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing</Link>
          </div>
        </div>
      )}

      {orgGatewayPosture && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-5 shadow-sm dark:border-blue-900 dark:bg-blue-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Organization &amp; Access Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workspace</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.workspace_context.workspace_name}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">API Keys</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.api_key_context.api_keys}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.ai_hub_context.hub_models}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.ai_hub_context.hub_active_models}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-blue-200 dark:border-blue-800">
            <Link href="/organization" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Organization</Link>
            <Link href="/api-keys" className="text-xs text-blue-600 hover:underline dark:text-blue-400">API Keys</Link>
            <Link href="/ai-hub" className="text-xs text-blue-600 hover:underline dark:text-blue-400">AI Hub</Link>
          </div>
        </div>
      )}

      {orgGatewayPosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5 shadow-sm dark:border-violet-900 dark:bg-violet-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">Gateway &amp; Routing Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Providers</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.provider_context.distinct_providers}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Routes</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.provider_context.active_routes}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Guardrails</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.guardrail_context.guardrail_rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cache Configs</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.cache_context.cache_configs}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-violet-200 dark:border-violet-800">
            <Link href="/gateway" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Model Gateway</Link>
            <Link href="/routes" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Routes</Link>
            <Link href="/guardrails" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
            <Link href="/response-cache" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Response Cache</Link>
            <Link href="/rate-limits" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Rate Limits</Link>
          </div>
        </div>
      )}

      {observePosture && (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm dark:border-cyan-900 dark:bg-cyan-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">Observe &amp; Runtime Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Runs 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.runs_context.runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Provider Calls 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.request_flow_context.provider_calls_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Distinct Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.model_usage_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-cyan-600 dark:text-cyan-400">${observePosture.cost_savings_context.total_cost_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800">
            <Link href="/analytics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Analytics Overview</Link>
            <Link href="/runs" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Runs</Link>
            <Link href="/analytics?tab=requests" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Flow</Link>
            <Link href="/request-explorer" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Explorer</Link>
            <Link href="/analytics?tab=models" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Model Usage</Link>
          </div>
        </div>
      )}

      {finOpsPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 shadow-sm dark:border-emerald-800 dark:bg-emerald-950/30">
          <h3 className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-300">FinOps &amp; Budget Context</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Active budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{finOpsPosture.budget_context.active_budgets}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Total limit</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">${finOpsPosture.budget_context.total_limit.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Spend 30d</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${finOpsPosture.budget_context.spend_30d.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">Billing periods</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{finOpsPosture.billing_context.active_billing_periods} / {finOpsPosture.billing_context.total_billing_periods}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing Periods</Link>
            <Link href="/chargeback" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Chargeback</Link>
            <Link href="/cost-savings" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Cost &amp; Savings</Link>
          </div>
        </div>
      )}

      {buildPosture && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm dark:border-rose-900 dark:bg-rose-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400">Build &amp; Improve Loop</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Playground 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.playground_context.sessions_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workflows</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.workflows_context.definitions}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.evaluation_context.experiments}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Prompts</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.prompts_context.total_prompts}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Replay Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.replay_context.experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-rose-200 dark:border-rose-800">
            <Link href="/playground" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Playground</Link>
            <Link href="/workflows" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Workflows</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Evaluation Studio</Link>
            <Link href="/optimization-opportunities" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Optimization</Link>
            <Link href="/optimization-simulator" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Simulator</Link>
          </div>
        </div>
      )}

      {intelPosture && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm dark:border-amber-900 dark:bg-amber-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Model Intelligence &amp; Cost Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{intelPosture.model_context.hub_models}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Distinct Models 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{intelPosture.model_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cost 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">${Number(intelPosture.cost_context.cost_30d).toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Score Events 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{intelPosture.optimization_context.score_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-amber-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{intelPosture.optimization_context.eval_experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
            <Link href="/model-usage" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Model Usage</Link>
            <Link href="/cost-savings" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Cost &amp; Savings</Link>
            <Link href="/optimization-opportunities" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Optimization</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-amber-600 hover:underline dark:text-amber-400">Evaluation Studio</Link>
          </div>
        </div>
      )}

      {/* Workspace context bar */}
      <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50/60 px-4 py-2.5 dark:border-blue-800 dark:bg-blue-950/30">
        <Building2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        <p className="text-sm text-blue-800 dark:text-blue-200">
          Scorecards are scoped to your current workspace.
        </p>
        <div className="ml-auto flex gap-2">
          {[
            { label: 'Workspaces', href: '/workspaces' },
            { label: 'Model Usage', href: '/model-usage' },
            { label: 'Evaluation Studio', href: '/evaluation' },
          ].map(({ label, href }) => (
            <Link key={label} href={href} className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:hover:bg-blue-800/50 transition-colors">
              {label}
            </Link>
          ))}
        </div>
      </div>

      {/* Time range selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Time Range
        </span>
        <div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
          {(['7d', '30d', '90d'] as RangeKey[]).map(r => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                range === r
                  ? 'bg-white text-blue-700 shadow-sm dark:bg-slate-700 dark:text-blue-300'
                  : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
              }`}
            >
              {r}
            </button>
          ))}
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
                  <th className="w-8 px-2 py-3" />
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
                  <Th label="Accept Rate" col="acceptance_rate" />
                  <Th label="Hallucinations" col="hallucination_flags" />
                  <Th label="Retry Rate" col="retry_rate" />
                  <Th label="User Feedback" col="user_feedback_score" />
                  <Th label="Eval Score" col="eval_score" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {sorted.map(row => {
                  const errorRate = Number(row.error_rate ?? 0)
                  const cacheRate = Number(row.cache_hit_rate ?? 0)
                  const totalTokens = Number(row.input_tokens ?? 0) + Number(row.output_tokens ?? 0)
                  const hallucinationFlags = row.hallucination_flags ?? 0
                  const isExpanded = expandedModel === row.model

                  return (
                    <>
                      <tr
                        key={row.model}
                        className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
                        onClick={() => toggleExpand(row.model)}
                      >
                        <td className="px-2 py-3 text-slate-400">
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </td>
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
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {row.acceptance_rate != null ? fmtPct(row.acceptance_rate) : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={
                              hallucinationFlags > 0
                                ? 'inline-flex items-center gap-1 font-medium text-red-600 dark:text-red-400'
                                : 'text-slate-700 dark:text-slate-300'
                            }
                          >
                            {hallucinationFlags > 0 && (
                              <AlertTriangle className="h-3.5 w-3.5" />
                            )}
                            {hallucinationFlags}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {row.retry_rate != null ? fmtPct(row.retry_rate) : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1 text-slate-700 dark:text-slate-300">
                            {row.user_feedback_score != null ? (
                              <>
                                <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                                {Number(row.user_feedback_score).toFixed(1)}/5
                              </>
                            ) : (
                              '—'
                            )}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                          {row.eval_score != null ? Number(row.eval_score).toFixed(2) : '—'}
                        </td>
                      </tr>

                      {/* Expanded row: recommendation + trend chart */}
                      {isExpanded && (
                        <tr key={`${row.model}-expanded`}>
                          <td colSpan={totalColumns} className="bg-slate-50/60 px-6 py-4 dark:bg-slate-800/40">
                            {/* Recommendation */}
                            {row.recommendation && (
                              <div className="mb-4 flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3 dark:border-blue-900/40 dark:bg-blue-950/30">
                                <Lightbulb className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-500 dark:text-blue-400" />
                                <div>
                                  <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
                                    Routing Recommendation
                                  </span>
                                  <p className="mt-0.5 text-sm text-blue-800 dark:text-blue-200">
                                    {row.recommendation}
                                  </p>
                                </div>
                              </div>
                            )}

                            {/* Trend chart */}
                            <div>
                              <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">
                                Score Trends
                              </h3>
                              {trendLoading ? (
                                <div className="flex items-center justify-center py-8 text-sm text-slate-400">
                                  Loading trend data...
                                </div>
                              ) : chartData.length === 0 ? (
                                <div className="flex items-center justify-center py-8 text-sm text-slate-400">
                                  No trend data available for this time range.
                                </div>
                              ) : (
                                <div className="h-64 w-full">
                                  <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                      <XAxis
                                        dataKey="date"
                                        tick={{ fontSize: 11 }}
                                        stroke="#94a3b8"
                                      />
                                      <YAxis
                                        yAxisId="left"
                                        tick={{ fontSize: 11 }}
                                        stroke="#3b82f6"
                                        label={{ value: 'Quality Score', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#3b82f6' } }}
                                      />
                                      <YAxis
                                        yAxisId="right"
                                        orientation="right"
                                        tick={{ fontSize: 11 }}
                                        stroke="#ef4444"
                                        label={{ value: 'Error Rate %', angle: 90, position: 'insideRight', style: { fontSize: 11, fill: '#ef4444' } }}
                                      />
                                      <Tooltip
                                        contentStyle={{
                                          backgroundColor: 'rgba(255,255,255,0.95)',
                                          border: '1px solid #e2e8f0',
                                          borderRadius: '8px',
                                          fontSize: '12px',
                                        }}
                                      />
                                      <Line
                                        yAxisId="left"
                                        type="monotone"
                                        dataKey="quality"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                        dot={{ r: 3 }}
                                        name="Quality Score"
                                        connectNulls
                                      />
                                      <Line
                                        yAxisId="right"
                                        type="monotone"
                                        dataKey="errorRate"
                                        stroke="#ef4444"
                                        strokeWidth={2}
                                        dot={{ r: 3 }}
                                        name="Error Rate %"
                                      />
                                    </LineChart>
                                  </ResponsiveContainer>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Model Intelligence Flow</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Use scorecards after usage concentration is clear</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Start in Model Usage to see where traffic and spend concentrate, then use this page to compare quality, latency, cache, retries, and recommendation signals model by model.
          </p>
        </div>
        <Link
          href="/model-usage"
          className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-400 dark:hover:bg-slate-800"
        >
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">Open Model Usage</h2>
            <Trophy className="h-5 w-5 text-blue-600" />
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Cross-check whether the models with the highest traffic or spend are also the ones with the best quality-for-cost behavior.
          </p>
        </Link>
        <Link
          href="/evaluation"
          className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-400 dark:hover:bg-slate-800"
        >
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">Open Evaluation Studio</h2>
            <Lightbulb className="h-5 w-5 text-blue-600" />
          </div>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            Move from observed scorecards into explicit evaluation datasets, experiments, and replay when you need deeper proof before changing routing.
          </p>
        </Link>
      </div>
    </div>
  )
}
