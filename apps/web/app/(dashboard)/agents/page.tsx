import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAgents } from '@/lib/api'
import type { AgentResponse } from '@/types/api'

function money(v: number | null) {
  if (!v) return '$0.00'
  if (v >= 1) return `$${v.toFixed(2)}`
  if (v >= 0.001) return `$${v.toFixed(4)}`
  return `$${v.toFixed(6)}`
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    active: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
    paused: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    retired: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  }
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${colors[status] || colors.active}`}>
      {status}
    </span>
  )
}

function typeBadge(type: string) {
  const colors: Record<string, string> = {
    autonomous: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    semi_autonomous: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
    workflow: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300',
    chat: 'bg-pink-100 text-pink-700 dark:bg-pink-900/40 dark:text-pink-300',
  }
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${colors[type] || colors.autonomous}`}>
      {type.replace('_', '-')}
    </span>
  )
}

function AgentCard({ agent }: { agent: AgentResponse }) {
  return (
    <Link
      href={`/agents/${agent.id}`}
      className="group rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm ring-1 ring-white/70 transition hover:border-blue-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-900/80 dark:ring-transparent dark:hover:border-blue-500"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-slate-950 dark:text-slate-50">
            {agent.name}
          </h3>
          {agent.description && (
            <p className="mt-1 line-clamp-2 text-xs text-slate-500">{agent.description}</p>
          )}
        </div>
        {statusBadge(agent.status)}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {typeBadge(agent.agent_type)}
        {agent.default_model && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {agent.default_model}
          </span>
        )}
        {agent.owner && (
          <span className="text-[11px] text-slate-500">
            by {agent.owner}
          </span>
        )}
      </div>
      <div className="mt-4 flex items-center gap-4 border-t border-slate-100 pt-3 text-[11px] text-slate-500 dark:border-slate-800">
        {agent.budget_envelope != null && (
          <span>Budget: {money(agent.budget_envelope)}</span>
        )}
        <span>{agent.default_tools.length} tools</span>
        <span className="ml-auto text-[10px] text-slate-400">
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
  } catch {
    // API may not be reachable yet
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-[-0.04em] text-slate-950 dark:text-slate-50">
            Agent Registry
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {total} agent{total !== 1 ? 's' : ''} registered
          </p>
        </div>
      </div>

      {agents.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/50 p-12 text-center dark:border-slate-700 dark:bg-slate-900/50">
          <p className="text-sm text-slate-500">
            No agents registered yet. Use the API to register your first agent.
          </p>
          <pre className="mx-auto mt-4 max-w-lg rounded-xl bg-slate-100 p-4 text-left text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-300">
{`POST /agents
{
  "name": "my-agent",
  "agent_type": "autonomous",
  "default_model": "gpt-4o"
}`}
          </pre>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  )
}
