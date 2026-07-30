import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { AlertTriangle, ArrowRight, Beaker, Gauge, Lightbulb, PiggyBank, Route, ShieldCheck, Sparkles } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getRunFlow } from '@/lib/api'
import DashboardScopeBar, { getDashboardWindow } from '@/components/dashboard/DashboardScopeBar'
import type { RunFlowRecord } from '@/types/api'

type FlowScope = 'workspace' | 'org' | 'platform'
type Risk = 'Low' | 'Medium' | 'High'
type Recommendation = {
  id: string
  title: string
  problem: string
  evidence: string[]
  action: string
  projectedSavings: number
  projectedSavingsPct: number
  risk: Risk
  confidence: 'High' | 'Medium' | 'Directional'
  href: string
  cta: string
  category: string
}

function parseMoney(value: string | null | undefined) {
  const parsed = Number.parseFloat(value ?? '0')
  return Number.isFinite(parsed) ? parsed : 0
}

function money(value: number) {
  if (!Number.isFinite(value)) return '$0'
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}`
  if (Math.abs(value) >= 0.001) return `$${value.toFixed(4)}`
  return `$${value.toFixed(6)}`
}

function percent(value: number) {
  if (!Number.isFinite(value)) return '0%'
  return `${value.toFixed(0)}%`
}

function allowedScope(raw: string | undefined, isPlatformAdmin: boolean, isOrgAdmin: boolean): FlowScope {
  const requested = raw === 'platform' || raw === 'org' || raw === 'workspace' ? raw : undefined
  const fallback: FlowScope = isPlatformAdmin ? 'platform' : isOrgAdmin ? 'org' : 'workspace'
  if (!requested) return fallback
  if (requested === 'platform' && !isPlatformAdmin) return fallback
  if (requested === 'org' && !isOrgAdmin && !isPlatformAdmin) return fallback
  return requested
}

function scopeLabel(scope: FlowScope): 'Platform' | 'Organization' | 'Workspace' {
  if (scope === 'platform') return 'Platform'
  if (scope === 'org') return 'Organization'
  return 'Workspace'
}

function modelName(item: RunFlowRecord) {
  return item.primary_model || item.provider || 'Unknown model'
}

function modelClass(item: RunFlowRecord) {
  const text = `${item.primary_model ?? ''} ${item.provider ?? ''}`.toLowerCase()
  if (text.includes('gpt') || text.includes('openai')) return 'GPT'
  if (text.includes('claude') || text.includes('anthropic')) return 'Claude'
  if (text.includes('gemini') || text.includes('google')) return 'Gemini'
  if (text.includes('llama') || text.includes('local') || text.includes('ollama')) return 'Local'
  if (text.includes('deepseek')) return 'DeepSeek'
  return 'Other'
}

function taskIntent(item: RunFlowRecord) {
  const fields = `${item.prompt} ${item.skill} ${item.agent} ${item.feature_tag ?? ''} ${item.route}`.toLowerCase()
  if (fields.includes('doc') || fields.includes('summar')) return 'Documentation / summarization'
  if (fields.includes('code') || fields.includes('repo') || fields.includes('pull request')) return 'Coding'
  if (fields.includes('search') || fields.includes('research')) return 'Research'
  if (fields.includes('support') || fields.includes('ticket')) return 'Support'
  if (fields.includes('reason') || fields.includes('plan')) return 'Reasoning'
  return item.feature_tag || item.skill || item.agent || 'General'
}

function totalSpend(items: RunFlowRecord[]) {
  return items.reduce((sum, item) => sum + parseMoney(item.total_cost_usd), 0)
}

function generateRecommendations(items: RunFlowRecord[]): Recommendation[] {
  const recommendations: Recommendation[] = []
  const total = totalSpend(items)
  const requests = items.length
  const cached = items.filter((item) => item.cached_input_tokens > 0).length
  const cacheRate = requests > 0 ? (cached / requests) * 100 : 0
  const failures = items.filter((item) => !item.success)
  const failureSpend = totalSpend(failures)
  const localEligible = items.filter((item) => {
    const intent = taskIntent(item).toLowerCase()
    const model = modelClass(item)
    return model !== 'Local' && (intent.includes('summar') || intent.includes('documentation') || intent.includes('support'))
  })
  const localEligibleSpend = totalSpend(localEligible)
  const gptDocs = items.filter((item) => modelClass(item) === 'GPT' && taskIntent(item).toLowerCase().includes('documentation'))
  const gptDocsSpend = totalSpend(gptDocs)
  const reasoningLike = items.filter((item) => {
    const text = `${item.primary_model ?? ''} ${item.route} ${item.prompt}`.toLowerCase()
    return text.includes('reason') || text.includes('o3') || text.includes('o4') || text.includes('gpt-5')
  })
  const reasoningSpend = totalSpend(reasoningLike)
  const toolHeavy = items.filter((item) => item.tool && item.tool !== 'No tool')
  const toolSpend = totalSpend(toolHeavy)
  const slow = items.filter((item) => (item.latency_ms ?? 0) > 8000)
  const slowSpend = totalSpend(slow)

  if (cacheRate < 25 && requests >= 5) {
    const projected = total * 0.18
    recommendations.push({
      id: 'cache-hit-rate',
      title: 'Raise cache hit rate on repeat traffic',
      problem: `Cache hit rate is ${percent(cacheRate)}, which is below the expected 35-45% for repeat enterprise workflows.`,
      evidence: [`${cached.toLocaleString()} cached requests out of ${requests.toLocaleString()}`, `${money(total)} spend in scope`, 'Repeated prompts and documentation/support traffic are good cache candidates'],
      action: 'Enable exact/semantic cache on high-repeat routes and set a cache policy experiment.',
      projectedSavings: projected,
      projectedSavingsPct: total > 0 ? (projected / total) * 100 : 0,
      risk: 'Low',
      confidence: 'Medium',
      href: '/gateway',
      cta: 'Tune cache policy',
      category: 'Cache policy',
    })
  }

  if (gptDocsSpend > 0) {
    const projected = gptDocsSpend * 0.45
    recommendations.push({
      id: 'docs-model-mismatch',
      title: 'Route documentation work to a cheaper high-quality model',
      problem: 'Documentation-style requests are using GPT-class routes where Claude or a smaller model may be sufficient.',
      evidence: [`${gptDocs.length.toLocaleString()} documentation requests on GPT-class models`, `${money(gptDocsSpend)} spend in this segment`, 'Expected 35-45% unit-cost reduction for the segment'],
      action: 'Create a gateway experiment comparing GPT, Claude Sonnet, and local summarization for documentation traffic.',
      projectedSavings: projected,
      projectedSavingsPct: gptDocsSpend > 0 ? 45 : 0,
      risk: 'Medium',
      confidence: 'Directional',
      href: '/experiments',
      cta: 'Launch experiment',
      category: 'Model routing',
    })
  }

  if (localEligibleSpend > 0) {
    const projected = localEligibleSpend * 0.35
    recommendations.push({
      id: 'local-model-lane',
      title: 'Move safe summarization/support traffic to local models',
      problem: 'A portion of repeatable low-risk traffic appears eligible for local model routing.',
      evidence: [`${localEligible.length.toLocaleString()} local-eligible requests`, `${money(localEligibleSpend)} current spend`, 'Summarization/support traffic is often low-risk after quality validation'],
      action: 'Add a local-model route in approval mode, then compare outcome rate before widening traffic.',
      projectedSavings: projected,
      projectedSavingsPct: localEligibleSpend > 0 ? 35 : 0,
      risk: 'Medium',
      confidence: 'Directional',
      href: '/gateway',
      cta: 'Create local route',
      category: 'Local models',
    })
  }

  if (reasoningLike.length > Math.max(3, requests * 0.15)) {
    const projected = reasoningSpend * 0.28
    recommendations.push({
      id: 'reasoning-overuse',
      title: 'Reduce unnecessary reasoning-model usage',
      problem: `${percent(requests > 0 ? (reasoningLike.length / requests) * 100 : 0)} of sampled requests look reasoning-model or premium-route heavy.`,
      evidence: [`${reasoningLike.length.toLocaleString()} reasoning-like requests`, `${money(reasoningSpend)} spend`, 'Many business workflows only need reasoning for planning, not every response'],
      action: 'Add a classifier route that sends only planning/reasoning intents to premium reasoning models.',
      projectedSavings: projected,
      projectedSavingsPct: reasoningSpend > 0 ? 28 : 0,
      risk: 'Medium',
      confidence: 'Medium',
      href: '/gateway',
      cta: 'Review routes',
      category: 'Reasoning control',
    })
  }

  if (toolHeavy.length > Math.max(3, requests * 0.2)) {
    const projected = toolSpend * 0.16
    recommendations.push({
      id: 'tool-overuse',
      title: 'Trim tool calls with MCP filtering and skill selection',
      problem: 'Tool usage is high enough to warrant tool filtering, skill routing, or retrieval narrowing.',
      evidence: [`${toolHeavy.length.toLocaleString()} requests used tools`, `${money(toolSpend)} spend touched tool paths`, 'Tool filtering can reduce latency and avoid irrelevant context'],
      action: 'Use MCP tool filtering to allow only relevant tools per task class, then measure cost and latency deltas.',
      projectedSavings: projected,
      projectedSavingsPct: toolSpend > 0 ? 16 : 0,
      risk: 'Low',
      confidence: 'Medium',
      href: '/mcp',
      cta: 'Open MCP tools',
      category: 'Tool optimization',
    })
  }

  if (slow.length > 0) {
    const projected = slowSpend * 0.12
    recommendations.push({
      id: 'latency-outliers',
      title: 'Investigate latency outliers before they become spend regressions',
      problem: `${slow.length.toLocaleString()} sampled requests crossed 8 seconds latency.`,
      evidence: [`${money(slowSpend)} spend on slow requests`, 'High latency usually correlates with retries, long context, or slow tools', 'Route-level fallback can protect user experience'],
      action: 'Compare slow routes against faster alternatives and add fallback thresholds for high-latency paths.',
      projectedSavings: projected,
      projectedSavingsPct: slowSpend > 0 ? 12 : 0,
      risk: 'Low',
      confidence: 'Medium',
      href: '/model-usage',
      cta: 'Compare models',
      category: 'Latency',
    })
  }

  if (failures.length > 0) {
    const projected = failureSpend * 0.5
    recommendations.push({
      id: 'failed-spend',
      title: 'Recover wasted spend from failed requests',
      problem: 'Failed requests are still consuming cost and tokens.',
      evidence: [`${failures.length.toLocaleString()} failed requests`, `${money(failureSpend)} failed-request spend`, 'Failures should trigger cheaper retry/fallback policies'],
      action: 'Add failure-aware fallback routing and alert on provider/model error spikes.',
      projectedSavings: projected,
      projectedSavingsPct: failureSpend > 0 ? 50 : 0,
      risk: 'Low',
      confidence: 'High',
      href: '/alert-rules',
      cta: 'Create alert',
      category: 'Reliability',
    })
  }

  return recommendations.sort((a, b) => b.projectedSavings - a.projectedSavings).slice(0, 8)
}

function riskClass(risk: Risk) {
  if (risk === 'Low') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  if (risk === 'Medium') return 'bg-amber-50 text-amber-700 border-amber-200'
  return 'bg-rose-50 text-rose-700 border-rose-200'
}

export default async function OptimizationOpportunitiesPage({
  searchParams,
}: {
  searchParams?: { range?: string; scope?: string }
}) {
  const session = await getServerSession(authOptions)
  if (!session?.apiKey) redirect('/login')
  const s = session as unknown as Record<string, unknown>
  const isPlatformAdmin = Boolean(s.isPlatformAdmin)
  const tenantRole = String(s.tenantRole ?? '')
  const isOrgAdmin = isPlatformAdmin || tenantRole === 'org_admin'
  const selectedScope = allowedScope(searchParams?.scope, isPlatformAdmin, isOrgAdmin)
  const win = getDashboardWindow(searchParams?.range ?? '30d')
  const flow = await getRunFlow(session.apiKey, {
    scope: selectedScope,
    mode: 'team-app-agent-model-cost',
    metric: 'cost',
    limit: 1000,
    from: win.from,
    to: win.to,
  })
  const items = flow.items
  const recommendations = generateRecommendations(items)
  const totalProjected = recommendations.reduce((sum, rec) => sum + rec.projectedSavings, 0)
  const total = totalSpend(items)
  const requests = flow.total_runs || items.length

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-[11px] font-semibold text-blue-700">Phase 9</span>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-[-0.05em] text-slate-950">Optimization Opportunities</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Rule-based recommendations backed by current dashboard evidence. This is the bridge from reporting to advisory intelligence.
          </p>
        </div>
        <Link href="/experiments" className="inline-flex items-center gap-1 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100">
          Experiment lab <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        {(['workspace', 'org', 'platform'] as FlowScope[]).map((scope) => {
          const disabled = (scope === 'platform' && !isPlatformAdmin) || (scope === 'org' && !isOrgAdmin && !isPlatformAdmin)
          if (disabled) return null
          const active = selectedScope === scope
          return (
            <Link
              key={scope}
              href={`/optimization-opportunities?scope=${scope}&range=${win.range}`}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${active ? 'bg-blue-600 text-white shadow-sm' : 'border border-slate-200 bg-white text-slate-600 hover:bg-blue-50'}`}
            >
              {scopeLabel(scope)}
            </Link>
          )
        })}
      </div>

      <DashboardScopeBar
        scope={scopeLabel(selectedScope)}
        context={`${requests.toLocaleString()} requests analyzed for recommendations`}
        activeRange={win.range}
        basePath={`/optimization-opportunities?scope=${selectedScope}`}
        dimensions={['Intent', 'Model', 'Route', 'Cache', 'Tools', 'Latency', 'Outcome', 'Experiment']}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Opportunities</p>
            <Lightbulb className="h-5 w-5 text-blue-700" />
          </div>
          <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{recommendations.length}</p>
          <p className="mt-1 text-xs text-slate-500">Rule-backed cards from sampled telemetry</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Projected savings</p>
            <PiggyBank className="h-5 w-5 text-emerald-700" />
          </div>
          <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{money(totalProjected)}</p>
          <p className="mt-1 text-xs text-slate-500">{percent(total > 0 ? (totalProjected / total) * 100 : 0)} of sampled spend</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Scope spend</p>
            <Gauge className="h-5 w-5 text-blue-700" />
          </div>
          <p className="mt-2 font-display text-3xl font-semibold tracking-[-0.045em] text-slate-950">{money(total)}</p>
          <p className="mt-1 text-xs text-slate-500">{items.length.toLocaleString()} sampled records</p>
        </div>
      </div>

      {recommendations.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white/80 p-10 text-center shadow-sm">
          <Sparkles className="mx-auto h-8 w-8 text-blue-600" />
          <h2 className="mt-4 text-lg font-semibold text-slate-950">No strong recommendations yet</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-slate-500">
            Send richer model, route, tool, cache, and outcome telemetry. RunLedger will start producing advisory cards as usage patterns emerge.
          </p>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          {recommendations.map((rec) => (
            <div key={rec.id} className="rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-semibold text-blue-700">{rec.category}</span>
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${riskClass(rec.risk)}`}>{rec.risk} risk</span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold text-slate-600">{rec.confidence} confidence</span>
                  </div>
                  <h2 className="mt-3 text-lg font-semibold text-slate-950">{rec.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{rec.problem}</p>
                </div>
                <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-right text-emerald-800">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em]">Projected</p>
                  <p className="font-display text-2xl font-semibold tracking-[-0.04em]">{money(rec.projectedSavings)}</p>
                  <p className="text-xs">{percent(rec.projectedSavingsPct)} segment lift</p>
                </div>
              </div>
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Evidence</p>
                <div className="mt-2 grid gap-2 md:grid-cols-3">
                  {rec.evidence.map((item) => (
                    <div key={item} className="rounded-xl bg-white px-3 py-2 text-xs font-medium text-slate-600 shadow-sm">{item}</div>
                  ))}
                </div>
              </div>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-2 text-sm text-slate-600">
                  {rec.risk === 'High' ? <AlertTriangle className="mt-0.5 h-4 w-4 text-rose-600" /> : <ShieldCheck className="mt-0.5 h-4 w-4 text-emerald-600" />}
                  <span>{rec.action}</span>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Link href={rec.href} className="inline-flex items-center gap-1 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-100">
                    {rec.cta}
                  </Link>
                  <Link href={`/experiments?recommendation=${rec.id}`} className="inline-flex items-center gap-1 rounded-xl bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700">
                    <Beaker className="h-3.5 w-3.5" /> Experiment
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <Route className="mt-0.5 h-5 w-5 text-blue-700" />
          <div>
            <h2 className="font-semibold text-slate-950">How recommendations are generated</h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              This first pass uses deterministic rules over request-flow telemetry: model mismatch, cache hit rate, reasoning-heavy routes, tool overuse, latency outliers, failed spend, local-model eligibility, and outcome success. Phase 13 can replace or augment these rules with a learned advisory engine.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
