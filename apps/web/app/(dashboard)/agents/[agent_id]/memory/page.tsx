import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAgent, getAgentMemories, getAgentMemoryStats, getAgentMemoryAudit } from '@/lib/api'
import type { AgentMemoryResponse, AgentMemoryStats, AgentMemoryAuditResponse } from '@/types/api'

function bytes(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function timeAgo(iso: string | null) {
  if (!iso) return '-'
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function typeBadge(t: string) {
  const map: Record<string, string> = {
    short_term: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
    long_term: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
    shared: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  }
  return map[t] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
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

function MemoryRow({ mem }: { mem: AgentMemoryResponse }) {
  const preview = mem.value.length > 120 ? mem.value.slice(0, 120) + '…' : mem.value
  return (
    <tr className="border-b border-slate-100 transition hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
      <td className="px-4 py-3 font-mono text-sm text-slate-800 dark:text-slate-200">{mem.key}</td>
      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400 max-w-xs truncate">{preview}</td>
      <td className="px-4 py-3">
        <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${typeBadge(mem.memory_type)}`}>
          {mem.memory_type.replace('_', ' ')}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{bytes(mem.size_bytes)}</td>
      <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-400">{mem.access_count}</td>
      <td className="px-4 py-3">
        {mem.has_pii && (
          <span className="inline-block rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-700 dark:bg-red-900/40 dark:text-red-300">
            PII
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">{timeAgo(mem.last_accessed_at)}</td>
    </tr>
  )
}

function AuditRow({ event }: { event: AgentMemoryAuditResponse }) {
  const actionColor: Record<string, string> = {
    store: 'text-emerald-600 dark:text-emerald-400',
    update: 'text-blue-600 dark:text-blue-400',
    delete: 'text-red-600 dark:text-red-400',
    search: 'text-amber-600 dark:text-amber-400',
    access: 'text-slate-600 dark:text-slate-400',
  }
  return (
    <tr className="border-b border-slate-100 dark:border-slate-800">
      <td className={`px-4 py-2 text-sm font-medium ${actionColor[event.action] || 'text-slate-600'}`}>
        {event.action}
      </td>
      <td className="px-4 py-2 font-mono text-sm text-slate-700 dark:text-slate-300">{event.key || '-'}</td>
      <td className="px-4 py-2 text-xs text-slate-500">{event.actor || 'api'}</td>
      <td className="px-4 py-2 text-xs text-slate-500">{timeAgo(event.created_at)}</td>
    </tr>
  )
}

export default async function AgentMemoryPage({ params }: { params: Promise<{ agent_id: string }> }) {
  const { agent_id } = await params
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) {
    return <p className="p-8 text-slate-500">Sign in to view agent memory.</p>
  }

  let agent, memories, stats: AgentMemoryStats | null = null, audit
  try {
    ;[agent, memories, stats, audit] = await Promise.all([
      getAgent(apiKey, agent_id),
      getAgentMemories(apiKey, agent_id, { limit: 100 }),
      getAgentMemoryStats(apiKey, agent_id),
      getAgentMemoryAudit(apiKey, agent_id, { limit: 50 }),
    ])
  } catch {
    return (
      <div className="p-8">
        <p className="text-slate-500">Failed to load agent memory. The agent may not exist.</p>
        <Link href="/agents" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
          Back to Agents
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 p-6 md:p-10">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href={`/agents/${agent_id}`} className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          ← {agent.name}
        </Link>
        <span className="text-slate-400">/</span>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Memory</h1>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <StatCard label="Total Memories" value={String(stats.total_memories)} />
          <StatCard label="Total Size" value={bytes(stats.total_size_bytes)} />
          <StatCard
            label="By Type"
            value={Object.entries(stats.by_type).map(([k, v]) => `${k.replace('_', ' ')}: ${v}`).join(', ') || 'none'}
          />
          <StatCard label="Contains PII" value={String(stats.pii_count)} sub={stats.pii_count > 0 ? 'flagged entries' : ''} />
          <StatCard label="Expired" value={String(stats.expired_count)} />
        </div>
      )}

      {/* Most Accessed */}
      {stats && stats.most_accessed.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">Most Accessed</h2>
          <div className="flex flex-wrap gap-2">
            {stats.most_accessed.map((m) => (
              <span
                key={m.id}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
              >
                <span className="font-mono text-slate-700 dark:text-slate-300">{m.key}</span>
                <span className="text-[10px] text-slate-400">×{m.access_count}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Memory Table */}
      <section>
        <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
          Memories ({memories.total})
        </h2>
        {memories.memories.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 p-10 text-center dark:border-slate-700 dark:bg-slate-900/40">
            <p className="text-sm text-slate-500">No memories stored for this agent yet.</p>
            <p className="mt-2 text-xs text-slate-400">
              Use <code className="rounded bg-slate-100 px-1 py-0.5 dark:bg-slate-800">POST /agents/{agent_id}/memory</code> to store key-value memories.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Key</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Value</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Type</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Size</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Accesses</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">PII</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Last Access</th>
                </tr>
              </thead>
              <tbody>
                {memories.memories.map((m) => (
                  <MemoryRow key={m.id} mem={m} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Audit Log */}
      {audit && audit.events.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
            Audit Log (recent {audit.events.length})
          </h2>
          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/80">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-800/60">
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Action</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Key</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Actor</th>
                  <th className="px-4 py-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">When</th>
                </tr>
              </thead>
              <tbody>
                {audit.events.map((e) => (
                  <AuditRow key={e.id} event={e} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
