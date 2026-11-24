'use client'

/** Curate a replay dataset from recorded runs (POST /datasets/from-runs, review B-07/B-24). */

import { useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { createDatasetFromRuns } from '@/lib/api'
import type { EvalDataset } from '@/types/api'

const inputCls =
  'w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800'
const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi

export function FromRunsDialog({
  apiKey,
  onClose,
  onCreated,
}: {
  apiKey: string
  onClose: () => void
  onCreated: (ds: EvalDataset) => void
}) {
  const [name, setName] = useState('')
  const [runText, setRunText] = useState('')
  const [asExpected, setAsExpected] = useState(false)
  const [saving, setSaving] = useState(false)
  const runIds = Array.from(new Set(runText.match(UUID_RE) ?? []))

  const create = async () => {
    if (!name.trim() || runIds.length === 0) return
    setSaving(true)
    try {
      const ds = await createDatasetFromRuns(apiKey, {
        name: name.trim(),
        run_ids: runIds,
        use_output_as_expected: asExpected,
      })
      toast.success(`Replay dataset created with ${ds.item_count} item(s)`)
      onCreated(ds)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Dataset from runs">
      <div className="w-full max-w-lg space-y-3 rounded-xl bg-white p-6 shadow-xl dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Dataset from recorded runs</h2>
          <button type="button" aria-label="Close" onClick={onClose} className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Each run&apos;s captured conversation becomes an item you can replay against other route aliases. Runs
          without a captured payload are skipped.
        </p>
        <label className="block text-sm">
          Name
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="block text-sm">
          Run IDs (paste from Runs; one per line or comma-separated)
          <textarea className={`${inputCls} font-mono`} rows={5} value={runText} onChange={(e) => setRunText(e.target.value)} />
        </label>
        <p className="text-xs text-slate-500">{runIds.length} run ID(s) found</p>
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" checked={asExpected} onChange={(e) => setAsExpected(e.target.checked)} />
          Use each run&apos;s recorded reply as the expected output (regression check)
        </label>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">Cancel</button>
          <button type="button" onClick={() => void create()} disabled={saving || !name.trim() || runIds.length === 0} className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Create
          </button>
        </div>
      </div>
    </div>
  )
}
