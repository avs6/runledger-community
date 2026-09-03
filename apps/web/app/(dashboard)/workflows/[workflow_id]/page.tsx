import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getWorkflow, getWorkflowRuns, getWorkflowCost, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getWorkflowDetailCrossFeaturePosture, getBuildInternalPosture, getWorkflowDetailLoopPosture } from '@/lib/api'
import type { WorkflowDefinitionResponse, WorkflowRunResponse, WorkflowCostAttribution, WorkflowDetailCrossFeaturePosture, BuildInternalPosture, WorkflowDetailLoopPosture } from '@/types/api'

function money(v: number | null | undefined) {
  if (!v) return '$0.00'
  if (v >= 1) return `$${v.toFixed(2)}`
  if (v >= 0.001) return `$${v.toFixed(4)}`
  return `$${v.toFixed(6)}`
}

function compact(value: number) {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function duration(ms: number | null | undefined) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function statusColor(status: string) {
  const map: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    pending: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    cancelled: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  }
  return map[status] || map.pending
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm ring-1 ring-white/70 dark:border-slate-700 dark:bg-slate-900/80">
      <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-950 dark:text-slate-50">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

export default async function WorkflowDetailPage({ params }: { params: { workflow_id: string } }) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let wf: WorkflowDefinitionResponse | null = null
  let runs: WorkflowRunResponse[] = []
  let cost: WorkflowCostAttribution | null = null
  let totalRuns = 0

  try {
    ;[wf, cost] = await Promise.all([
      getWorkflow(session.apiKey, params.workflow_id),
      getWorkflowCost(session.apiKey, params.workflow_id),
    ])
    const runsData = await getWorkflowRuns(session.apiKey, params.workflow_id, { limit: 30 })
    runs = runsData.runs
    totalRuns = runsData.total
  } catch {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-slate-500">Workflow not found or API unavailable.</p>
      </div>
    )
  }

  if (!wf) return null

  const budgetBuildPosture = await getBudgetDetailBuildPosture(session.apiKey).catch(() => null)
  const budgetControlBuildPosture = await getBudgetControlBuildPosture(session.apiKey).catch(() => null)
  const crossFeaturePosture: WorkflowDetailCrossFeaturePosture | null = await getWorkflowDetailCrossFeaturePosture(session.apiKey).catch(() => null)
  const buildPosture: BuildInternalPosture | null = await getBuildInternalPosture(session.apiKey).catch(() => null)
  const loopPosture: WorkflowDetailLoopPosture | null = await getWorkflowDetailLoopPosture(session.apiKey).catch(() => null)

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link href="/workflows" className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          Workflows
        </Link>
        <span className="text-slate-400">/</span>
        <h1 className="text-xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
          {wf.name}
        </h1>
        <span className={`ml-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${wf.status === 'active' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>
          {wf.status}
        </span>
      </div>

      {wf.description && (
        <p className="text-sm text-slate-600 dark:text-slate-400">{wf.description}</p>
      )}

      {budgetBuildPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Budget &amp; Build Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetBuildPosture.budget_context.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workflow Runs (30d)</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetBuildPosture.build_context.workflow_runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">30d Spend</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${budgetBuildPosture.spend_context.total_spend_30d.toFixed(2)}</p>
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

      {crossFeaturePosture && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-5 shadow-sm dark:border-blue-900 dark:bg-blue-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Organization &amp; Access Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workspace</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.org_context.workspace_name}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Access Groups</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.org_context.access_groups}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">API Keys</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.org_context.api_keys}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.org_context.hub_models}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-blue-200 dark:border-blue-800">
            <Link href="/organization" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Organization</Link>
            <Link href="/access-groups" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Access Groups</Link>
            <Link href="/api-keys" className="text-xs text-blue-600 hover:underline dark:text-blue-400">API Keys</Link>
            <Link href="/ai-hub" className="text-xs text-blue-600 hover:underline dark:text-blue-400">AI Hub</Link>
          </div>
        </div>
      )}

      {crossFeaturePosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5 shadow-sm dark:border-violet-900 dark:bg-violet-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">Gateway &amp; Routing Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Providers</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.gateway_context.distinct_providers}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Routes</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.gateway_context.active_routes}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Guardrail Rules</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.gateway_context.guardrail_rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cache Configs</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.gateway_context.cache_configs}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-violet-200 dark:border-violet-800">
            <Link href="/provider-profiles" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Provider Profiles</Link>
            <Link href="/guardrails" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
            <Link href="/gateway?tab=cache" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Response Cache</Link>
            <Link href="/gateway?tab=rate-limits" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Rate Limits</Link>
          </div>
        </div>
      )}

      {crossFeaturePosture && (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm dark:border-cyan-900 dark:bg-cyan-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">Observe &amp; Analytics Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Runs (30d)</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.observe_context.runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Provider Calls (30d)</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.observe_context.provider_calls_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Distinct Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.observe_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Cost (30d)</p>
              <p className="mt-1 text-lg font-semibold text-cyan-600 dark:text-cyan-400">${crossFeaturePosture.observe_context.total_cost_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800">
            <Link href="/analytics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Analytics Overview</Link>
            <Link href="/analytics?tab=request-explorer" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Explorer</Link>
            <Link href="/analytics?tab=model-usage" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Model Usage</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Cost &amp; Savings</Link>
          </div>
        </div>
      )}

      {crossFeaturePosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">FinOps &amp; Budget Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Active Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.finops_context.active_budgets}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Billing Periods</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{crossFeaturePosture.finops_context.billing_periods}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Budget Limit</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${crossFeaturePosture.finops_context.total_budget_limit.toFixed(2)}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">30d Spend</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${crossFeaturePosture.finops_context.total_spend_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/budgets" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
            <Link href="/billing" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Billing Periods</Link>
          </div>
        </div>
      )}

      {buildPosture && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm dark:border-rose-900 dark:bg-rose-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400">Build &amp; Improve Loop</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-3">
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Playground 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.playground_context.sessions_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.evaluation_context.experiments}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Score Events 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.scorecards_context.score_events_30d}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-rose-200 dark:border-rose-800">
            <Link href="/playground" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Playground</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Evaluation Studio</Link>
            <Link href="/model-scorecards" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Model Scorecards</Link>
          </div>
        </div>
      )}

      {loopPosture && (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm dark:border-cyan-900 dark:bg-cyan-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">Runs &amp; Workflow Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2">
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Runs (30d)</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{loopPosture.runs_context.runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Distinct Workflows</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{loopPosture.runs_context.distinct_workflows}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800">
            <Link href="/analytics?tab=runs" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Runs List</Link>
          </div>
        </div>
      )}

      {loopPosture && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Chargeback &amp; Cost Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2">
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Chargeback Rules</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{loopPosture.chargeback_context.rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-emerald-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cost (30d)</p>
              <p className="mt-1 text-lg font-semibold text-emerald-600 dark:text-emerald-400">${loopPosture.chargeback_context.cost_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-emerald-200 dark:border-emerald-800">
            <Link href="/chargeback" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Chargeback Rules</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-emerald-600 hover:underline dark:text-emerald-400">Cost &amp; Savings</Link>
          </div>
        </div>
      )}

      {loopPosture && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm dark:border-rose-900 dark:bg-rose-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400">Optimization &amp; Eval Loop</p>
          <div className="mt-3 grid gap-3 grid-cols-2">
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Replay Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{loopPosture.optimization_context.replay_experiments}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{loopPosture.eval_context.experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-rose-200 dark:border-rose-800">
            <Link href="/optimization-opportunities" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Optimization Opportunities</Link>
            <Link href="/evaluation" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Evaluation Studio</Link>
          </div>
        </div>
      )}

      {cost && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Runs" value={String(cost.total_runs)} />
          <StatCard label="Total Cost" value={money(cost.total_cost)} />
          <StatCard label="Avg Cost / Run" value={money(cost.avg_cost_per_run)} />
          <StatCard label="Steps Defined" value={String(wf.steps_schema.length)} />
        </div>
      )}

      {cost && cost.cost_by_step.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
          <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
            <h2 className="text-sm font-semibold text-slate-950 dark:text-slate-50">Cost by Step</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-3">Step</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Total Cost</th>
                  <th className="px-4 py-3">Avg Cost</th>
                  <th className="px-4 py-3">Invocations</th>
                </tr>
              </thead>
              <tbody>
                {cost.cost_by_step.map((s, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="px-4 py-3 text-xs font-medium text-slate-700 dark:text-slate-300">{s.step_name}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{s.step_type}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(s.total_cost)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(s.avg_cost)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{s.invocation_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold text-slate-950 dark:text-slate-50">
            Runs ({totalRuns})
          </h2>
        </div>
        {runs.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">No runs recorded for this workflow.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500 dark:border-slate-800">
                  <th className="px-4 py-3">Run ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Tokens</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Steps</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
                    <td className="px-4 py-3">
                      <Link href={`/workflows/${wf.id}/runs/${run.id}`} className="text-xs font-mono text-blue-600 hover:underline dark:text-blue-400">
                        {run.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusColor(run.status)}`}>
                        {run.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(run.total_cost)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{compact(run.total_tokens)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{duration(run.total_duration_ms)}</td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{run.steps.length}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
