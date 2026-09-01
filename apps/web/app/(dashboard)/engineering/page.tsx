import { getServerSession } from 'next-auth'
import Link from 'next/link'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  DollarSign,
  Filter,
  GitBranch,
  Layers,
  MessageSquareText,
  RefreshCw,
  Route,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  Wrench,
  Zap,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getEngineeringMetrics, getBudgetDetailObservePosture } from '@/lib/api'
import DashboardScopeBar, { getDashboardWindow } from '@/components/dashboard/DashboardScopeBar'
import { formatCost, formatTokens } from '@/lib/utils'
import type { EngineeringMetrics, CostByDimension, LifecycleStage, QualityFunnel } from '@/types/api'

interface PageProps {
  searchParams: { range?: string }
}

function KpiCard({
  title,
  value,
  sub,
  icon: Icon,
  accent = 'blue',
}: {
  title: string
  value: string
  sub?: string
  icon: React.ElementType
  accent?: 'blue' | 'green' | 'amber' | 'red' | 'purple'
}) {
  const colors = {
    blue: 'text-blue-600 bg-blue-50',
    green: 'text-emerald-600 bg-emerald-50',
    amber: 'text-amber-600 bg-amber-50',
    red: 'text-red-600 bg-red-50',
    purple: 'text-purple-600 bg-purple-50',
  }
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-300 dark:bg-white/90">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</p>
        <span className={`rounded-lg p-1.5 ${colors[accent]}`}>
          <Icon className="h-3.5 w-3.5" />
        </span>
      </div>
      <p className="mt-2 text-xl font-bold text-slate-950">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

function SectionCard({ title, children, icon: Icon }: { title: string; children: React.ReactNode; icon: React.ElementType }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-300 dark:bg-white/90">
      <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-4">
        <Icon className="h-4 w-4 text-blue-600" />
        <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}

function CostTable({ title, items }: { title: string; items: CostByDimension[] }) {
  if (items.length === 0) {
    return <p className="py-4 text-center text-sm text-slate-500">No data yet</p>
  }
  const maxCost = Math.max(...items.map((i) => Number(i.cost_usd)), 0.001)
  return (
    <div>
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <div className="space-y-2">
        {items.map((item) => {
          const pct = (Number(item.cost_usd) / maxCost) * 100
          return (
            <div key={item.name}>
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-700 truncate max-w-[180px]" title={item.name}>{item.name}</span>
                <span className="font-mono text-slate-600">{formatCost(item.cost_usd)} <span className="text-slate-400">({item.call_count})</span></span>
              </div>
              <div className="mt-1 h-1.5 w-full rounded-full bg-slate-100">
                <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
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
    { label: 'Total requests', count: funnel.total_requests, color: 'bg-blue-500' },
    { label: 'Successful', count: funnel.successful, color: 'bg-emerald-500' },
    { label: 'Gateway routed', count: funnel.routed, color: 'bg-purple-500' },
    { label: 'Cache hits', count: funnel.cached, color: 'bg-amber-500' },
    { label: 'With outcome', count: funnel.with_outcome, color: 'bg-cyan-500' },
    { label: 'Positive outcome', count: funnel.positive_outcome, color: 'bg-green-600' },
  ]
  const maxCount = Math.max(funnel.total_requests, 1)

  return (
    <div className="space-y-3">
      {stages.map((stage) => {
        const pct = (stage.count / maxCount) * 100
        return (
          <div key={stage.label}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-700">{stage.label}</span>
              <span className="font-mono text-slate-600">
                {stage.count.toLocaleString()} <span className="text-slate-400">({pct.toFixed(1)}%)</span>
              </span>
            </div>
            <div className="mt-1 h-4 w-full rounded-lg bg-slate-100">
              <div className={`h-4 rounded-lg ${stage.color} transition-all`} style={{ width: `${Math.max(pct, 0.5)}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function LifecyclePipeline({ stages }: { stages: LifecycleStage[] }) {
  const pipelineStages = [
    { icon: MessageSquareText, label: 'Received', color: 'bg-blue-100 text-blue-700 border-blue-200' },
    { icon: Route, label: 'Routed', color: 'bg-purple-100 text-purple-700 border-purple-200' },
    { icon: Sparkles, label: 'Cached', color: 'bg-amber-100 text-amber-700 border-amber-200' },
    { icon: CheckCircle2, label: 'Completed', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
    { icon: ShieldCheck, label: 'With outcome', color: 'bg-cyan-100 text-cyan-700 border-cyan-200' },
    { icon: TrendingDown, label: 'Positive', color: 'bg-green-100 text-green-700 border-green-200' },
  ]

  return (
    <div className="flex flex-wrap items-center gap-2">
      {pipelineStages.map((ps, i) => {
        const match = stages.find((s) => s.stage === ps.label)
        const Icon = ps.icon
        return (
          <div key={ps.label} className="flex items-center gap-2">
            <div className={`flex items-center gap-2 rounded-xl border px-3 py-2 ${ps.color}`}>
              <Icon className="h-4 w-4" />
              <div>
                <p className="text-xs font-semibold">{ps.label}</p>
                <p className="text-[11px] font-mono">
                  {match?.count.toLocaleString() ?? 0} ({match?.pct ?? '0'}%)
                </p>
              </div>
            </div>
            {i < pipelineStages.length - 1 && (
              <ArrowRight className="h-4 w-4 text-slate-300 flex-shrink-0" />
            )}
          </div>
        )
      })}
    </div>
  )
}

function AgentDependencyGraph() {
  /* ── Layout constants ── */
  const W = 400, H = 300
  const nodeW = 110, nodeH = 36, iconR = 12

  /* ── Node definitions with pixel positions (centre of each node) ── */
  const nodes: { id: string; label: string; icon: React.ElementType; cx: number; cy: number; fill: string; stroke: string; text: string; iconBg: string }[] = [
    { id: 'agent',    label: 'Agent',         icon: BrainCircuit,     cx: 200, cy: 42,  fill: '#dbeafe', stroke: '#93c5fd', text: '#1e40af', iconBg: '#3b82f6' },
    { id: 'subagent', label: 'Sub-Agent',     icon: GitBranch,        cx: 62,  cy: 145, fill: '#ede9fe', stroke: '#c4b5fd', text: '#5b21b6', iconBg: '#8b5cf6' },
    { id: 'memory',   label: 'Memory',        icon: Database,         cx: 200, cy: 145, fill: '#cffafe', stroke: '#67e8f9', text: '#155e75', iconBg: '#06b6d4' },
    { id: 'policy',   label: 'Policy Engine', icon: ShieldCheck,      cx: 338, cy: 145, fill: '#fef3c7', stroke: '#fcd34d', text: '#92400e', iconBg: '#f59e0b' },
    { id: 'model',    label: 'Model',         icon: Cpu,              cx: 62,  cy: 252, fill: '#d1fae5', stroke: '#6ee7b7', text: '#065f46', iconBg: '#10b981' },
    { id: 'tool',     label: 'Tool',          icon: Wrench,           cx: 200, cy: 252, fill: '#ffedd5', stroke: '#fdba74', text: '#9a3412', iconBg: '#f97316' },
    { id: 'response', label: 'Response',      icon: MessageSquareText,cx: 338, cy: 252, fill: '#dcfce7', stroke: '#86efac', text: '#14532d', iconBg: '#22c55e' },
  ]

  const edges: { from: string; to: string }[] = [
    { from: 'agent', to: 'subagent' },
    { from: 'agent', to: 'memory' },
    { from: 'agent', to: 'policy' },
    { from: 'subagent', to: 'model' },
    { from: 'agent', to: 'tool' },
    { from: 'model', to: 'response' },
    { from: 'tool', to: 'response' },
    { from: 'policy', to: 'response' },
  ]

  const byId = (id: string) => nodes.find((n) => n.id === id)!

  /* ── Build a smooth cubic‑bezier path between two nodes ── */
  function edgePath(from: typeof nodes[0], to: typeof nodes[0]) {
    const x1 = from.cx, y1 = from.cy + nodeH / 2
    const x2 = to.cx,   y2 = to.cy - nodeH / 2
    const dy = (y2 - y1) * 0.5
    return `M${x1},${y1} C${x1},${y1 + dy} ${x2},${y2 - dy} ${x2},${y2}`
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ maxHeight: 320 }}
      role="img"
      aria-label="Agent dependency graph showing how agents, models, tools, memory, and policies connect"
    >
      <defs>
        {/* Gradient for edges */}
        <linearGradient id="edgeGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#94a3b8" stopOpacity="0.6" />
          <stop offset="100%" stopColor="#94a3b8" stopOpacity="0.2" />
        </linearGradient>
        {/* Soft drop shadow for nodes */}
        <filter id="nodeShadow" x="-8%" y="-8%" width="116%" height="130%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0f172a" floodOpacity="0.08" />
        </filter>
        {/* Small arrowhead marker */}
        <marker id="arrowHead" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
          <path d="M0,0 L7,2.5 L0,5" fill="none" stroke="#94a3b8" strokeWidth="1" />
        </marker>
      </defs>

      {/* ── Edges ── */}
      {edges.map((e) => {
        const from = byId(e.from), to = byId(e.to)
        return (
          <path
            key={`${e.from}-${e.to}`}
            d={edgePath(from, to)}
            fill="none"
            stroke="url(#edgeGrad)"
            strokeWidth="1.5"
            strokeLinecap="round"
            markerEnd="url(#arrowHead)"
          />
        )
      })}

      {/* ── Nodes ── */}
      {nodes.map((n) => {
        const Icon = n.icon
        const rx = nodeW / 2, ry = nodeH / 2
        return (
          <g key={n.id}>
            {/* Card background */}
            <rect
              x={n.cx - rx}
              y={n.cy - ry}
              width={nodeW}
              height={nodeH}
              rx={10}
              ry={10}
              fill={n.fill}
              stroke={n.stroke}
              strokeWidth="1.2"
              filter="url(#nodeShadow)"
            />
            {/* Icon circle */}
            <circle cx={n.cx - rx + 20} cy={n.cy} r={iconR} fill={n.iconBg} opacity="0.15" />
            <foreignObject x={n.cx - rx + 20 - 7} y={n.cy - 7} width="14" height="14">
              <Icon
                className="h-3.5 w-3.5"
                style={{ color: n.iconBg }}
              />
            </foreignObject>
            {/* Label */}
            <text
              x={n.cx + 6}
              y={n.cy + 1}
              textAnchor="middle"
              dominantBaseline="middle"
              fill={n.text}
              fontSize="11"
              fontWeight="600"
              fontFamily="ui-sans-serif, system-ui, sans-serif"
            >
              {n.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export default async function EngineeringPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const { range, from, to, label } = getDashboardWindow(searchParams.range)
  let metrics: EngineeringMetrics | null = null
  try {
    metrics = await getEngineeringMetrics(session.apiKey, { from, to })
  } catch {
    /* endpoint may not be available yet */
  }

  const budgetPosture = await getBudgetDetailObservePosture(session.apiKey).catch(() => null)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950">Engineering Dashboard</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Latency, errors, retries, cache performance, cost breakdowns, and quality funnel for your AI systems.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/request-explorer"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50"
          >
            Request Explorer <Search className="h-4 w-4" />
          </Link>
          <Link
            href="/request-flow"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50"
          >
            Request Flow <Route className="h-4 w-4" />
          </Link>
          <Link
            href="/model-usage"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-blue-50"
          >
            Model Usage <Cpu className="h-4 w-4" />
          </Link>
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
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-12 text-center shadow-sm">
          <Activity className="mx-auto h-8 w-8 text-slate-400" />
          <p className="mt-3 text-base font-semibold text-slate-950">No engineering data available</p>
          <p className="mt-1 text-sm text-slate-500">Send traffic through SDK, Gateway, or OTLP to see metrics here.</p>
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-8">
            <KpiCard title="Avg latency" value={metrics.avg_latency_ms ? `${Number(metrics.avg_latency_ms).toFixed(0)}ms` : 'N/A'} sub={metrics.p95_latency_ms ? `P95: ${Number(metrics.p95_latency_ms).toFixed(0)}ms` : undefined} icon={Clock} accent="blue" />
            <KpiCard title="Error rate" value={`${Number(metrics.error_pct).toFixed(1)}%`} icon={AlertTriangle} accent={Number(metrics.error_pct) > 5 ? 'red' : 'green'} />
            <KpiCard title="Retry rate" value={`${Number(metrics.retry_pct).toFixed(1)}%`} icon={RefreshCw} accent={Number(metrics.retry_pct) > 10 ? 'amber' : 'green'} />
            <KpiCard title="Cache rate" value={`${Number(metrics.cache_pct).toFixed(1)}%`} icon={Sparkles} accent="purple" />
            <KpiCard title="Total requests" value={metrics.total_requests.toLocaleString()} icon={Zap} accent="blue" />
            <KpiCard title="Total tokens" value={formatTokens(metrics.total_tokens)} icon={Layers} accent="blue" />
            <KpiCard title="Avg cost/req" value={metrics.avg_cost_per_request ? formatCost(metrics.avg_cost_per_request) : '$0.00'} icon={DollarSign} accent="green" />
            <KpiCard title="Total cost" value={formatCost(String(metrics.cost_by_model.reduce((s, m) => s + Number(m.cost_usd), 0).toFixed(6)))} icon={DollarSign} accent="blue" />
          </div>

          {budgetPosture && (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">Budget Signals</p>
              </div>
              <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
                  <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPosture.engineering_context.active_budgets}</p>
                </div>
                <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Feature Budgets</p>
                  <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetPosture.engineering_context.feature_scoped_budgets}</p>
                </div>
                <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Total Limit</p>
                  <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${budgetPosture.engineering_context.total_limit_usd.toFixed(2)}</p>
                </div>
                <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
                  <p className="text-xs text-slate-500 dark:text-slate-400">Breached</p>
                  <p className={`mt-1 text-lg font-semibold ${budgetPosture.engineering_context.breach_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-900 dark:text-white'}`}>{budgetPosture.engineering_context.breach_count}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
                <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
                <Link href="/budgets?scope_type=feature_tag" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Feature Budgets</Link>
                <Link href="/analytics?tab=economics" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Economics</Link>
                <Link href="/analytics?tab=savings" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Cost & Savings</Link>
              </div>
            </div>
          )}

          {/* Prompt Lifecycle Pipeline */}
          <SectionCard title="Request Lifecycle Pipeline" icon={Route}>
            <p className="mb-4 text-sm text-slate-600">How requests flow through the system: received → routed → cached → completed → outcome → positive feedback.</p>
            <LifecyclePipeline stages={metrics.lifecycle_stages} />
          </SectionCard>

          {/* Quality Funnel + Agent Dependency side by side */}
          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Quality Funnel" icon={Filter}>
              <p className="mb-4 text-sm text-slate-600">Conversion from total requests to positive outcomes.</p>
              <FunnelChart funnel={metrics.quality_funnel} />
            </SectionCard>

            <SectionCard title="Agent Dependency Graph" icon={BrainCircuit}>
              <p className="mb-4 text-sm text-slate-600">How agents, models, tools, memory, and policies connect in the request path.</p>
              <AgentDependencyGraph />
            </SectionCard>
          </div>

          {/* Cost Breakdowns */}
          <div className="grid gap-6 xl:grid-cols-3">
            <SectionCard title="Cost by Feature / Team" icon={BarChart3}>
              <CostTable title="Top features by cost" items={metrics.cost_by_feature} />
            </SectionCard>
            <SectionCard title="Cost by Model" icon={Cpu}>
              <CostTable title="Top models by cost" items={metrics.cost_by_model} />
            </SectionCard>
            <SectionCard title="Tool Usage" icon={Wrench}>
              <CostTable title="Top tools by call count" items={metrics.cost_by_tool} />
            </SectionCard>
          </div>
        </>
      )}
    </div>
  )
}
