import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { authOptions } from '@/lib/auth'
import { getAgent, getAgentMemories, getAgentMemoryStats, getAgentMemoryAudit, getAgentDetailGovernancePosture } from '@/lib/api'
import type { AgentMemoryResponse, AgentMemoryStats, AgentMemoryAuditResponse } from '@/types/api'
import { num } from '@/lib/utils'

function bytes(n: number) {
  if (n < 1024) return `${n} B`
  if (num(n) < 1024 * 1024) return `${(num(n) / 1024).toFixed(1)} KB`
  return `${(num(n) / (1024 * 1024)).toFixed(1)} MB`
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

const typeBadge: Record<string, string> = {
  short_term: 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
  long_term: 'bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300',
  shared: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
}

const actionColors: Record<string, string> = {
  store: 'text-emerald-600 dark:text-emerald-400',
  update: 'text-blue-600 dark:text-blue-400',
  delete: 'text-rose-600 dark:text-rose-400',
  search: 'text-amber-600 dark:text-amber-400',
  access: 'text-slate-600 dark:text-slate-400',
}

export default async function AgentMemoryPage({ params }: { params: Promise<{ agent_id: string }> }) {
  const { agent_id } = await params
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) {
    return <p className="p-6 text-xs text-slate-500">Sign in to view agent memory.</p>
  }

  let agent, memories, stats: AgentMemoryStats | null = null, audit, governancePosture
  try {
    ;[agent, memories, stats, audit, governancePosture] = await Promise.all([
      getAgent(apiKey, agent_id),
      getAgentMemories(apiKey, agent_id, { limit: 100 }),
      getAgentMemoryStats(apiKey, agent_id),
      getAgentMemoryAudit(apiKey, agent_id, { limit: 50 }),
      getAgentDetailGovernancePosture(apiKey).catch(() => null),
    ])
  } catch {
    return (
      <div className="p-6">
        <p className="text-xs text-slate-500">Failed to load agent memory.</p>
        <Link href="/agents" className="mt-2 inline-block text-xs text-blue-600 hover:underline dark:text-blue-400">Back to Agents</Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* ── Header ───────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75" /></svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Link href="/agents" className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">Agents</Link>
              <span className="text-[10px] text-slate-300 dark:text-slate-600">/</span>
              <Link href={`/agents/${agent_id}`} className="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">{agent.name}</Link>
              <span className="text-[10px] text-slate-300 dark:text-slate-600">/</span>
            </div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Memory Store</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Key-value memory entries, access patterns, and audit trail.</p>
          </div>
        </div>
        <Link
          href={`/agents/${agent_id}`}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
        >
          ← Agent Detail
        </Link>
      </div>

      {/* ── KPI strip ────────────────────────────── */}
      {stats && (
        <div className="grid grid-cols-5 gap-2">
          {[
            { label: 'Total Memories', value: String(stats.total_memories) },
            { label: 'Total Size', value: bytes(stats.total_size_bytes) },
            { label: 'By Type', value: Object.entries(stats.by_type).map(([k, v]) => `${k.replace('_', ' ')}: ${v}`).join(', ') || 'none' },
            { label: 'Contains PII', value: String(stats.pii_count), alert: stats.pii_count > 0 },
            { label: 'Expired', value: String(stats.expired_count) },
          ].map(({ label, value, alert }) => (
            <div key={label} className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-2.5 py-2 text-center">
              <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">{label}</p>
              <p className={`text-sm font-bold ${alert ? 'text-rose-600 dark:text-rose-400' : 'text-slate-900 dark:text-white'}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Governance posture (compact) ─────────── */}
      {governancePosture && (
        <div className="rounded-lg border border-violet-200/60 dark:border-violet-800/40 bg-violet-50/30 dark:bg-violet-950/20 px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400 mb-1">Governance Context</p>
          <div className="flex flex-wrap gap-1.5">
            <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.guardrail_context.rules} guardrails</span>
            <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.safety_context.capture_policies} capture</span>
            <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.safety_context.security_events_30d} sec events</span>
            <span className="rounded-full bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 text-[10px] text-violet-700 dark:text-violet-300">{governancePosture.eval_context.datasets} datasets</span>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-1.5 pt-1.5 border-t border-violet-200/60 dark:border-violet-800/40">
            <Link href="/guardrails" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Guardrails</Link>
            <Link href="/data-capture" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Data Capture</Link>
            <Link href="/security" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Security</Link>
            <Link href="/evaluation" className="text-[10px] text-violet-600 hover:underline dark:text-violet-400">Eval Studio</Link>
          </div>
        </div>
      )}

      {/* ── Most Accessed ─────────────────────────── */}
      {stats && stats.most_accessed.length > 0 && (
        <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Most Accessed</p>
          <div className="flex flex-wrap gap-1.5">
            {stats.most_accessed.map((m) => (
              <span key={m.id} className="inline-flex items-center gap-1 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-0.5 text-[10px]">
                <span className="font-mono text-slate-700 dark:text-slate-300">{m.key}</span>
                <span className="text-[9px] text-slate-400">×{m.access_count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Memory Table ──────────────────────────── */}
      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 overflow-hidden">
        <div className="border-b border-slate-100 dark:border-slate-700/40 px-3 py-2">
          <h2 className="text-xs font-semibold text-slate-900 dark:text-white">Memories ({memories.total})</h2>
        </div>
        {memories.memories.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-xs text-slate-400">No memories stored for this agent yet.</p>
            <p className="mt-1 text-[10px] text-slate-400">
              Use <code className="rounded bg-slate-100 dark:bg-slate-800 px-1 py-0.5 text-[9px]">POST /agents/{agent_id}/memory</code> to store key-value memories.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700/40 bg-slate-50/80 dark:bg-slate-800/60">
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Key</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Value</th>
                  <th className="px-3 py-1.5 text-center text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Type</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Size</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Accesses</th>
                  <th className="px-3 py-1.5 text-center text-[10px] font-semibold text-slate-500 uppercase tracking-wider">PII</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Last Access</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/60 dark:divide-slate-700/30">
                {memories.memories.map((mem) => (
                  <tr key={mem.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors align-top">
                    <td className="px-3 py-1.5 font-mono font-medium text-slate-900 dark:text-slate-100">{mem.key}</td>
                    <td className="px-3 py-1.5 max-w-xs">
                      <span className="text-slate-600 dark:text-slate-300 line-clamp-2">{mem.value.length > 120 ? mem.value.slice(0, 120) + '...' : mem.value}</span>
                    </td>
                    <td className="px-3 py-1.5 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase ${typeBadge[mem.memory_type] || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>{mem.memory_type.replace('_', ' ')}</span>
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-slate-500">{bytes(mem.size_bytes)}</td>
                    <td className="px-3 py-1.5 text-right text-slate-600 dark:text-slate-400">{mem.access_count}</td>
                    <td className="px-3 py-1.5 text-center">
                      {mem.has_pii && <span className="rounded-full bg-rose-100 dark:bg-rose-900/40 px-1.5 py-0.5 text-[9px] font-semibold text-rose-700 dark:text-rose-300">PII</span>}
                    </td>
                    <td className="px-3 py-1.5 text-right text-[10px] text-slate-400 whitespace-nowrap">{timeAgo(mem.last_accessed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Audit Log ─────────────────────────────── */}
      {audit && audit.events.length > 0 && (
        <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 overflow-hidden">
          <div className="border-b border-slate-100 dark:border-slate-700/40 px-3 py-2">
            <h2 className="text-xs font-semibold text-slate-900 dark:text-white">Audit Log (recent {audit.events.length})</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-700/40 bg-slate-50/80 dark:bg-slate-800/60">
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Key</th>
                  <th className="px-3 py-1.5 text-left text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Actor</th>
                  <th className="px-3 py-1.5 text-right text-[10px] font-semibold text-slate-500 uppercase tracking-wider">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100/60 dark:divide-slate-700/30">
                {audit.events.map((event) => (
                  <tr key={event.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className={`px-3 py-1.5 font-medium ${actionColors[event.action] || 'text-slate-600'}`}>{event.action}</td>
                    <td className="px-3 py-1.5 font-mono text-slate-700 dark:text-slate-300">{event.key || '-'}</td>
                    <td className="px-3 py-1.5 text-slate-500">{event.actor || 'api'}</td>
                    <td className="px-3 py-1.5 text-right text-[10px] text-slate-400 whitespace-nowrap">{timeAgo(event.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Quick nav ─────────────────────────────── */}
      <div className="flex flex-wrap gap-1.5">
        {[
          { label: 'Agent Detail', href: `/agents/${agent_id}` },
          { label: 'Agents', href: '/agents' },
          { label: 'Runs', href: '/runs' },
          { label: 'Data Capture', href: '/data-capture' },
          { label: 'Security', href: '/security' },
          { label: 'Guardrails', href: '/guardrails' },
        ].map(({ label, href }) => (
          <Link key={label} href={href} className="rounded-full bg-violet-100 dark:bg-violet-900/30 px-2.5 py-1 text-[10px] font-semibold text-violet-700 dark:text-violet-300 hover:bg-violet-200 dark:hover:bg-violet-800/40 transition-colors">{label}</Link>
        ))}
      </div>
    </div>
  )
}
