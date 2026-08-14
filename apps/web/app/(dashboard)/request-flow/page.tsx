import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { ArrowRight, Expand, GitBranch, Layers3, Route as RouteIcon, Search, ShieldCheck } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getRunFlow } from '@/lib/api'
import RequestFlowSankey, {
  type RequestFlowDensity,
  type RequestFlowMetric,
  type RequestFlowMode,
  type RequestFlowScope,
} from '@/components/dashboard/RequestFlowSankey'
import type { RunFlowResponse } from '@/types/api'

interface PageProps {
  searchParams: {
    mode?: string
    metric?: string
    scope?: string
    density?: string
    top?: string
    collapse?: string
  }
}

const flowModes: RequestFlowMode[] = [
  'request-intent-model-result',
  'user-intent-model',
  'prompt-skill-agent-model-tool-result',
  'request-route-provider-outcome',
  'workspace-app-agent-model-cost',
]

const flowMetrics: RequestFlowMetric[] = ['requests', 'cost', 'tokens', 'savings']
const flowScopes: RequestFlowScope[] = ['workspace', 'org', 'platform']
const flowDensities: RequestFlowDensity[] = ['compact', 'comfortable', 'presentation']

function parseMode(value: string | undefined): RequestFlowMode {
  if (value === 'team-app-agent-model-cost') return 'workspace-app-agent-model-cost'
  return flowModes.includes(value as RequestFlowMode) ? (value as RequestFlowMode) : 'request-intent-model-result'
}

function parseMetric(value: string | undefined): RequestFlowMetric {
  return flowMetrics.includes(value as RequestFlowMetric) ? (value as RequestFlowMetric) : 'requests'
}

function parseScope(value: string | undefined): RequestFlowScope {
  return flowScopes.includes(value as RequestFlowScope) ? (value as RequestFlowScope) : 'workspace'
}

function parseDensity(value: string | undefined): RequestFlowDensity {
  return flowDensities.includes(value as RequestFlowDensity) ? (value as RequestFlowDensity) : 'comfortable'
}

function parseTopN(value: string | undefined) {
  const parsed = Number.parseInt(value ?? '', 10)
  return Number.isFinite(parsed) ? parsed : 8
}

function pct(value: number, total: number) {
  if (total <= 0) return '0%'
  return `${Math.round((value / total) * 100)}%`
}

export default async function RequestFlowPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const mode = parseMode(searchParams.mode)
  const metric = parseMetric(searchParams.metric)
  const density = parseDensity(searchParams.density)
  const topN = parseTopN(searchParams.top)
  const collapseSmall = searchParams.collapse !== '0'
  const requestedScope = parseScope(searchParams.scope)
  let scope = requestedScope
  let flow: RunFlowResponse
  try {
    flow = await getRunFlow(session.apiKey, { scope, mode, metric, limit: 500 })
  } catch {
    scope = 'workspace'
    flow = await getRunFlow(session.apiKey, { scope, mode, metric, limit: 500 })
  }
  const items = flow.items
  const uniqueIntents = new Set(items.map((run) => run.feature_tag || 'General / Untagged')).size
  const uniqueModels = new Set(items.map((run) => run.primary_model || 'Model Unknown')).size
  const succeeded = items.filter((run) => run.success).length

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
            AI Request Flow
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Follow AI traffic from incoming request to intent, skill, agent, model, tool, route, provider, outcome, and cost. Click any flow line to inspect the matching requests.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/analytics?scope=${scope}&view=overview`}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-300 dark:bg-white dark:text-slate-700 dark:hover:border-blue-300 dark:hover:text-blue-700"
          >
            Analytics Overview <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/request-explorer"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-300 dark:bg-white dark:text-slate-700 dark:hover:border-blue-300 dark:hover:text-blue-700"
          >
            Request Explorer <Search className="h-4 w-4" />
          </Link>
          <Link
            href={`/request-flow/focus?mode=${mode}&metric=${metric}&scope=${scope}&density=presentation&top=${topN}${collapseSmall ? '' : '&collapse=0'}`}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-slate-300 dark:bg-white dark:text-slate-700 dark:hover:border-blue-300 dark:hover:text-blue-700"
          >
            Focus Mode <Expand className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-20 text-center dark:border-slate-700 dark:bg-slate-950/30">
          <RouteIcon className="h-10 w-10 text-slate-400 dark:text-slate-500" />
          <h2 className="mt-4 text-lg font-semibold text-slate-700 dark:text-slate-300">No request flow data yet</h2>
          <p className="mt-1.5 max-w-md text-sm text-slate-500 dark:text-slate-400">
            Send AI requests through the RunLedger gateway to see traffic flow visualized here. The Sankey diagram will show how requests route through intents, models, and outcomes.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            {[
              { label: 'Runs sampled', value: items.length.toLocaleString(), icon: GitBranch },
              { label: 'Intent groups', value: uniqueIntents.toLocaleString(), icon: Layers3 },
              { label: 'Models observed', value: uniqueModels.toLocaleString(), icon: RouteIcon },
              { label: 'Success rate', value: pct(succeeded, items.length), icon: ShieldCheck },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">{label}</p>
                  <Icon className="h-4 w-4 text-teal-600 dark:text-teal-300" />
                </div>
                <p className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">{value}</p>
              </div>
            ))}
          </div>

          <RequestFlowSankey
            flow={flow}
            scope={scope}
            mode={mode}
            metric={metric}
            density={density}
            topN={topN}
            collapseSmall={collapseSmall}
          />

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950/45">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Request Analysis Flow</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Start broad, then drill into evidence</h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Use Analytics Overview for scope health, Request Flow for routing causality, and Request Explorer when you need the exact run, prompt path, and gateway evidence.
              </p>
            </div>
            <Link
              href="/request-explorer"
              className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-800 dark:bg-slate-950/45 dark:hover:border-blue-400 dark:hover:bg-slate-900"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Drill-in</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Open Request Explorer</h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Filter the exact requests behind a suspicious edge, inspect run detail, and correlate route, model, cache, and outcome behavior.
              </p>
            </Link>
            <Link
              href={`/request-flow/focus?mode=${mode}&metric=${metric}&scope=${scope}&density=presentation&top=${topN}${collapseSmall ? '' : '&collapse=0'}`}
              className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50/70 dark:border-slate-800 dark:bg-slate-950/45 dark:hover:border-blue-400 dark:hover:bg-slate-900"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Presentation Mode</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-950 dark:text-white">Launch Focus Mode</h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Expand the same flow into a larger canvas for demos, incident review, and dense route-to-outcome debugging without changing the underlying dataset.
              </p>
            </Link>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-950/35 dark:text-slate-300">
            <p className="font-semibold text-slate-950 dark:text-white">Scope note</p>
            <p className="mt-1">
              This page uses the backend flow aggregate API. Workspace scope is available to workspace access; org scope requires org admin; platform scope requires platform admin.
            </p>
          </div>
        </>
      )}
    </div>
  )
}
