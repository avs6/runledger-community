'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, usePathname, useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { Archive, Pencil, Plug, RotateCcw, Route } from 'lucide-react'
import { PageHeader } from '@/components/ui/page-header'
import { AsyncCard } from '@/components/ui/async-card'
import { DataTable, type DataTableColumn, type DataTableQuery } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { RelatedPanel } from '@/components/context/RelatedPanel'
import { useRole } from '@/components/rbac/useRole'
import { archiveWorkflow, getWorkflowCost, getWorkflowOverview, getWorkflowRunsPage, updateWorkflow } from '@/lib/api'
import { routes } from '@/lib/routes'
import { num } from '@/lib/utils'
import type { RunSummary, WorkflowCostAttribution, WorkflowOverview } from '@/types/api'
import {
  ConnectSnippets,
  HealthCard,
  StatusBadge,
  WorkflowSheet,
  apiErrorMessage,
  money,
  ms,
  useApiKey,
} from '../_components/shared'

const WINDOWS = [7, 30, 90]
const RUN_STATUSES = ['', 'succeeded', 'failed', 'running', 'cancelled']

function useAsync<T>(load: (() => Promise<T>) | null, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    if (!load) return
    let live = true
    setLoading(true)
    setError(null)
    load()
      .then((d) => { if (live) setData(d) })
      .catch((e) => { if (live) setError(apiErrorMessage(e)) })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  return { data, error, loading, retry: () => setTick((t) => t + 1) }
}

function WorkflowDetail() {
  const { workflow_id: id } = useParams<{ workflow_id: string }>()
  const apiKey = useApiKey()
  const { canWrite } = useRole()
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const days = Number(params.get('days') ?? 30) || 30
  const runStatus = params.get('run_status') ?? ''
  const { confirm, dialog } = useConfirm()
  const [editOpen, setEditOpen] = useState(false)
  const [showConnect, setShowConnect] = useState(false)

  const overview = useAsync<WorkflowOverview>(apiKey ? () => getWorkflowOverview(apiKey, id, days) : null, [apiKey, id, days])
  const cost = useAsync<WorkflowCostAttribution>(apiKey ? () => getWorkflowCost(apiKey, id, days) : null, [apiKey, id, days])
  const wf = overview.data?.workflow

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString())
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('runs_page')
    router.replace(`${pathname}?${next}`, { scroll: false })
  }

  const fetchRuns = useCallback(
    (q: DataTableQuery) => (apiKey ? getWorkflowRunsPage(apiKey, id, { limit: q.limit, offset: q.offset, status: runStatus || undefined }) : Promise.resolve({ items: [], total: 0 })),
    [apiKey, id, runStatus],
  )

  const onArchive = async () => {
    if (!apiKey || !wf) return
    if (!(await confirm({ title: `Archive ${wf.name}?`, description: 'New traffic stops matching it; runs and history are kept. You can restore it.', confirmLabel: 'Archive', destructive: true }))) return
    try {
      await archiveWorkflow(apiKey, wf.id)
      toast.success('Workflow archived')
      overview.retry()
    } catch (e) {
      toast.error(apiErrorMessage(e))
    }
  }

  const onRestore = async () => {
    if (!apiKey || !wf) return
    try {
      await updateWorkflow(apiKey, wf.id, { status: 'active' })
      toast.success('Workflow restored')
      overview.retry()
    } catch (e) {
      toast.error(apiErrorMessage(e))
    }
  }

  const runColumns: DataTableColumn<RunSummary>[] = [
    { key: 'started_at', header: 'Started', value: (r) => r.started_at, render: (r) => <Link href={routes.runsRunId(r.id)} className="text-indigo-600 hover:underline dark:text-indigo-400">{new Date(r.started_at).toLocaleString()}</Link> },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
    { key: 'total_cost_usd', header: 'Cost', value: (r) => num(r.total_cost_usd), render: (r) => money(r.total_cost_usd) },
    { key: 'total_tokens', header: 'Tokens', value: (r) => r.total_tokens, render: (r) => r.total_tokens.toLocaleString() },
    { key: 'duration_ms', header: 'Duration', value: (r) => r.duration_ms, render: (r) => ms(r.duration_ms) },
    { key: 'source_type', header: 'Source', render: (r) => r.source_type ?? 'sdk' },
    { key: 'end_user_id', header: 'End user', defaultHidden: true },
    { key: 'agent_id', header: 'Agent', defaultHidden: true, render: (r) => r.agent_id ? <Link href={routes.agentsAgentId(r.agent_id)} className="text-indigo-600 hover:underline">agent</Link> : '—' },
  ]

  const ov = overview.data
  return (
    <div className="space-y-4">
      {dialog}
      <PageHeader
        icon={Route}
        title={<span className="flex items-center gap-2">{wf?.name ?? 'Workflow'} {wf && <StatusBadge status={wf.status} />}</span>}
        description={wf ? (
          <>
            {wf.feature_tag ? <>Tag <code>{wf.feature_tag}</code></> : 'No feature tag linked'}
            {wf.gateway_alias && <> · alias <code>{wf.gateway_alias}</code></>}
            {wf.owner && <> · owner {wf.owner}</>}
            {wf.description && <> · {wf.description}</>}
          </>
        ) : undefined}
        breadcrumbs={[{ label: 'Workflows', href: '/workflows' }, { label: wf?.name ?? '…' }]}
        actions={
          <>
            <label className="flex items-center gap-1.5 text-xs text-slate-500">
              Window
              <select aria-label="Time window" value={days} onChange={(e) => setParam('days', e.target.value)} className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800">
                {WINDOWS.map((d) => <option key={d} value={d}>{d} days</option>)}
              </select>
            </label>
            <button type="button" onClick={() => setShowConnect((s) => !s)} aria-expanded={showConnect} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium dark:border-slate-700">
              <Plug className="h-3.5 w-3.5" aria-hidden="true" /> Connect
            </button>
            {wf && <RelatedPanel entity="workflow" id={wf.id} />}
            {canWrite && wf && (
              <>
                <button type="button" aria-label="Edit workflow" onClick={() => setEditOpen(true)} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium dark:border-slate-700">
                  <Pencil className="h-3.5 w-3.5" aria-hidden="true" /> Edit
                </button>
                {wf.status === 'archived' ? (
                  <button type="button" onClick={() => void onRestore()} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium dark:border-slate-700">
                    <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Restore
                  </button>
                ) : (
                  <button type="button" onClick={() => void onArchive()} className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1.5 text-xs font-medium text-rose-600 dark:border-rose-900">
                    <Archive className="h-3.5 w-3.5" aria-hidden="true" /> Archive
                  </button>
                )}
              </>
            )}
          </>
        }
      />

      {showConnect && wf && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="mb-2 text-sm font-semibold">Send this workflow&apos;s traffic</h2>
          <ConnectSnippets workflow={wf} />
        </section>
      )}

      <AsyncCard title="Workflow health" description={`Last ${days} days: unit economics joined to quality`} loading={overview.loading && !ov} error={overview.error} onRetry={overview.retry}
        empty={!!ov && ov.health.runs === 0} emptyTitle="No runs attributed yet" emptyDescription="Send traffic with this workflow's tag (Connect, above) and runs appear here within seconds.">
        {ov && <HealthCard health={ov.health} />}
      </AsyncCard>

      <section aria-label="Runs" className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Runs</h2>
          <label className="flex items-center gap-1.5 text-xs text-slate-500">
            Status
            <select aria-label="Run status filter" value={runStatus} onChange={(e) => setParam('run_status', e.target.value)} className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800">
              {RUN_STATUSES.map((s) => <option key={s} value={s}>{s || 'all'}</option>)}
            </select>
          </label>
        </div>
        <DataTable key={runStatus} label="Workflow runs" urlPrefix="runs_" columns={runColumns} rowKey={(r) => r.id} fetchPage={fetchRuns}
          searchable={false} csvFileName={`workflow-${id}-runs.csv`} emptyTitle="No runs yet" emptyDescription="Runs attributed to this workflow appear here."
          onRowClick={(r) => router.push(routes.runsRunId(r.id))} />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <AsyncCard title="Cost by step" description="Rolled up from provider calls under each span" loading={cost.loading && !cost.data} error={cost.error} onRetry={cost.retry} empty={!!cost.data && cost.data.cost_by_step.length === 0} emptyTitle="No priced calls yet">
          {cost.data && (
            <table className="w-full text-xs">
              <caption className="sr-only">Cost by step</caption>
              <thead><tr className="text-left text-slate-500"><th className="py-1">Step</th><th>Calls</th><th>Avg</th><th className="text-right">Total</th></tr></thead>
              <tbody>
                {cost.data.cost_by_step.map((s) => (
                  <tr key={s.step_name} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-1 font-mono">{s.step_name}</td><td>{s.invocation_count}</td><td>{money(s.avg_cost)}</td><td className="text-right">{money(s.total_cost)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot><tr className="border-t border-slate-200 font-semibold dark:border-slate-700"><td className="py-1">Steps total</td><td colSpan={2} className="text-slate-500">runs total {money(cost.data.total_cost)}</td><td className="text-right">{money(cost.data.steps_cost)}</td></tr></tfoot>
            </table>
          )}
        </AsyncCard>

        <AsyncCard title="Cost by model" loading={cost.loading && !cost.data} error={cost.error} onRetry={cost.retry} empty={!!cost.data && cost.data.cost_by_model.length === 0} emptyTitle="No model calls yet">
          {cost.data && (
            <table className="w-full text-xs">
              <caption className="sr-only">Cost by model</caption>
              <thead><tr className="text-left text-slate-500"><th className="py-1">Model</th><th>Calls</th><th>Tokens</th><th className="text-right">Cost</th></tr></thead>
              <tbody>
                {cost.data.cost_by_model.map((m) => (
                  <tr key={`${m.provider}/${m.model}`} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-1">{m.provider}/{m.model}</td><td>{m.calls}</td><td>{m.total_tokens.toLocaleString()}</td><td className="text-right">{money(m.total_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </AsyncCard>

        <AsyncCard title="Budgets" description="Feature-tag budgets on this workflow, enforced at ingest and the gateway" loading={overview.loading && !ov} error={overview.error} onRetry={overview.retry}
          empty={!!ov && ov.budgets.length === 0} emptyTitle="No budget on this workflow" emptyDescription={wf?.feature_tag ? `Create a feature_tag budget on "${wf.feature_tag}".` : 'Link a feature tag first, then add a budget on it.'}
          actions={wf?.feature_tag ? <Link href={`/budgets?scope_type=feature_tag&scope_id=${encodeURIComponent(wf.feature_tag)}`} className="text-xs text-indigo-600 hover:underline">Add budget</Link> : undefined}>
          {ov && (
            <ul className="space-y-2">
              {ov.budgets.map((b) => {
                const used = num(b.limit_usd) ? Math.min(100, (num(b.spent_usd) / num(b.limit_usd)) * 100) : 0
                return (
                  <li key={b.id} className="text-xs">
                    <div className="flex justify-between"><Link href={routes.budgetsId(b.id)} className="font-medium text-indigo-600 hover:underline">{b.period_type} · {b.action}</Link><span>{money(b.spent_usd)} / {money(b.limit_usd)}</span></div>
                    <div className="mt-1 h-1.5 rounded bg-slate-100 dark:bg-slate-800" role="progressbar" aria-label={`Budget used ${used.toFixed(0)}%`} aria-valuenow={Math.round(used)} aria-valuemin={0} aria-valuemax={100}>
                      <div className={`h-1.5 rounded ${used >= 100 ? 'bg-status-error' : used >= 80 ? 'bg-status-warning' : 'bg-status-success'}`} style={{ width: `${used}%` }} />
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </AsyncCard>

        <AsyncCard title="Evaluations" description="Average score per evaluator on this workflow's runs" loading={overview.loading && !ov} error={overview.error} onRetry={overview.retry}
          empty={!!ov && ov.evals.length === 0} emptyTitle="No scores yet" emptyDescription="Attach an evaluator or send scores for these runs." actions={<Link href={'/evaluation'} className="text-xs text-indigo-600 hover:underline">Evaluation</Link>}>
          {ov && (
            <ul className="space-y-1 text-xs">
              {ov.evals.map((e) => <li key={e.name} className="flex justify-between"><span>{e.name}</span><span>{e.avg_score.toFixed(2)} <span className="text-slate-400">({e.count})</span></span></li>)}
            </ul>
          )}
        </AsyncCard>

        <AsyncCard title="Policies" description="Controls that apply to this workflow's traffic" loading={overview.loading && !ov} error={overview.error} onRetry={overview.retry}
          empty={!!ov && ov.policies.length === 0} emptyTitle="No controls apply" emptyDescription="Link a gateway alias, or add guardrails and tool policies.">
          {ov && (
            <ul className="space-y-1.5 text-xs">
              {ov.policies.map((p, i) => (
                <li key={`${p.kind}-${i}`} className="flex justify-between gap-3">
                  {p.href ? <Link href={p.href} className="font-medium text-indigo-600 hover:underline">{p.name}</Link> : <span className="font-medium">{p.name}</span>}
                  <span className="text-right text-slate-500">{p.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </AsyncCard>

        <AsyncCard title="Agents" description="Registered agents that ran in this workflow" loading={overview.loading && !ov} error={overview.error} onRetry={overview.retry}
          empty={!!ov && ov.agents.length === 0} emptyTitle="No agents attributed" emptyDescription="Pass agent=… in the SDK (or runledger.agent in OTLP) to attribute runs to a registered agent.">
          {ov && (
            <ul className="space-y-1 text-xs">
              {ov.agents.map((a) => <li key={a.id} className="flex justify-between"><Link href={routes.agentsAgentId(a.id)} className="text-indigo-600 hover:underline">{a.name}</Link><span>{a.runs} runs · {money(a.total_cost_usd)}</span></li>)}
            </ul>
          )}
        </AsyncCard>
      </div>

      <WorkflowSheet open={editOpen} onOpenChange={setEditOpen} workflow={wf} onSaved={() => { overview.retry(); cost.retry() }} />
    </div>
  )
}

export default function WorkflowDetailPage() {
  return (
    <Suspense fallback={null}>
      <WorkflowDetail />
    </Suspense>
  )
}
