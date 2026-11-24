'use client'

/** Edit an experiment's name, models and evaluators (review B-24). */

import { useEffect, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { getPlaygroundModels, listEvaluators, updateEvalExperiment } from '@/lib/api'
import type { EvalExperiment, EvaluatorResponse, PlaygroundModel } from '@/types/api'

const inputCls =
  'w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800'

export function ExperimentEditDialog({
  apiKey,
  experiment,
  onClose,
  onSaved,
}: {
  apiKey: string
  experiment: EvalExperiment
  onClose: () => void
  onSaved: (exp: EvalExperiment) => void
}) {
  const [name, setName] = useState(experiment.name)
  const [description, setDescription] = useState(experiment.description ?? '')
  const [models, setModels] = useState<string[]>(experiment.models.map((m) => m.model))
  const [evaluatorIds, setEvaluatorIds] = useState<string[]>(experiment.evaluator_ids)
  const [aliases, setAliases] = useState<PlaygroundModel[]>([])
  const [evaluators, setEvaluators] = useState<EvaluatorResponse[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([getPlaygroundModels(apiKey), listEvaluators(apiKey)])
      .then(([m, e]) => {
        setAliases(m.items)
        setEvaluators(e.items)
      })
      .catch((err) => toast.error(err instanceof Error ? err.message : 'Failed to load options'))
  }, [apiKey])

  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v])
  // Keep current models selectable even if their route was removed since.
  const aliasNames = Array.from(new Set([...models, ...aliases.map((a) => a.alias)]))

  const save = async () => {
    if (!models.length) return toast.error('Pick at least one route alias')
    setSaving(true)
    try {
      const exp = await updateEvalExperiment(apiKey, experiment.id, {
        name: name.trim(),
        description: description.trim(),
        models: models.map((m) => ({ model: m })),
        evaluator_ids: evaluatorIds,
      })
      toast.success('Experiment saved; run it again to refresh results')
      onSaved(exp)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Edit experiment">
      <div className="w-full max-w-lg space-y-3 rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Edit experiment</h2>
          <button type="button" aria-label="Close" onClick={onClose} className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-4 w-4" />
          </button>
        </div>
        <label className="block text-sm">
          Name
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="block text-sm">
          Description
          <input className={inputCls} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <fieldset className="text-sm">
          <legend className="mb-1">Route aliases (first selected = baseline)</legend>
          <div className="flex flex-wrap gap-2">
            {aliasNames.map((a) => (
              <label key={a} className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 dark:border-slate-700">
                <input type="checkbox" checked={models.includes(a)} onChange={() => setModels(toggle(models, a))} />
                {a}
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset className="text-sm">
          <legend className="mb-1">Evaluators</legend>
          <div className="flex flex-wrap gap-2">
            {evaluators.map((ev) => (
              <label key={ev.id} className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 dark:border-slate-700">
                <input type="checkbox" checked={evaluatorIds.includes(ev.id)} onChange={() => setEvaluatorIds(toggle(evaluatorIds, ev.id))} />
                {ev.name}
              </label>
            ))}
            {evaluators.length === 0 ? <span className="text-xs text-slate-500">No evaluators.</span> : null}
          </div>
        </fieldset>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">Cancel</button>
          <button type="button" onClick={() => void save()} disabled={saving || !name.trim()} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
