import { getServerSession } from 'next-auth'
import Link from 'next/link'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  Clock,
  Cpu,
  DollarSign,
  Filter,
  Layers,
  RefreshCw,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
  Wrench,
  Zap,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getEngineeringMetrics, getBudgetDetailObservePosture, getBudgetControlObservePosture } from '@/lib/api'
import DashboardScopeBar from '@/components/dashboard/DashboardScopeBar'
import { getDashboardWindow } from '@/lib/dashboard-window'
import { formatCost, formatTokens, num } from '@/lib/utils'
import type { EngineeringMetrics, CostByDimension, QualityFunnel } from '@/types/api'
import { InteractivePipeline, InteractiveAgentGraph } from './EngineeringClient'

interface PageProps {
  searchParams: { range?: string }
}

function CostTable({ title, items }: { title: string; items: CostByDimension[] }) {
  if (items.length === 0) return <p className="py-3 text-center text-[11px] text-slate-400">No data</p>
  const maxCost = Math.max(...items.map(i => Number(i.cost_usd)), 0.001)
  return (
    <div>
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400">{title}</p>
      <div className="space-y-1.5">
        {items.map(item => {
          const pct = (Number(item.cost_usd) / maxCost) * 100
          return (
            <div key={item.name}>
              <div className="flex items-center justify-between text-[11px]">
                <span className="max-w-[140px] truncate font-medium text-slate-700 dark:text-slate-300" title={item.name}>{item.name}</span>
                <span className="font-mono text-slate-500">{formatCost(item.cost_usd)} <span className="text-slate-400">({item.call_count})</span></span>
              </div>
              <div className="mt-0.5 h-1 w-full rounded-full bg-slate-100 dark:bg-slate-800">
                <div className="h-1 rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function FunnelChart({ funnel }: { funnel: QualityFunnel }) {
  const stages = [
    { label: 'Total', count: funnel.total_requests, color: 'bg-blue-500' },
    { label: 'Success', count: funnel.successful, color: 'bg-emerald-500' },
    { label: 'Routed', count: funnel.routed, color: 'bg-purple-500' },
    { label: 'Cached', count: funnel.cached, color: 'bg-amber-500' },
    { label: 'Outcome', count: funnel.with_outcome, color: 'bg-cyan-500' },
    { label: 'Positive', count: funnel.positive_outcome, color: 'bg-green-600' },
  ]
  const maxCount = Math.max(funnel.total_requests, 1)
  return (
    <div className="space-y-1.5">
      {stages.map(s => {
        const pct = (s.count / maxCount) * 100
        return (
          <div key={s.label}>
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-medium text-slate-600 dark:text-slate-300">{s.label}</span>
              <span className="font-mono text-slate-500">{s.count.toLocaleString()} <span className="text-slate-400">({num(pct).toFixed(0)}%)</span></span>
            </div>
            <div className="mt-0.5 h-2.5 w-full rounded-md bg-slate-100 dark:bg-slate-800">
              <div className={`h-2.5 rounded-md ${s.color} transition-all`} style={{ width: `${Math.max(pct, 0.5)}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default async function EngineeringPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const { range, from, to, label } = getDashboardWindow(searchParams.range)
  let metrics: EngineeringMetrics | null = null
  try {
    metrics = await getEngineeringMetrics(session.apiKey, { from, to })
  } catch { /* endpoint may not be available */ }

  const budgetPosture = await getBudgetDetailObservePosture(session.apiKey).catch(() => null)
  const budgetControlPosture = await getBudgetControlObservePosture(session.apiKey).catch(() => null)

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-bold text-slate-950 dark:text-white">Engineering</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">Latency, errors, cost breakdowns, quality funnel, and agent architecture.</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { href: '/request-explorer', label: 'Explorer', icon: Search },
            { href: '/request-flow', label: 'Flow', icon: Route },
            { href: '/model-usage', label: 'Models', icon: Cpu },
          ].map(nav => (
            <Link key={nav.label} href={nav.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              {nav.label} <nav.icon className="h-3 w-3" />
            </Link>
          ))}
        </div>
      </div>

      <DashboardScopeBar
        scope="Workspace"
        context={label}
        activeRange={range}
        basePath="/engineering"
        dimensions={['Latency', 'Errors', 'Cache', 'Cost', 'Quality']}
      />

      {!metrics ? (
        <div className="rounded-xl border border-slate-200 bg-white/90 p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <Activity className="mx-auto h-6 w-6 text-slate-400" />
          <p className="mt-2 text-sm font-semibold text-slate-800 dark:text-white">No engineering data</p>
          <p className="mt-1 text-xs text-slate-500">Send traffic through SDK, Gateway, or OTLP to populate.</p>
        </div>
      ) : (
        <>
          {/* HERO: Request Lifecycle Pipeline — full width */}
          <div className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-3 flex items-center gap-1.5">
              <Route className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Request Lifecycle Pipeline</p>
              <span className="text-[10px] text-slate-400">Click any stage for details</span>
            </div>
            <InteractivePipeline stages={metrics.lifecycle_stages} />
          </div>

          {/* KPI strip */}
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
            {[
              { title: 'Avg Latency', value: metrics.avg_latency_ms ? `${Number(metrics.avg_latency_ms).toFixed(0)}ms` : 'N/A', sub: metrics.p95_latency_ms ? `P95: ${Number(metrics.p95_latency_ms).toFixed(0)}ms` : undefined, icon: Clock, color: 'text-blue-600 dark:text-blue-400' },
              { title: 'Error Rate', value: `${Number(metrics.error_pct).toFixed(1)}%`, icon: AlertTriangle, color: Number(metrics.error_pct) > 5 ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400' },
              { title: 'Retry Rate', value: `${Number(metrics.retry_pct).toFixed(1)}%`, icon: RefreshCw, color: Number(metrics.retry_pct) > 10 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400' },
              { title: 'Cache Rate', value: `${Number(metrics.cache_pct).toFixed(1)}%`, icon: Sparkles, color: 'text-purple-600 dark:text-purple-400' },
              { title: 'Requests', value: metrics.total_requests.toLocaleString(), icon: Zap, color: 'text-blue-600 dark:text-blue-400' },
              { title: 'Tokens', value: formatTokens(metrics.total_tokens), icon: Layers, color: 'text-blue-600 dark:text-blue-400' },
              { title: 'Avg Cost/Req', value: metrics.avg_cost_per_request ? formatCost(metrics.avg_cost_per_request) : '$0', icon: DollarSign, color: 'text-emerald-600 dark:text-emerald-400' },
              { title: 'Total Cost', value: formatCost(String(metrics.cost_by_model.reduce((s, m) => s + Number(m.cost_usd), 0).toFixed(6))), icon: DollarSign, color: 'text-blue-600 dark:text-blue-400' },
            ].map(kpi => (
              <div key={kpi.title} className="rounded-xl border border-slate-200 bg-white/90 p-2.5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center gap-1">
                  <kpi.icon className={`h-3 w-3 ${kpi.color}`} />
                  <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{kpi.title}</span>
                </div>
                <p className="mt-1 text-base font-bold text-slate-950 dark:text-white">{kpi.value}</p>
                {kpi.sub && <p className="text-[10px] text-slate-400">{kpi.sub}</p>}
              </div>
            ))}
          </div>

          {/* Quality Funnel + Cost breakdowns */}
          <div className="grid gap-3 xl:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="mb-2 flex items-center gap-1.5">
                <Filter className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" />
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Quality Funnel</p>
              </div>
              <FunnelChart funnel={metrics.quality_funnel} />
            </div>
            <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="mb-2 flex items-center gap-1.5">
                <BarChart3 className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Cost by Feature</p>
              </div>
              <CostTable title="Top features" items={metrics.cost_by_feature} />
            </div>
            <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="mb-2 flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Cost by Model</p>
              </div>
              <CostTable title="Top models" items={metrics.cost_by_model} />
            </div>
            <div className="rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
              <div className="mb-2 flex items-center gap-1.5">
                <Wrench className="h-3.5 w-3.5 text-orange-600 dark:text-orange-400" />
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Tool Usage</p>
              </div>
              <CostTable title="Top tools" items={metrics.cost_by_tool} />
            </div>
          </div>

          {/* Agent Dependency Graph — full width */}
          <div className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-3 flex items-center gap-1.5">
              <BrainCircuit className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Agent Dependency Graph</p>
              <span className="text-[10px] text-slate-400">Click any node to explore</span>
            </div>
            <InteractiveAgentGraph />
          </div>

          {/* Budget postures — compact chips */}
          {(budgetPosture || budgetControlPosture) && (
            <div className="grid gap-2 lg:grid-cols-2">
              {budgetPosture && (
                <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <DollarSign className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">Budget Signals</span>
                    </div>
                    <Link href="/budgets" className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">Manage</Link>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {[
                      { l: 'Active', v: `${budgetPosture.engineering_context.active_budgets}` },
                      { l: 'Feature', v: `${budgetPosture.engineering_context.feature_scoped_budgets}` },
                      { l: 'Limit', v: `$${num(budgetPosture.engineering_context.total_limit_usd).toFixed(2)}` },
                      { l: 'Breached', v: `${budgetPosture.engineering_context.breach_count}` },
                    ].map(c => (
                      <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                        <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                        <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {budgetControlPosture && (
                <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                      <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">Budget Control</span>
                    </div>
                    <Link href="/budgets" className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">Manage</Link>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {[
                      { l: 'Active', v: `${budgetControlPosture.budget_policy.active_budgets}` },
                      { l: 'Breached', v: `${budgetControlPosture.budget_policy.breached_budgets}` },
                      { l: 'At Risk', v: `${budgetControlPosture.budget_policy.at_risk_budgets}` },
                      { l: 'Utilization', v: `${num(budgetControlPosture.budget_policy.avg_utilization_pct).toFixed(1)}%` },
                    ].map(c => (
                      <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                        <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                        <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
