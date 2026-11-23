'use client'

/**
 * Edit a dataset's name, description and items (review B-24). Eval items have an
 * editable input; replay items (curated from runs) keep their captured messages and
 * only their expected output is editable.
 */

import { useEffect, useState } from 'react'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { updateEvalDataset } from '@/lib/api'
import type { DatasetItem, EvalDataset } from '@/types/api'

const cellCls =
  'w-full rounded border border-slate-200 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800'

function messagesPreview(item: DatasetItem): string {
  const last = item.messages?.filter((m) => m.role === 'user').at(-1)
  return typeof last?.content === 'string' ? last.content : `${item.messages?.length ?? 0} messages`
}

export function DatasetEditor({
  apiKey,
  dataset,
  canWrite,
  onSaved,
}: {
  apiKey: string
  dataset: EvalDataset
  canWrite: boolean
  onSaved: (ds: EvalDataset) => void
}) {
  const [name, setName] = useState(dataset.name)
  const [description, setDescription] = useState(dataset.description ?? '')
  const [items, setItems] = useState<DatasetItem[]>(dataset.items)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setName(dataset.name)
    setDescription(dataset.description ?? '')
    setItems(dataset.items)
    setDirty(false)
  }, [dataset])

  const update = (i: number, patch: Partial<DatasetItem>) => {
    setItems((prev) => prev.map((it, idx) => (idx === i ? { ...it, ...patch } : it)))
    setDirty(true)
  }

  const save = async () => {
    const bad = items.findIndex((it) => !it.input?.trim() && !it.messages?.length)
    if (bad >= 0) return toast.error(`Item ${bad + 1} needs an input`)
    setSaving(true)
    try {
      const ds = await updateEvalDataset(apiKey, dataset.id, {
        name: name.trim(),
        description: description.trim(),
        items: items.map((it) => ({ ...it, expected_output: it.expected_output || null })),
      })
      toast.success('Dataset saved')
      setDirty(false)
      onSaved(ds)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2 md:grid-cols-2">
        <label className="text-xs text-slate-500">
          Name
          <input className={cellCls} value={name} disabled={!canWrite} onChange={(e) => { setName(e.target.value); setDirty(true) }} />
        </label>
        <label className="text-xs text-slate-500">
          Description
          <input className={cellCls} value={description} disabled={!canWrite} onChange={(e) => { setDescription(e.target.value); setDirty(true) }} />
        </label>
      </div>
      <div className="max-h-96 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white text-xs text-slate-400 dark:bg-slate-900">
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="py-2 pr-2 text-left">#</th>
              <th className="py-2 pr-2 text-left">Input</th>
              <th className="py-2 pr-2 text-left">Expected output</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i} className="border-b border-slate-100 align-top dark:border-slate-800">
                <td className="py-1.5 pr-2 text-slate-400">{i + 1}</td>
                <td className="py-1.5 pr-2">
                  {item.messages?.length ? (
                    <span className="text-xs text-slate-500" title="Captured conversation from a recorded run">
                      Replay: {messagesPreview(item)}
                    </span>
                  ) : (
                    <input aria-label={`Input for item ${i + 1}`} className={cellCls} value={item.input ?? ''} disabled={!canWrite} onChange={(e) => update(i, { input: e.target.value })} />
                  )}
                </td>
                <td className="py-1.5 pr-2">
                  <input aria-label={`Expected output for item ${i + 1}`} className={cellCls} value={item.expected_output ?? ''} disabled={!canWrite} onChange={(e) => update(i, { expected_output: e.target.value })} />
                </td>
                <td className="py-1.5">
                  {canWrite ? (
                    <button type="button" aria-label={`Remove item ${i + 1}`} onClick={() => { setItems((prev) => prev.filter((_, idx) => idx !== i)); setDirty(true) }} className="rounded p-1 text-slate-400 hover:text-rose-600">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 ? <p className="py-4 text-center text-sm text-slate-400">No items yet.</p> : null}
      </div>
      {canWrite ? (
        <div className="flex justify-between">
          <button type="button" onClick={() => { setItems((prev) => [...prev, { input: '', expected_output: null, metadata: {} }]); setDirty(true) }} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800">
            <Plus className="h-4 w-4" /> Add item
          </button>
          <button type="button" onClick={() => void save()} disabled={!dirty || saving} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Save changes
          </button>
        </div>
      ) : null}
    </div>
  )
}
