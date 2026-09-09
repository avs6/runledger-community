import { getServerSession } from 'next-auth'
import Link from 'next/link'
import {
  BrainCircuit, Bot, Cpu, DollarSign, FlaskConical, GitBranch,
  Layers, MemoryStick, Network, Plus, Rocket, Shield, Sparkles,
  Terminal, Wrench, Zap,
} from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { getAgents, getBudgetDetailBuildPosture, getBudgetControlBuildPosture, getAgentsListPosture } from '@/lib/api'
import type { AgentResponse } from '@/types/api'
import { num } from '@/lib/utils'

function money(v: number | string | null | undefined) {
  const n = num(v)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

const typeConfig: Record<string, { label: string; color: string; glow: string; icon: typeof Bot }> = {
  autonomous: { label: 'Autonomous', color: 'from-blue-500 to-cyan-400', glow: 'shadow-blue-500/20', icon: Rocket },
  semi_autonomous: { label: 'Semi-Auto', color: 'from-violet-500 to-purple-400', glow: 'shadow-violet-500/20', icon: GitBranch },
  workflow: { label: 'Workflow', color: 'from-cyan-500 to-teal-400', glow: 'shadow-cyan-500/20', icon: Layers },
  chat: { label: 'Chat', color: 'from-pink-500 to-rose-400', glow: 'shadow-pink-500/20', icon: Sparkles },
}

const statusDot: Record<string, string> = {
  active: 'bg-emerald-400 shadow-emerald-400/50',
  paused: 'bg-amber-400 shadow-amber-400/50',
  retired: 'bg-slate-400 shadow-slate-400/30',
}

function AgentCard({ agent }: { agent: AgentResponse }) {
  const tc = typeConfig[agent.agent_type] ?? typeConfig.autonomous
  const TypeIcon = tc.icon

  return (
    <Link
      href={`/agents/${agent.id}`}
      className={`group relative flex flex-col rounded-xl border border-slate-200/80 bg-white/90 p-4 shadow-sm transition-all hover:shadow-lg hover:${tc.glow} dark:border-slate-700/60 dark:bg-slate-900/80 dark:hover:border-slate-600`}
    >
      {/* Gradient accent bar */}
      <div className={`absolute inset-x-0 top-0 h-0.5 rounded-t-xl bg-gradient-to-r ${tc.color}`} />

      <div className="flex items-start gap-3">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${tc.color} shadow-lg ${tc.glow}`}>
          <TypeIcon className="h-4.5 w-4.5 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-bold text-slate-950 dark:text-white">{agent.name}</h3>
            <span className={`h-2 w-2 shrink-0 rounded-full shadow-sm ${statusDot[agent.status] ?? statusDot.active}`} title={agent.status} />
          </div>
          {agent.description && (
            <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">{agent.description}</p>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className={`inline-flex items-center gap-1 rounded-md bg-gradient-to-r ${tc.color} px-2 py-0.5 text-[10px] font-bold text-white shadow-sm`}>
          <TypeIcon className="h-2.5 w-2.5" />
          {tc.label}
        </span>
        {agent.default_model && (
          <span className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
            {agent.default_model}
          </span>
        )}
        {agent.owner && (
          <span className="text-[10px] text-slate-400">by {agent.owner}</span>
        )}
      </div>

      <div className="mt-3 flex items-center gap-3 border-t border-slate-100 pt-2.5 text-[10px] text-slate-500 dark:border-slate-800">
        {agent.budget_envelope != null && (
          <span className="flex items-center gap-0.5">
            <DollarSign className="h-2.5 w-2.5 text-emerald-500" />
            {money(agent.budget_envelope)}
          </span>
        )}
        <span className="flex items-center gap-0.5">
          <Wrench className="h-2.5 w-2.5 text-blue-400" />
          {agent.default_tools.length} tools
        </span>
        <span className="ml-auto text-slate-400">
          {new Date(agent.created_at).toLocaleDateString()}
        </span>
      </div>
    </Link>
  )
}

export default async function AgentsPage() {
  const session = await getServerSession(authOptions)
  if (!session) return null

  let agents: AgentResponse[] = []
  let total = 0
  try {
    const data = await getAgents(session.apiKey, { limit: 100 })
    agents = data.agents
    total = data.total
  } catch { /* API may not be reachable */ }

  const budgetBuildPosture = await getBudgetDetailBuildPosture(session.apiKey).catch(() => null)
  const budgetControlPosture = await getBudgetControlBuildPosture(session.apiKey).catch(() => null)
  const agentsPosture = await getAgentsListPosture(session.apiKey).catch(() => null)

  const activeCount = agents.filter(a => a.status === 'active').length
  const pausedCount = agents.filter(a => a.status === 'paused').length
  const typeCounts = agents.reduce((acc, a) => { acc[a.agent_type] = (acc[a.agent_type] || 0) + 1; return acc }, {} as Record<string, number>)

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg shadow-blue-500/25">
            <BrainCircuit className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-950 dark:text-white">Agent Registry</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Register, monitor, and govern your AI agents.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { href: '/workflows', label: 'Workflows', icon: GitBranch },
            { href: '/runs', label: 'Runs', icon: Zap },
            { href: '/evaluation', label: 'Eval Studio', icon: FlaskConical },
            { href: '/ai-hub', label: 'AI Hub', icon: Cpu },
          ].map(nav => (
            <Link key={nav.label} href={nav.href} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <nav.icon className="h-3 w-3" /> {nav.label}
            </Link>
          ))}
        </div>
      </div>

      {/* KPI hero strip */}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8">
        {[
          { label: 'Total', value: total, icon: Bot, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Active', value: activeCount, icon: Zap, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: 'Paused', value: pausedCount, icon: Shield, color: 'text-amber-600 dark:text-amber-400' },
          { label: 'Autonomous', value: typeCounts.autonomous ?? 0, icon: Rocket, color: 'text-blue-600 dark:text-blue-400' },
          { label: 'Semi-Auto', value: typeCounts.semi_autonomous ?? 0, icon: GitBranch, color: 'text-violet-600 dark:text-violet-400' },
          { label: 'Workflow', value: typeCounts.workflow ?? 0, icon: Layers, color: 'text-cyan-600 dark:text-cyan-400' },
          { label: 'Runs 30d', value: agentsPosture?.observe_context.runs_30d ?? 0, icon: Terminal, color: 'text-blue-600 dark:text-blue-400' },
          { label: '30d Spend', value: budgetBuildPosture ? `$${num(budgetBuildPosture.spend_context.total_spend_30d).toFixed(2)}` : '$0', icon: DollarSign, color: 'text-emerald-600 dark:text-emerald-400' },
        ].map(kpi => (
          <div key={kpi.label} className="rounded-xl border border-slate-200 bg-white/90 p-2.5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
            <div className="flex items-center gap-1">
              <kpi.icon className={`h-3 w-3 ${kpi.color}`} />
              <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-400">{kpi.label}</span>
            </div>
            <p className="mt-1 text-base font-bold text-slate-950 dark:text-white">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Posture chips — condensed */}
      <div className="grid gap-2 lg:grid-cols-3">
        {budgetBuildPosture && (
          <div className="rounded-xl border border-emerald-200/60 bg-emerald-50/30 p-3 dark:border-emerald-800/40 dark:bg-emerald-950/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <DollarSign className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">FinOps</span>
              </div>
              <Link href="/budgets" className="text-[10px] font-semibold text-emerald-600 hover:underline dark:text-emerald-400">Manage</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {[
                { l: 'Budgets', v: budgetBuildPosture.budget_context.active_budgets },
                { l: 'Agents', v: budgetBuildPosture.build_context.agents },
                { l: 'Breached', v: budgetBuildPosture.budget_context.breach_count },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] dark:border-emerald-800 dark:bg-emerald-950/40">
                  <span className="font-medium text-emerald-500 dark:text-emerald-400">{c.l}</span>
                  <span className="font-bold text-emerald-700 dark:text-emerald-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {agentsPosture && (
          <div className="rounded-xl border border-blue-200/60 bg-blue-50/30 p-3 dark:border-blue-800/40 dark:bg-blue-950/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Network className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                <span className="text-xs font-semibold text-blue-700 dark:text-blue-300">Org & Providers</span>
              </div>
              <Link href="/providers" className="text-[10px] font-semibold text-blue-600 hover:underline dark:text-blue-400">Providers</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {[
                { l: 'Hub Models', v: agentsPosture.org_context.hub_models },
                { l: 'Active', v: agentsPosture.org_context.active_models },
                { l: 'Providers', v: agentsPosture.provider_context.distinct_providers },
                { l: 'Chargeback', v: agentsPosture.finops_context.chargeback_rules },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] dark:border-blue-800 dark:bg-blue-950/40">
                  <span className="font-medium text-blue-500 dark:text-blue-400">{c.l}</span>
                  <span className="font-bold text-blue-700 dark:text-blue-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {agentsPosture && (
          <div className="rounded-xl border border-rose-200/60 bg-rose-50/30 p-3 dark:border-rose-800/40 dark:bg-rose-950/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <FlaskConical className="h-3.5 w-3.5 text-rose-600 dark:text-rose-400" />
                <span className="text-xs font-semibold text-rose-700 dark:text-rose-300">Build & Improve</span>
              </div>
              <Link href="/evaluation" className="text-[10px] font-semibold text-rose-600 hover:underline dark:text-rose-400">Eval Studio</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {[
                { l: 'Datasets', v: agentsPosture.eval_context.datasets },
                { l: 'Experiments', v: agentsPosture.eval_context.experiments },
              ].map(c => (
                <span key={c.l} className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] dark:border-rose-800 dark:bg-rose-950/40">
                  <span className="font-medium text-rose-500 dark:text-rose-400">{c.l}</span>
                  <span className="font-bold text-rose-700 dark:text-rose-300">{c.v}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Agent grid */}
      {agents.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map(agent => <AgentCard key={agent.id} agent={agent} />)}
        </div>
      )}

      {/* Registration guide — always visible */}
      <div className="rounded-xl border border-slate-200 bg-white/90 p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-2 mb-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500">
            <Plus className="h-3.5 w-3.5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900 dark:text-white">Register an Agent</p>
            <p className="text-[10px] text-slate-500">POST to the API to register agents into your workspace</p>
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          {/* Minimal agent */}
          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">Minimal — Quick Start</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-[11px] font-mono leading-relaxed text-green-400">{`curl -X POST /api/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "name": "my-agent",
    "agent_type": "autonomous",
    "default_model": "gpt-4o"
  }'`}</pre>
          </div>

          {/* Full agent */}
          <div>
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-400">Full — With Budget & Tools</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-[11px] font-mono leading-relaxed text-green-400">{`curl -X POST /api/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "name": "research-agent",
    "description": "Autonomous research assistant",
    "agent_type": "autonomous",
    "owner": "ml-team",
    "default_model": "gpt-4o",
    "default_tools": ["web_search", "code_exec"],
    "budget_envelope": 50.00,
    "policy_profile": "standard"
  }'`}</pre>
          </div>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { type: 'autonomous', desc: 'Fully self-directed. Makes decisions, picks tools, iterates independently.', icon: Rocket, color: 'from-blue-500 to-cyan-400' },
            { type: 'semi_autonomous', desc: 'Proposes actions, waits for approval. Human-in-the-loop.', icon: GitBranch, color: 'from-violet-500 to-purple-400' },
            { type: 'workflow', desc: 'Follows a defined step sequence. Predictable, auditable.', icon: Layers, color: 'from-cyan-500 to-teal-400' },
            { type: 'chat', desc: 'Conversational interface. Responds to user messages directly.', icon: Sparkles, color: 'from-pink-500 to-rose-400' },
          ].map(t => (
            <div key={t.type} className="rounded-lg border border-slate-100 bg-slate-50/60 p-2.5 dark:border-slate-700 dark:bg-slate-800/60">
              <div className="flex items-center gap-1.5">
                <div className={`flex h-5 w-5 items-center justify-center rounded bg-gradient-to-br ${t.color}`}>
                  <t.icon className="h-3 w-3 text-white" />
                </div>
                <span className="text-[11px] font-bold text-slate-800 dark:text-white">{t.type}</span>
              </div>
              <p className="mt-1 text-[10px] leading-relaxed text-slate-500 dark:text-slate-400">{t.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-100 pt-3 text-[10px] dark:border-slate-800">
          <span className="font-semibold text-slate-500">After registering:</span>
          {[
            { l: 'Add memory', href: '#', desc: 'POST /agents/{id}/memory' },
            { l: 'Run workflows', href: '/workflows', desc: 'Link to workflow steps' },
            { l: 'Set budgets', href: '/budgets', desc: 'Control spend per agent' },
            { l: 'View runs', href: '/runs', desc: 'Track agent executions' },
          ].map(tip => (
            <Link key={tip.l} href={tip.href} className="rounded-md border border-slate-200 bg-white px-2 py-0.5 font-medium text-blue-600 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800 dark:text-blue-400" title={tip.desc}>
              {tip.l}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
