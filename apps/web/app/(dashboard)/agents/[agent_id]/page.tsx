import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAgent, getAgentStats, getAgentRuns, getBudgetDetailBuildPosture, getBudgetControlBuildPosture } from '@/lib/api'
import type { AgentResponse, AgentStats, WorkflowRunSummary } from '@/types/api'

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
    active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    paused: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    retired: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
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

function RunRow({ run }: { run: WorkflowRunSummary }) {
  return (
    <tr className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
      <td className="px-4 py-3 text-xs font-mono text-slate-600 dark:text-slate-400">
        {run.id.slice(0, 8)}
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusColor(run.status)}`}>
          {run.status}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(run.total_cost)}</td>
      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{compact(run.total_tokens)}</td>
      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{duration(run.total_duration_ms)}</td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {new Date(run.created_at).toLocaleString()}
      </td>
    </tr>
  )
}

export default async function AgentDetailPage({ params }: { params: { agent_id: string } }) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let agent: AgentResponse | null = null
  let stats: AgentStats | null = null
  let runs: WorkflowRunSummary[] = []

  try {
    ;[agent, stats] = await Promise.all([
      getAgent(session.apiKey, params.agent_id),
      getAgentStats(session.apiKey, params.agent_id),
    ])
    const runsData = await getAgentRuns(session.apiKey, params.agent_id, { limit: 20 })
    runs = runsData.runs
  } catch {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-sm text-slate-500">Agent not found or API unavailable.</p>
      </div>
    )
  }

  if (!agent) return null

  const budgetBuildPosture = await getBudgetDetailBuildPosture(session.apiKey).catch(() => null)
  const budgetControlBuildPosture = await getBudgetControlBuildPosture(session.apiKey).catch(() => null)

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link href="/agents" className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          Agents
        </Link>
        <span className="text-slate-400">/</span>
        <h1 className="text-xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
          {agent.name}
        </h1>
        <span className={`ml-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusColor(agent.status)}`}>
          {agent.status}
        </span>
        <Link
          href={`/agents/${params.agent_id}/memory`}
          className="ml-auto rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          Memory →
        </Link>
      </div>

      {agent.description && (
        <p className="text-sm text-slate-600 dark:text-slate-400">{agent.description}</p>
      )}

      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-blue-100 px-2.5 py-1 text-[11px] font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
          {agent.agent_type.replace('_', '-')}
        </span>
        {agent.default_model && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {agent.default_model}
          </span>
        )}
        {agent.owner && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            Owner: {agent.owner}
          </span>
        )}
        {agent.policy_profile && (
          <span className="rounded-full bg-violet-100 px-2.5 py-1 text-[11px] font-medium text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
            Policy: {agent.policy_profile}
          </span>
        )}
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
              <p className="text-xs text-slate-500 dark:text-slate-400">Feature Budgets</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{budgetBuildPosture.budget_context.feature_budgets}</p>
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

      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Total Runs" value={String(stats.total_runs)} sub={`${stats.completed_runs} completed, ${stats.failed_runs} failed`} />
          <StatCard label="Success Rate" value={stats.success_rate != null ? `${(stats.success_rate * 100).toFixed(1)}%` : '-'} />
          <StatCard label="Total Cost" value={money(stats.total_cost)} sub={`${compact(stats.total_tokens)} tokens`} />
          <StatCard label="Avg Duration" value={duration(stats.avg_duration_ms)} sub={stats.last_run_at ? `Last: ${new Date(stats.last_run_at).toLocaleDateString()}` : 'No runs yet'} />
        </div>
      )}

      {stats && (stats.models_used.length > 0 || stats.tools_used.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {stats.models_used.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Models Used</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {stats.models_used.map((m) => (
                  <span key={m} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">{m}</span>
                ))}
              </div>
            </div>
          )}
          {stats.tools_used.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Tools Used</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {stats.tools_used.map((t) => (
                  <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">{t}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="rounded-2xl border border-slate-200 bg-white/90 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
        <div className="border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <h2 className="text-sm font-semibold text-slate-950 dark:text-slate-50">Recent Runs</h2>
        </div>
        {runs.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">No runs yet for this agent.</div>
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
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <RunRow key={run.id} run={run} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
