import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAgent, getAgentStats, getAgentRuns, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getAgentDetailGovernancePosture } from '@/lib/api'
import type { AgentResponse, AgentStats, WorkflowRunSummary } from '@/types/api'
import { num } from '@/lib/utils'

function money(v: number | null | undefined) {
  const n = num(v)
  if (!n) return '$0.00'
  if (num(n) >= 1) return `$${num(n).toFixed(2)}`
  if (num(n) >= 0.001) return `$${num(n).toFixed(4)}`
  return `$${num(n).toFixed(6)}`
}

function compact(value: number) {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function duration(ms: number | null | undefined) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(num(ms) / 1000).toFixed(1)}s`
}

const statusColors: Record<string, string> = {
  completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  pending: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  failed: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  cancelled: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  paused: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  retired: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
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
      <div className="p-6">
        <p className="text-xs text-slate-500">Agent not found or API unavailable.</p>
        <Link href="/agents" className="mt-2 inline-block text-xs text-blue-600 hover:underline dark:text-blue-400">Back to Agents</Link>
      </div>
    )
  }

  if (!agent) return null

  const budgetBuildPosture = await getBudgetDetailBuildPosture(session.apiKey).catch(() => null)
  const budgetControlBuildPosture = await getBudgetControlBuildPosture(session.apiKey).catch(() => null)
  const governancePosture = await getAgentDetailGovernancePosture(session.apiKey).catch(() => null)

  return (
    <div className="space-y-3">
      {/* ── Header ───────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25">
            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Link href="/agents" className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">Agents</Link>
              <span className="text-[10px] text-slate-300 dark:text-slate-600">/</span>
            </div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-900 dark:text-white">{agent.name}</h1>
              <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase ${statusColors[agent.status] || statusColors.pending}`}>{agent.status}</span>
            </div>
            {agent.description && <p className="text-xs text-slate-500 dark:text-slate-400">{agent.description}</p>}
          </div>
        </div>
        <Link
          href={`/agents/${params.agent_id}/memory`}
          className="rounded-lg bg-gradient-to-r from-blue-500 to-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:from-blue-600 hover:to-indigo-700 transition-colors"
        >
          Memory →
        </Link>
      </div>

      {/* ── Agent meta chips ─────────────────────── */}
      <div className="flex flex-wrap gap-1.5">
        <span className="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-[10px] font-semibold text-blue-700 dark:text-blue-300">{agent.agent_type.replace('_', '-')}</span>
        {agent.default_model && <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300">{agent.default_model}</span>}
        {agent.owner && <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300">Owner: {agent.owner}</span>}
        {agent.policy_profile && <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">Policy: {agent.policy_profile}</span>}
      </div>

      {/* ── KPI strip ────────────────────────────── */}
      {stats && (
        <div className="grid grid-cols-4 gap-2">
          {[
            { label: 'Total Runs', value: String(stats.total_runs), sub: `${stats.completed_runs} ok · ${stats.failed_runs} fail` },
            { label: 'Success Rate', value: stats.success_rate != null ? `${(num(stats.success_rate) * 100).toFixed(1)}%` : '-' },
            { label: 'Total Cost', value: money(stats.total_cost), accent: true },
            { label: 'Avg Duration', value: duration(stats.avg_duration_ms), sub: stats.last_run_at ? `Last: ${new Date(stats.last_run_at).toLocaleDateString()}` : '' },
          ].map(({ label, value, sub, accent }) => (
            <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
              <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
              <p className={`text-sm font-bold ${accent ? 'text-blue-600 dark:text-blue-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
              {sub && <p className="text-[9px] text-slate-400 truncate">{sub}</p>}
            </div>
          ))}
        </div>
      )}

      {/* ── Posture cards (compact) ──────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {budgetBuildPosture && (
          <div className="rounded-lg border border-emerald-200/60 dark:border-emerald-800/40 bg-emerald-50/30 dark:bg-emerald-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-1">Budget Context</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{budgetBuildPosture.budget_context.active_budgets} active</span>
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">${num(budgetBuildPosture.spend_context.total_spend_30d).toFixed(2)} 30d</span>
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{budgetBuildPosture.budget_context.feature_budgets} features</span>
              {budgetBuildPosture.budget_context.breach_count > 0 && <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] font-semibold text-rose-700 dark:text-rose-300">{budgetBuildPosture.budget_context.breach_count} breached</span>}
            </div>
            <div className="flex flex-wrap gap-1.5 mt-1.5 pt-1.5 border-t border-emerald-200/60 dark:border-emerald-800/40">
              <Link href="/budgets" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
              <Link href="/analytics?tab=economics" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Economics</Link>
              <Link href="/model-scorecards" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Scorecards</Link>
            </div>
          </div>
        )}

        {budgetControlBuildPosture && (
          <div className="rounded-lg border border-emerald-200/60 dark:border-emerald-800/40 bg-emerald-50/30 dark:bg-emerald-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-1">Budget Control</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{budgetControlBuildPosture.budget_policy.active_budgets} active</span>
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{num(budgetControlBuildPosture.budget_policy.avg_utilization_pct).toFixed(1)}% util</span>
              {budgetControlBuildPosture.budget_policy.breached_budgets > 0 && <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-2 py-0.5 text-[10px] font-semibold text-rose-700 dark:text-rose-300">{budgetControlBuildPosture.budget_policy.breached_budgets} breached</span>}
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] text-emerald-700 dark:text-emerald-300">{Object.keys(budgetControlBuildPosture.scope_context).length} scopes</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-1.5 pt-1.5 border-t border-emerald-200/60 dark:border-emerald-800/40">
              <Link href="/budgets" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Budgets</Link>
              <Link href="/budgets?tab=overrides" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Overrides</Link>
              <Link href="/billing" className="text-[10px] text-emerald-600 hover:underline dark:text-emerald-400">Billing</Link>
            </div>
          </div>
        )}

        {governancePosture && (
          <div className="rounded-lg border border-violet-200/60 dark:border-violet-800/40 bg-violet-50/30 dark:bg-violet-950/20 px-3 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400 mb-1">Governance</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.guardrail_context.rules} rules</span>
              <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.guardrail_context.events_30d} events</span>
              <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.safety_context.capture_policies} capture</span>
              <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.observe_context.runs_30d} runs</span>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-1.5 pt-1.5 border-t border-violet-200/60 dark:border-violet-800/40">
              <Link href="/guardrails" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
              <Link href="/security" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Security</Link>
              <Link href="/evaluation" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Eval Studio</Link>
              <Link href="/runs" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Runs</Link>
            </div>
          </div>
        )}
      </div>

      {/* ── Models & Tools ────────────────────────── */}
      {stats && (stats.models_used.length > 0 || stats.tools_used.length > 0) && (
        <div className="grid gap-2 sm:grid-cols-2">
          {stats.models_used.length > 0 && (
            <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Models Used</p>
              <div className="flex flex-wrap gap-1">
                {stats.models_used.map((m) => (
                  <Link key={m} href={`/runs?model=${encodeURIComponent(m)}`} className="rounded-full bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-800/40 transition-colors">{m}</Link>
                ))}
              </div>
            </div>
          )}
          {stats.tools_used.length > 0 && (
            <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1">Tools Used</p>
              <div className="flex flex-wrap gap-1">
                {stats.tools_used.map((t) => (
                  <span key={t} className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300">{t}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Recent Runs ──────────────────────────── */}
      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 overflow-hidden">
        <div className="border-b border-slate-100 dark:border-slate-700/40 px-3 py-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold text-slate-900 dark:text-white">Recent Runs</h2>
          <Link href={`/runs?agent=${params.agent_id}`} className="text-[10px] text-blue-600 hover:underline dark:text-blue-400">View all →</Link>
        </div>
        {runs.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-400">No runs yet for this agent.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700/40 bg-slate-50/80 dark:bg-slate-800/60">
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Run ID</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Cost</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Tokens</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Duration</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/60 dark:divide-slate-700/30">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="px-3 py-1.5">
                      <Link href={`/runs/${run.id}`} className="font-mono text-blue-600 dark:text-blue-400 hover:underline">{run.id.slice(0, 8)}</Link>
                    </td>
                    <td className="px-3 py-1.5">
                      <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase ${statusColors[run.status] || statusColors.pending}`}>{run.status}</span>
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-slate-600 dark:text-slate-400">{money(run.total_cost)}</td>
                    <td className="px-3 py-1.5 text-right text-slate-600 dark:text-slate-400">{compact(run.total_tokens)}</td>
                    <td className="px-3 py-1.5 text-right font-mono text-slate-600 dark:text-slate-400">{duration(run.total_duration_ms)}</td>
                    <td className="px-3 py-1.5 text-right text-slate-500 whitespace-nowrap">{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Quick nav ─────────────────────────────── */}
      <div className="flex flex-wrap gap-1.5">
        {[
          { label: 'Agents', href: '/agents' },
          { label: 'Runs', href: '/runs' },
          { label: 'Analytics', href: '/analytics' },
          { label: 'Guardrails', href: '/guardrails' },
          { label: 'Budgets', href: '/budgets' },
          { label: 'Evaluation', href: '/evaluation' },
        ].map(({ label, href }) => (
          <Link key={label} href={href} className="rounded-full bg-blue-100 dark:bg-blue-900/30 px-2.5 py-1 text-[10px] font-semibold text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800/40 transition-colors">{label}</Link>
        ))}
      </div>
    </div>
  )
}
