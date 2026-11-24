'use client'

import { Suspense, useCallback, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { Archive, Pencil, Plus, RotateCcw, Route, Sparkles } from 'lucide-react'
import { PageHeader } from '@/components/ui/page-header'
import { DataTable, type DataTableColumn, type DataTableQuery } from '@/components/ui/data-table'
import { EmptyState } from '@/components/ui/empty-state'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { useRole } from '@/components/rbac/useRole'
import { archiveWorkflow, getWorkflowsPage, updateWorkflow } from '@/lib/api'
import { routes } from '@/lib/routes'
import type { WorkflowDefinitionResponse } from '@/types/api'
import { StatusBadge, WorkflowSheet, apiErrorMessage, money, ms, pct, relTime, useApiKey } from './_components/shared'

const WINDOWS = [7, 30, 90]

function WorkflowsInner() {
  const apiKey = useApiKey()
  const { canWrite } = useRole()
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const status = params.get('status') ?? 'active'
  const days = Number(params.get('days') ?? 30) || 30
  const { confirm, dialog } = useConfirm()
  const [editing, setEditing] = useState<WorkflowDefinitionResponse | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [version, setVersion] = useState(0)
  const [empty, setEmpty] = useState(false)

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString())
    next.set(key, value)
    next.delete('wf_page')
    router.replace(`${pathname}?${next}`, { scroll: false })
  }

  const fetchPage = useCallback(
    async (q: DataTableQuery) => {
      if (!apiKey) return { items: [], total: 0 }
      const page = await getWorkflowsPage(apiKey, {
        status: status === 'all' ? undefined : status,
        days,
        q: q.q,
        sort: q.sort,
        dir: q.dir,
        limit: q.limit,
        offset: q.offset,
      })
      setEmpty(page.total === 0 && !q.q && status === 'active')
      return page
    },
    [apiKey, status, days],
  )

  const onArchive = async (wf: WorkflowDefinitionResponse) => {
    if (!apiKey) return
    const ok = await confirm({
      title: `Archive ${wf.name}?`,
      description: 'New traffic stops matching this workflow. Its runs and history are kept, and you can restore it later.',
      confirmLabel: 'Archive',
      destructive: true,
    })
    if (!ok) return
    try {
      await archiveWorkflow(apiKey, wf.id)
      toast.success(`${wf.name} archived`)
      setVersion((v) => v + 1)
    } catch (e) {
      toast.error(apiErrorMessage(e))
    }
  }

  const onRestore = async (wf: WorkflowDefinitionResponse) => {
    if (!apiKey) return
    try {
      const saved = await updateWorkflow(apiKey, wf.id, { status: 'active' })
      toast.success(`${wf.name} restored`, { description: saved.linked_runs ? `${saved.linked_runs} runs linked` : undefined })
      setVersion((v) => v + 1)
    } catch (e) {
      toast.error(apiErrorMessage(e))
    }
  }

  const columns: DataTableColumn<WorkflowDefinitionResponse>[] = [
    {
      key: 'name',
      header: 'Workflow',
      sortable: true,
      render: (wf) => (
        <div className="min-w-0">
          <Link href={routes.workflowsWorkflowId(wf.id)} className="font-medium text-indigo-600 hover:underline dark:text-indigo-400">{wf.name}</Link>
          {wf.description && <p className="truncate text-[11px] text-slate-500">{wf.description}</p>}
        </div>
      ),
    },
    { key: 'feature_tag', header: 'Feature tag', render: (wf) => wf.feature_tag ? <code className="text-xs">{wf.feature_tag}</code> : <span className="text-xs text-status-warning">not linked</span> },
    { key: 'gateway_alias', header: 'Gateway alias', defaultHidden: true, render: (wf) => wf.gateway_alias ? <code className="text-xs">{wf.gateway_alias}</code> : '—' },
    { key: 'runs', header: `Runs (${days}d)`, value: (wf) => wf.stats?.runs ?? 0 },
    { key: 'success', header: 'Success', value: (wf) => wf.stats?.success_rate ?? null, render: (wf) => pct(wf.stats?.success_rate) },
    { key: 'cost_per_success', header: 'Cost / success', value: (wf) => Number(wf.stats?.cost_per_success ?? 0), render: (wf) => money(wf.stats?.cost_per_success) },
    { key: 'cost', header: 'Spend', value: (wf) => Number(wf.stats?.total_cost_usd ?? 0), render: (wf) => money(wf.stats?.total_cost_usd) },
    { key: 'p95', header: 'p95 latency', value: (wf) => wf.stats?.p95_latency_ms ?? null, render: (wf) => ms(wf.stats?.p95_latency_ms) },
    { key: 'last_run', header: 'Last run', value: (wf) => wf.stats?.last_run_at ?? '', render: (wf) => relTime(wf.stats?.last_run_at) },
    { key: 'owner', header: 'Owner', defaultHidden: true },
    { key: 'status', header: 'Status', render: (wf) => <StatusBadge status={wf.status} /> },
    { key: 'created_at', header: 'Created', sortable: true, defaultHidden: true, value: (wf) => wf.created_at, render: (wf) => new Date(wf.created_at).toLocaleDateString() },
    {
      key: 'actions',
      header: 'Actions',
      value: () => '',
      render: (wf) =>
        canWrite ? (
          <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
            <button type="button" aria-label={`Edit ${wf.name}`} title="Edit" onClick={() => { setEditing(wf); setSheetOpen(true) }} className="rounded-md p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800">
              <Pencil className="h-3.5 w-3.5" />
            </button>
            {wf.status === 'archived' ? (
              <button type="button" aria-label={`Restore ${wf.name}`} title="Restore" onClick={() => void onRestore(wf)} className="rounded-md p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800 dark:hover:bg-slate-800">
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button type="button" aria-label={`Archive ${wf.name}`} title="Archive" onClick={() => void onArchive(wf)} className="rounded-md p-1 text-slate-500 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950/40">
                <Archive className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        ) : null,
    },
  ]

  return (
    <div className="space-y-4">
      {dialog}
      <PageHeader
        icon={Route}
        title="Workflows"
        description="Every unit of AI work you run: its runs, cost, quality, budgets and policies in one place."
        actions={
          canWrite ? (
            <>
              <Link href={'/workflows/new'} className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800">
                <Sparkles className="h-4 w-4" aria-hidden="true" /> Guided setup
              </Link>
              <button type="button" onClick={() => { setEditing(null); setSheetOpen(true) }} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
                <Plus className="h-4 w-4" aria-hidden="true" /> New workflow
              </button>
            </>
          ) : undefined
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div role="group" aria-label="Status filter" className="flex gap-1">
          {['active', 'archived', 'all'].map((s) => (
            <button key={s} type="button" aria-pressed={status === s} onClick={() => setParam('status', s)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium capitalize ${status === s ? 'bg-indigo-600 text-white' : 'border border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300'}`}>
              {s}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1.5 text-xs text-slate-500">
          Window
          <select aria-label="Stats window" value={days} onChange={(e) => setParam('days', e.target.value)} className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-800">
            {WINDOWS.map((d) => <option key={d} value={d}>{d} days</option>)}
          </select>
        </label>
      </div>

      {empty ? (
        <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700">
          <EmptyState
            icon={Route}
            title="Create your first workflow"
            description="A workflow names a piece of AI work (a support bot, a code reviewer) and collects its runs, cost, quality and controls. Link it to a feature tag or a gateway alias and traffic is attributed automatically."
            action={canWrite ? <Link href={'/workflows/new'} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"><Sparkles className="h-4 w-4" aria-hidden="true" /> Start guided setup</Link> : undefined}
          />
        </div>
      ) : null}
      <div className={empty ? 'hidden' : undefined}>
        <DataTable
          key={`${status}-${days}-${version}`}
          label="Workflows"
          urlPrefix="wf_"
          columns={columns}
          rowKey={(wf) => wf.id}
          fetchPage={fetchPage}
          searchPlaceholder="Search name or tag…"
          csvFileName="workflows.csv"
          emptyTitle="No workflows match"
          emptyDescription="Try another status or search."
          onRowClick={(wf) => router.push(routes.workflowsWorkflowId(wf.id))}
        />
      </div>

      <WorkflowSheet open={sheetOpen} onOpenChange={setSheetOpen} workflow={editing} onSaved={(wf) => {
        setVersion((v) => v + 1)
        if (!editing) router.push(routes.workflowsWorkflowId(wf.id))
      }} />
    </div>
  )
}

export default function WorkflowsPage() {
  return (
    <Suspense fallback={null}>
      <WorkflowsInner />
    </Suspense>
  )
}
