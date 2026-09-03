import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import Link from 'next/link'
import { getPlaygroundSessions, getPlaygroundHistory, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getPlaygroundOrgGatewayPosture, getPlaygroundObservePosture, getBuildInternalPosture } from '@/lib/api'
import type { PlaygroundSessionResponse, PlaygroundRequestResponse, PlaygroundOrgGatewayPosture, PlaygroundObservePosture, BuildInternalPosture } from '@/types/api'

function money(v: number | null | undefined) {
  if (!v) return '$0.00'
  if (v >= 1) return `$${v.toFixed(2)}`
  if (v >= 0.001) return `$${v.toFixed(4)}`
  return `$${v.toFixed(6)}`
}

function timeAgo(iso: string) {
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function statusColor(s: string) {
  const map: Record<string, string> = {
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    pending: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  }
  return map[s] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

function modeBadge(m: string) {
  const map: Record<string, string> = {
    single: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    conversation: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
    compare: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  }
  return map[m] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

function SessionCard({ s }: { s: PlaygroundSessionResponse }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm ring-1 ring-white/70 dark:border-slate-700 dark:bg-slate-900/80">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-slate-900 dark:text-slate-50">
          {s.name || 'Untitled Session'}
        </h3>
        <div className="flex gap-1.5">
          <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${modeBadge(s.mode)}`}>
            {s.mode}
          </span>
          {s.is_favorite && <span className="text-amber-500">★</span>}
        </div>
      </div>
      {s.system_prompt && (
        <p className="mt-2 text-xs text-slate-500 line-clamp-2 font-mono">{s.system_prompt.slice(0, 100)}{s.system_prompt.length > 100 ? '…' : ''}</p>
      )}
      <p className="mt-3 text-xs text-slate-400">{timeAgo(s.updated_at)}</p>
    </div>
  )
}

function RequestRow({ r }: { r: PlaygroundRequestResponse }) {
  const preview = r.user_prompt.length > 60 ? r.user_prompt.slice(0, 60) + '…' : r.user_prompt
  const responsePreview = r.response_text
    ? r.response_text.length > 80 ? r.response_text.slice(0, 80) + '…' : r.response_text
    : '-'
  return (
    <tr className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
      <td className="px-4 py-3">
        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
          {r.model}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-800 dark:text-slate-200 max-w-xs truncate">{preview}</td>
      <td className="px-4 py-3 text-sm text-slate-500 max-w-xs truncate">{responsePreview}</td>
      <td className="px-4 py-3">
        <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusColor(r.status)}`}>
          {r.status}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{money(r.cost_usd)}</td>
      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
        {r.input_tokens != null ? `${r.input_tokens}/${r.output_tokens}` : '-'}
      </td>
      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
        {r.latency_ms != null ? `${r.latency_ms}ms` : '-'}
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">{timeAgo(r.created_at)}</td>
    </tr>
  )
}

export default async function PlaygroundPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to use the playground.</p>

  let sessions: PlaygroundSessionResponse[] = []
  let history: PlaygroundRequestResponse[] = []
  let historyTotal = 0
  try {
    const [sessData, histData] = await Promise.all([
      getPlaygroundSessions(apiKey, { limit: 10 }),
      getPlaygroundHistory(apiKey, { limit: 50 }),
    ])
    sessions = sessData.sessions
    history = histData.requests
    historyTotal = histData.total
  } catch {
    return <p className="p-8 text-slate-500">Failed to load playground data.</p>
  }

  const budgetBuildPosture = await getBudgetDetailBuildPosture(apiKey).catch(() => null)
  const budgetControlBuildPosture = await getBudgetControlBuildPosture(apiKey).catch(() => null)
  const orgGatewayPosture: PlaygroundOrgGatewayPosture | null = await getPlaygroundOrgGatewayPosture(apiKey).catch(() => null)
  const observePosture: PlaygroundObservePosture | null = await getPlaygroundObservePosture(apiKey).catch(() => null)
  const buildPosture: BuildInternalPosture | null = await getBuildInternalPosture(apiKey).catch(() => null)

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          API Playground
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Send requests through the RunLedger gateway, compare models side-by-side, and track costs.
        </p>
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
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400">Workspace &amp; Identity Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workspace</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.workspace_context.workspace_name}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Users</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.workspace_context.workspace_users}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">API Keys</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.api_key_context.total_api_keys}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-blue-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.ai_hub_context.hub_active_models}/{orgGatewayPosture.ai_hub_context.hub_models}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-blue-200 dark:border-blue-800">
            <Link href="/organization" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Organization</Link>
            <Link href="/users" className="text-xs text-blue-600 hover:underline dark:text-blue-400">Users</Link>
            <Link href="/api-keys" className="text-xs text-blue-600 hover:underline dark:text-blue-400">API Keys</Link>
            <Link href="/ai-hub" className="text-xs text-blue-600 hover:underline dark:text-blue-400">AI Hub</Link>
          </div>
        </div>
      )}

      {orgGatewayPosture && (
        <div className="rounded-2xl border border-violet-200 bg-violet-50/50 p-5 shadow-sm dark:border-violet-900 dark:bg-violet-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400">Gateway Configuration Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Providers</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.provider_context.distinct_providers}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Guardrails</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.guardrail_context.active_guardrails}/{orgGatewayPosture.guardrail_context.guardrail_rules}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Cache Configs</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.cache_context.cache_enabled}/{orgGatewayPosture.cache_context.cache_configs}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-violet-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Rate-Limited Routes</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{orgGatewayPosture.rate_limit_context.rate_limited_routes}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-violet-200 dark:border-violet-800">
            <Link href="/provider-profiles" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Provider Profiles</Link>
            <Link href="/gateway" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Gateway</Link>
            <Link href="/guardrails" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
            <Link href="/gateway?tab=cache" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Response Cache</Link>
            <Link href="/gateway?tab=rate-limits" className="text-xs text-violet-600 hover:underline dark:text-violet-400">Rate Limits</Link>
          </div>
        </div>
      )}

      {observePosture && (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50/50 p-5 shadow-sm dark:border-cyan-900 dark:bg-cyan-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-600 dark:text-cyan-400">Observe &amp; Runtime Context</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Runs (30d)</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.runs_context.runs_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Provider Calls (30d)</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.request_flow_context.provider_calls_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Distinct Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{observePosture.model_usage_context.distinct_models_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-cyan-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Total Cost (30d)</p>
              <p className="mt-1 text-lg font-semibold text-cyan-600 dark:text-cyan-400">${observePosture.cost_savings_context.total_cost_30d.toFixed(2)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800">
            <Link href="/analytics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Analytics Overview</Link>
            <Link href="/runs" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Runs</Link>
            <Link href="/analytics?tab=request-flow" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Flow</Link>
            <Link href="/analytics?tab=request-explorer" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Request Explorer</Link>
            <Link href="/analytics?tab=model-usage" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Model Usage</Link>
            <Link href="/analytics?tab=economics" className="text-xs text-cyan-600 hover:underline dark:text-cyan-400">Cost &amp; Savings</Link>
          </div>
        </div>
      )}

      {buildPosture && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5 shadow-sm dark:border-rose-900 dark:bg-rose-950/30">
          <p className="text-xs font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400">Build &amp; Improve Loop</p>
          <div className="mt-3 grid gap-3 grid-cols-2 md:grid-cols-5">
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Workflows</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.workflows_context.definitions}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Eval Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.evaluation_context.experiments}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Hub Models</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.optimization_context.hub_models}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Score Events 30d</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.scorecards_context.score_events_30d}</p>
            </div>
            <div className="rounded-xl bg-white/80 dark:bg-rose-900/30 p-3">
              <p className="text-xs text-slate-500 dark:text-slate-400">Replay Experiments</p>
              <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{buildPosture.replay_context.experiments}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-rose-200 dark:border-rose-800">
            <Link href="/workflows" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Workflows</Link>
            <Link href="/evaluation?tab=scores" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Evaluation Studio</Link>
            <Link href="/optimization-opportunities" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Optimization</Link>
            <Link href="/optimization-simulator" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Simulator</Link>
            <Link href="/model-scorecards" className="text-xs text-rose-600 hover:underline dark:text-rose-400">Model Scorecards</Link>
          </div>
        </div>
      )}

      {/* Quick Send */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">Quick Send</h2>
        <p className="text-sm text-slate-500">
          Use the API to send requests:
        </p>
        <pre className="mt-3 rounded-lg bg-slate-100 p-4 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300 overflow-x-auto">
{`POST /playground/send
{
  "model": "gpt-4o",
  "user_prompt": "Explain quantum computing in one sentence.",
  "parameters": { "temperature": 0.7, "max_tokens": 100 }
}

POST /playground/compare
{
  "models": ["gpt-4o", "claude-sonnet-4-20250514"],
  "user_prompt": "What is the capital of France?"
}`}
        </pre>
      </div>

      {/* Sessions */}
      {sessions.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
            Sessions ({sessions.length})
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sessions.map((s) => (
              <SessionCard key={s.id} s={s} />
            ))}
          </div>
        </section>
      )}

      {/* History */}
      <section>
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
          Request History ({historyTotal})
        </h2>
        {history.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center dark:border-slate-700 dark:bg-slate-900/40">
            <p className="text-sm text-slate-500">No playground requests yet.</p>
            <p className="mt-2 text-xs text-slate-400">Send your first request using the API above.</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Model</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Prompt</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Response</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Status</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Cost</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Tokens</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Latency</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">When</th>
                </tr>
              </thead>
              <tbody>
                {history.map((r) => (
                  <RequestRow key={r.id} r={r} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
