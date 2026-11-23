'use client'

/** Edit an evaluator (review B-24: the PUT endpoint had no UI). */

import { useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { toast } from 'sonner'
import { updateEvaluator } from '@/lib/api'
import type { EvaluatorResponse } from '@/types/api'

const inputCls =
  'w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-violet-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'

// Read-only fields the API adds to a judge's config; never sent back.
const DISPLAY_ONLY = ['gateway_key_set', 'gateway_key_source']

export function EvaluatorEditDialog({
  apiKey,
  evaluator,
  onClose,
  onSaved,
}: {
  apiKey: string
  evaluator: EvaluatorResponse
  onClose: () => void
  onSaved: (ev: EvaluatorResponse) => void
}) {
  const editable = Object.fromEntries(
    Object.entries(evaluator.config).filter(([k]) => !DISPLAY_ONLY.includes(k))
  )
  const [name, setName] = useState(evaluator.name)
  const [description, setDescription] = useState(evaluator.description ?? '')
  const [status, setStatus] = useState(evaluator.status)
  const [configText, setConfigText] = useState(JSON.stringify(editable, null, 2))
  const [newKey, setNewKey] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const isJudge = evaluator.type === 'llm_judge'
  const keySet = Boolean(evaluator.config.gateway_key_set)

  const save = async () => {
    let config: Record<string, unknown>
    try {
      config = JSON.parse(configText)
    } catch {
      setError('Config is not valid JSON')
      return
    }
    if (isJudge && newKey.trim()) config.gateway_api_key = newKey.trim()
    setSaving(true)
    try {
      const ev = await updateEvaluator(apiKey, evaluator.id, {
        name: name.trim(),
        description: description.trim() || null,
        status,
        config,
      })
      toast.success('Evaluator saved')
      onSaved(ev)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label={`Edit evaluator ${evaluator.name}`}>
      <div className="w-full max-w-lg space-y-3 rounded-xl bg-white p-5 shadow-xl dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Edit evaluator</h2>
          <button type="button" aria-label="Close" onClick={onClose} className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-4 w-4" />
          </button>
        </div>
        <label className="block text-xs">
          Name
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="block text-xs">
          Description
          <input className={inputCls} value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label className="block text-xs">
          Status
          <select className={inputCls} value={status} onChange={(e) => setStatus(e.target.value as EvaluatorResponse['status'])}>
            <option value="active">active</option>
            <option value="inactive">inactive</option>
          </select>
        </label>
        <label className="block text-xs">
          Config (JSON)
          <textarea
            className={`${inputCls} font-mono`}
            rows={8}
            value={configText}
            onChange={(e) => {
              setConfigText(e.target.value)
              setError('')
            }}
          />
        </label>
        {isJudge ? (
          <label className="block text-xs">
            Gateway API key ({keySet ? 'set; leave blank to keep it' : 'not set'})
            <input
              className={inputCls}
              type="password"
              autoComplete="off"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder={keySet ? '•••••••• (unchanged)' : 'RunLedger API key, stored encrypted'}
            />
          </label>
        ) : null}
        {error ? <p role="alert" className="text-xs text-rose-600">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-800">
            Cancel
          </button>
          <button type="button" onClick={() => void save()} disabled={saving || !name.trim()} className="inline-flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50">
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
            Save
          </button>
        </div>
      </div>
    </div>
  )
}
