import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { ArrowLeft, Route } from 'lucide-react'
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
    zoom?: string
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
  return flowModes.includes(value as RequestFlowMode) ? (value as RequestFlowMode) : 'prompt-skill-agent-model-tool-result'
}

function parseMetric(value: string | undefined): RequestFlowMetric {
  return flowMetrics.includes(value as RequestFlowMetric) ? (value as RequestFlowMetric) : 'requests'
}

function parseScope(value: string | undefined): RequestFlowScope {
  return flowScopes.includes(value as RequestFlowScope) ? (value as RequestFlowScope) : 'workspace'
}

function parseDensity(value: string | undefined): RequestFlowDensity {
  return flowDensities.includes(value as RequestFlowDensity) ? (value as RequestFlowDensity) : 'presentation'
}

function parseNumber(value: string | undefined, fallback: number) {
  const parsed = Number.parseFloat(value ?? '')
  return Number.isFinite(parsed) ? parsed : fallback
}

function exitHref(mode: RequestFlowMode, metric: RequestFlowMetric, scope: RequestFlowScope, density: RequestFlowDensity, topN: number, collapseSmall: boolean) {
  const params = new URLSearchParams({
    mode,
    metric,
    scope,
    density,
    top: String(topN),
  })
  if (!collapseSmall) params.set('collapse', '0')
  return `/request-flow?${params.toString()}`
}

export default async function RequestFlowFocusPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const mode = parseMode(searchParams.mode)
  const metric = parseMetric(searchParams.metric)
  const density = parseDensity(searchParams.density)
  const topN = Math.trunc(parseNumber(searchParams.top, 12))
  const zoom = parseNumber(searchParams.zoom, 1)
  const collapseSmall = searchParams.collapse !== '0'
  const requestedScope = parseScope(searchParams.scope)
  let scope = requestedScope
  let flow: RunFlowResponse

  try {
    flow = await getRunFlow(session.apiKey, { scope, mode, metric, limit: 1000 })
  } catch {
    scope = 'workspace'
    flow = await getRunFlow(session.apiKey, { scope, mode, metric, limit: 1000 })
  }

  return (
    <div className="fixed inset-0 z-[100] overflow-auto bg-[#f4f8fc] p-4 text-slate-950">
      <div className="sticky top-0 z-20 mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-[#f4f8fc]/95 p-3 shadow-sm backdrop-blur">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
            <Route className="h-3.5 w-3.5" />
            Focus mode
          </div>
          <h1 className="mt-2 font-display text-2xl font-semibold tracking-[-0.03em]">AI Request Flow</h1>
          <p className="text-sm text-slate-500">Large canvas with pan, zoom, density, top-N, and SVG export for demos and debugging.</p>
        </div>
        <Link
          href={exitHref(mode, metric, scope, density, topN, collapseSmall)}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:border-blue-300 hover:text-blue-700"
        >
          <ArrowLeft className="h-4 w-4" /> Back to page
        </Link>
      </div>

      <RequestFlowSankey
        flow={flow}
        scope={scope}
        mode={mode}
        metric={metric}
        density={density}
        topN={topN}
        zoom={zoom}
        collapseSmall={collapseSmall}
        focus
        basePath="/request-flow/focus"
      />
    </div>
  )
}
