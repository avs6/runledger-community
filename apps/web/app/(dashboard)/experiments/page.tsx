'use client'

/**
 * Experiments: the one experiment system (review B-07). `eval` runs dataset inputs
 * (optionally with a prompt version) and `replay` re-runs captured conversations of
 * recorded runs; both go through the gateway once per route alias (B-08).
 */

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { FlaskConical, Loader2, Plus, Trash2, X } from 'lucide-react'
import { toast } from 'sonner'
import {
  apiFetchPage,
  createEvalExperiment,
  deleteEvalExperiment,
  getPlaygroundModels,
  listEvalDatasets,
  listEvaluators,
  listPrompts,
} from '@/lib/api'
import type {
  EvalDataset,
  EvalExperiment,
  EvaluatorResponse,
  ExperimentMode,
  PlaygroundModel,
  PromptResponse,
} from '@/types/api'
import { PageHeader } from '@/components/ui/page-header'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { useRole } from '@/components/rbac/useRole'
import { routes } from '@/lib/routes'

const inputCls =
  'w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100'

const STATUS_CLS: Record<EvalExperiment['status'], string> = {
  pending: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  running: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
  completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300',
  failed: 'bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300',
}

export default function ExperimentsPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const { canWrite } = useRole()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const mode = (searchParams.get('mode') as ExperimentMode | null) ?? null
  const { confirm, dialog } = useConfirm()
  const [refreshKey, setRefreshKey] = useState(0)

  const [showCreate, setShowCreate] = useState(false)
  const [prompts, setPrompts] = useState<PromptResponse[]>([])
  const [datasets, setDatasets] = useState<EvalDataset[]>([])
  const [evaluators, setEvaluators] = useState<EvaluatorResponse[]>([])
  const [aliases, setAliases] = useState<PlaygroundModel[]>([])
  const [form, setForm] = useState({
    name: '',
    description: '',
    mode: 'eval' as ExperimentMode,
    datasetId: '',
    promptName: '',
    promptVersion: '',
    evaluatorIds: [] as string[],
    models: [] as string[],
  })
  const [creating, setCreating] = useState(false)

  const setMode = (next: string) => {
    const qs = new URLSearchParams(searchParams.toString())
    if (next) qs.set('mode', next)
    else qs.delete('mode')
    router.replace(`${pathname}?${qs.toString()}`)
  }

  const openCreate = useCallback(async () => {
    setShowCreate(true)
    try {
      const [p, d, e, m] = await Promise.all([
        listPrompts(apiKey),
        listEvalDatasets(apiKey, 200),
        listEvaluators(apiKey),
        getPlaygroundModels(apiKey),
      ])
      setPrompts(p.items)
      setDatasets(d.items)
      setEvaluators(e.items.filter((ev) => ev.status === 'active'))
      setAliases(m.items)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load form options')
    }
  }, [apiKey])

  useEffect(() => {
    if (searchParams.get('new') === '1' && apiKey) void openCreate()
  }, [searchParams, apiKey, openCreate])

  const create = async () => {
    if (!form.name.trim()) return toast.error('Name is required')
    if (!form.datasetId) return toast.error('Pick a dataset')
    if (!form.models.length) return toast.error('Pick at least one route alias')
    setCreating(true)
    try {
      const exp = await createEvalExperiment(apiKey, {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        mode: form.mode,
        dataset_id: form.datasetId,
        prompt_name: form.mode === 'eval' && form.promptName ? form.promptName : undefined,
        prompt_version:
          form.mode === 'eval' && form.promptVersion ? Number(form.promptVersion) : undefined,
        evaluator_ids: form.evaluatorIds,
        models: form.models.map((m) => ({ model: m })),
      })
      toast.success('Experiment created')
      router.push(routes.experimentsExperimentId(exp.id))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  const remove = async (exp: EvalExperiment) => {
    const ok = await confirm({
      title: `Delete experiment "${exp.name}"?`,
      description: 'Its results are removed. Runs it recorded through the gateway stay.',
      confirmLabel: 'Delete',
      destructive: true,
    })
    if (!ok) return
    try {
      await deleteEvalExperiment(apiKey, exp.id)
      toast.success('Experiment deleted')
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const columns: DataTableColumn<EvalExperiment>[] = [
    { key: 'name', header: 'Name', sortable: true },
    { key: 'mode', header: 'Mode', render: (e) => (e.mode === 'replay' ? 'Replay' : 'Eval') },
    {
      key: 'status',
      header: 'Status',
      render: (e) => (
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLS[e.status]}`}>
          {e.status}
        </span>
      ),
    },
    {
      key: 'prompt',
      header: 'Prompt',
      render: (e) => (e.prompt_name ? `${e.prompt_name}${e.prompt_version ? ` v${e.prompt_version}` : ''}` : '—'),
      value: (e) => e.prompt_name,
    },
    { key: 'models', header: 'Models', render: (e) => e.models.map((m) => m.label || m.model).join(', ') },
    {
      key: 'score',
      header: 'Avg score',
      render: (e) => {
        const s = e.results?.summary?.avg_score
        return s === null || s === undefined ? '—' : s.toFixed(3)
      },
      value: (e) => e.results?.summary?.avg_score ?? null,
    },
    { key: 'run_count', header: 'Gateway calls' },
    { key: 'created_at', header: 'Created', render: (e) => new Date(e.created_at).toLocaleString() },
    {
      key: 'actions',
      header: '',
      render: (e) =>
        canWrite ? (
          <button
            type="button"
            aria-label={`Delete experiment ${e.name}`}
            onClick={(ev) => {
              ev.stopPropagation()
              void remove(e)
            }}
            className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        ) : null,
    },
  ]

  const toggle = (list: string[], v: string) =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v]

  return (
    <div className="space-y-6 p-6">
      {dialog}
      <PageHeader
        icon={FlaskConical}
        title="Experiments"
        description="Run a dataset through the gateway against several route aliases, score the outputs, and turn the winner into a route recommendation. Replay mode re-runs captured conversations of recorded runs."
        actions={
          canWrite ? (
            <button
              type="button"
              onClick={() => void openCreate()}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" /> New experiment
            </button>
          ) : null
        }
      />

      <div className="flex items-center gap-2" role="group" aria-label="Filter by mode">
        {[
          ['', 'All'],
          ['eval', 'Eval'],
          ['replay', 'Replay'],
        ].map(([value, label]) => (
          <button
            key={value || 'all'}
            type="button"
            aria-pressed={(mode ?? '') === value}
            onClick={() => setMode(value)}
            className={`rounded-full px-3 py-1 text-sm ${
              (mode ?? '') === value
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {apiKey ? (
        <DataTable
          key={`${mode ?? 'all'}-${refreshKey}`}
          label="Experiments"
          columns={columns}
          rowKey={(e) => e.id}
          urlPrefix="exp"
          csvFileName="experiments.csv"
          searchable={false}
          emptyTitle="No experiments yet"
          emptyDescription="Create one to compare route aliases on a dataset, or replay recorded runs."
          onRowClick={(e) => router.push(routes.experimentsExperimentId(e.id))}
          fetchPage={(q) =>
            apiFetchPage<EvalExperiment>(
              `/experiments?limit=${q.limit}&offset=${q.offset}${mode ? `&mode=${mode}` : ''}`,
              apiKey
            )
          }
        />
      ) : null}

      {showCreate ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="New experiment">
          <div className="max-h-[90vh] w-full max-w-xl space-y-3 overflow-y-auto rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">New experiment</h2>
              <button type="button" aria-label="Close" onClick={() => setShowCreate(false)} className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="block text-sm">
              Name
              <input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label className="block text-sm">
              Description
              <input className={inputCls} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </label>
            <label className="block text-sm">
              Mode
              <select className={inputCls} value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value as ExperimentMode })}>
                <option value="eval">Eval: dataset inputs (+ prompt)</option>
                <option value="replay">Replay: captured conversations of runs</option>
              </select>
            </label>
            <label className="block text-sm">
              Dataset
              <select className={inputCls} value={form.datasetId} onChange={(e) => setForm({ ...form, datasetId: e.target.value })}>
                <option value="">Select…</option>
                {datasets
                  .filter((d) => (form.mode === 'replay' ? d.source === 'runs' : true))
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.item_count} items{d.source === 'runs' ? ', from runs' : ''})
                    </option>
                  ))}
              </select>
            </label>
            {form.mode === 'eval' ? (
              <div className="grid grid-cols-2 gap-2">
                <label className="block text-sm">
                  Prompt (system)
                  <select className={inputCls} value={form.promptName} onChange={(e) => setForm({ ...form, promptName: e.target.value })}>
                    <option value="">None</option>
                    {prompts.map((p) => (
                      <option key={p.id} value={p.name}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  Version (blank = latest)
                  <input className={inputCls} inputMode="numeric" value={form.promptVersion} onChange={(e) => setForm({ ...form, promptVersion: e.target.value })} />
                </label>
              </div>
            ) : null}
            <fieldset className="text-sm">
              <legend className="mb-1">Route aliases (first = baseline)</legend>
              {aliases.length === 0 ? (
                <p className="text-xs text-slate-500">No active gateway routes. Add a route under Gateway first.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {aliases.map((a) => (
                    <label key={a.alias} className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 dark:border-slate-700">
                      <input type="checkbox" checked={form.models.includes(a.alias)} onChange={() => setForm({ ...form, models: toggle(form.models, a.alias) })} />
                      {a.alias}
                      <span className="text-xs text-slate-500">({a.targets.join(', ')})</span>
                    </label>
                  ))}
                </div>
              )}
            </fieldset>
            <fieldset className="text-sm">
              <legend className="mb-1">Evaluators (optional)</legend>
              <div className="flex flex-wrap gap-2">
                {evaluators.map((ev) => (
                  <label key={ev.id} className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 dark:border-slate-700">
                    <input type="checkbox" checked={form.evaluatorIds.includes(ev.id)} onChange={() => setForm({ ...form, evaluatorIds: toggle(form.evaluatorIds, ev.id) })} />
                    {ev.name}
                  </label>
                ))}
                {evaluators.length === 0 ? (
                  <span className="text-xs text-slate-500">Items with an expected output are scored by match even without evaluators.</span>
                ) : null}
              </div>
            </fieldset>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                Cancel
              </button>
              <button type="button" onClick={() => void create()} disabled={creating} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Create
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
