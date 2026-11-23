'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, usePathname, useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { BrainCircuit, Database, Pencil, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/ui/page-header'
import { AsyncCard } from '@/components/ui/async-card'
import { DataTable, type DataTableColumn, type DataTableQuery } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { useRole } from '@/components/rbac/useRole'
import { getAgent, getAgentRunsPage, getAgentStats, retireAgent } from '@/lib/api'
import { routes } from '@/lib/routes'
import { num } from '@/lib/utils'
import type { AgentResponse, AgentStats, RunSummary } from '@/types/api'
import { StatusBadge, apiErrorMessage, money, ms, pct, relTime, useApiKey } from '../../workflows/_components/shared'
import { AgentSheet } from '../_components/AgentSheet'

const RUN_STATUSES = ['', 'succeeded', 'failed', 'running', 'cancelled']

function AgentDetail() {
  const { agent_id: id } = useParams<{ agent_id: string }>()
  const apiKey = useApiKey()
  const { canWrite } = useRole()
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const runStatus = params.get('run_status') ?? ''
  const { confirm, dialog } = useConfirm()
  const [agent, setAgent] = useState<AgentResponse | null>(null)
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const [editOpen, setEditOpen] = useState(false)

  useEffect(() => {
    if (!apiKey) return
    let live = true
    setLoading(true)
    setError(null)
    Promise.all([getAgent(apiKey, id), getAgentStats(apiKey, id)])
      .then(([a, s]) => { if (live) { setAgent(a); setStats(s) } })
      .catch((e) => { if (live) setError(apiErrorMessage(e)) })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [apiKey, id, tick])

  const fetchRuns = useCallback(
    (q: DataTableQuery) => (apiKey ? getAgentRunsPage(apiKey, id, { limit: q.limit, offset: q.offset, status: runStatus || undefined }) : Promise.resolve({ items: [], total: 0 })),
    [apiKey, id, runStatus],
  )

  const setRunStatus = (s: string) => {
    const next = new URLSearchParams(params.toString())
    if (s) next.set('run_status', s)
    else next.delete('run_status')
    next.delete('runs_page')
    router.replace(`${pathname}?${next}`, { scroll: false })
  }

  const onRetire = async () => {
    if (!apiKey || !agent) return
    if (!(await confirm({ title: `Retire ${agent.name}?`, description: 'Its envelope check will refuse new runs. History is kept; reactivate it from Edit.', confirmLabel: 'Retire', destructive: true }))) return
    try {
      await retireAgent(apiKey, agent.id)
      toast.success('Agent retired')
      setTick((t) => t + 1)
    } catch (e) {
      toast.error(apiErrorMessage(e))
    }
  }

  const env = stats?.envelope
  const envUsed = env?.envelope_usd != null && num(env.envelope_usd) > 0 ? Math.min(100, (num(env.spent_usd) / num(env.envelope_usd)) * 100) : null

  const columns: DataTableColumn<RunSummary>[] = [
    { key: 'started_at', header: 'Started', value: (r) => r.started_at, render: (r) => <Link href={routes.runsRunId(r.id)} className="text-indigo-600 hover:underline dark:text-indigo-400">{new Date(r.started_at).toLocaleString()}</Link> },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    { key: 'workflow_id', header: 'Workflow', render: (r) => (r.workflow_id ? <Link href={routes.workflowsWorkflowId(r.workflow_id)} className="text-indigo-600 hover:underline">open</Link> : '—') },
    { key: 'total_cost_usd', header: 'Cost', value: (r) => num(r.total_cost_usd), render: (r) => money(r.total_cost_usd) },
    { key: 'duration_ms', header: 'Duration', value: (r) => r.duration_ms, render: (r) => ms(r.duration_ms) },
    { key: 'total_tokens', header: 'Tokens', value: (r) => r.total_tokens, render: (r) => r.total_tokens.toLocaleString() },
  ]

  return (
    <div className="space-y-4">
      {dialog}
      <PageHeader
        icon={BrainCircuit}
        title={<span className="flex items-center gap-2">{agent?.name ?? 'Agent'} {agent && <StatusBadge status={agent.status} />}</span>}
        description={agent?.description ?? (agent ? `${agent.agent_type}${agent.owner ? ` · owner ${agent.owner}` : ''}` : undefined)}
        breadcrumbs={[{ label: 'Agents', href: '/agents' }, { label: agent?.name ?? '…' }]}
        actions={
          <>
            <Link href={routes.agentsAgentIdMemory(id)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium dark:border-slate-700">
              <Database className="h-3.5 w-3.5" aria-hidden="true" /> Memory
            </Link>
            {canWrite && agent && (
              <>
                <button type="button" onClick={() => setEditOpen(true)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium dark:border-slate-700">
                  <Pencil className="h-3.5 w-3.5" aria-hidden="true" /> Edit
                </button>
                {agent.status !== 'retired' && (
                  <button type="button" onClick={() => void onRetire()} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1.5 text-xs font-medium text-rose-600 dark:border-rose-900">
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" /> Retire
                  </button>
                )}
              </>
            )}
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <AsyncCard title="Performance" description="From runs attributed to this agent" loading={loading && !stats} error={error} onRetry={() => setTick((t) => t + 1)}
          empty={!!stats && stats.total_runs === 0} emptyTitle="No runs attributed yet" emptyDescription={`Send agent="${agent?.name ?? ''}" from the SDK, or gen_ai.agent.name in OTLP.`}>
          {stats && (
            <dl className="grid grid-cols-2 gap-2 text-xs">
              <dt className="text-slate-500">Runs</dt><dd className="text-right font-semibold">{stats.total_runs}</dd>
              <dt className="text-slate-500">Success rate</dt><dd className="text-right font-semibold">{pct(stats.success_rate)}</dd>
              <dt className="text-slate-500">Total cost</dt><dd className="text-right font-semibold">{money(stats.total_cost)}</dd>
              <dt className="text-slate-500">Avg duration</dt><dd className="text-right font-semibold">{ms(stats.avg_duration_ms)}</dd>
              <dt className="text-slate-500">Last run</dt><dd className="text-right font-semibold">{relTime(stats.last_run_at)}</dd>
            </dl>
          )}
        </AsyncCard>

        <AsyncCard title="Budget envelope" description="This month's attributed spend; enforced by the SDK preflight" loading={loading && !stats} error={error} onRetry={() => setTick((t) => t + 1)}>
          {env && (
            <div className="space-y-2 text-xs">
              <p className="flex justify-between"><span>{money(env.spent_usd)} spent</span><span>{env.envelope_usd == null ? 'no envelope' : `of ${money(env.envelope_usd)}`}</span></p>
              {envUsed !== null && (
                <div className="h-1.5 rounded bg-slate-100 dark:bg-slate-800" role="progressbar" aria-label={`Envelope used ${envUsed.toFixed(0)}%`} aria-valuenow={Math.round(envUsed)} aria-valuemin={0} aria-valuemax={100}>
                  <div className={`h-1.5 rounded ${envUsed >= 100 ? 'bg-status-error' : envUsed >= 80 ? 'bg-status-warning' : 'bg-status-success'}`} style={{ width: `${envUsed}%` }} />
                </div>
              )}
              <p className={env.allowed ? 'text-status-success' : 'text-status-error'}>{env.allowed ? 'New runs allowed' : `Runs refused: ${env.reason}`}</p>
            </div>
          )}
        </AsyncCard>

        <AsyncCard title="Models and tools" loading={loading && !stats} error={error} onRetry={() => setTick((t) => t + 1)}
          empty={!!stats && stats.models_used.length + stats.tools_used.length === 0} emptyTitle="None recorded yet">
          {stats && (
            <div className="space-y-2 text-xs">
              <div className="flex flex-wrap gap-1">{stats.models_used.map((m) => <span key={m} className="rounded-full bg-indigo-50 px-2 py-0.5 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">{m}</span>)}</div>
              <div className="flex flex-wrap gap-1">{stats.tools_used.map((t) => <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-700 dark:bg-slate-800 dark:text-slate-300">{t}</span>)}</div>
            </div>
          )}
        </AsyncCard>
      </div>

      <section aria-label="Agent runs" className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Runs</h2>
          <label className="flex items-center gap-1.5 text-xs text-slate-500">
            Status
            <select aria-label="Run status filter" value={runStatus} onChange={(e) => setRunStatus(e.target.value)} className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800">
              {RUN_STATUSES.map((s) => <option key={s} value={s}>{s || 'all'}</option>)}
            </select>
          </label>
        </div>
        <DataTable key={runStatus} label="Agent runs" urlPrefix="runs_" columns={columns} rowKey={(r) => r.id} fetchPage={fetchRuns} searchable={false}
          csvFileName={`agent-${id}-runs.csv`} emptyTitle="No runs" onRowClick={(r) => router.push(routes.runsRunId(r.id))} />
      </section>

      <AgentSheet open={editOpen} onOpenChange={setEditOpen} agent={agent} onSaved={(a) => { setAgent(a); setTick((t) => t + 1) }} />
    </div>
  )
}

export default function AgentDetailPage() {
  return (
    <Suspense fallback={null}>
      <AgentDetail />
    </Suspense>
  )
}
