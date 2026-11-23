'use client'

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import type { RunawayHold } from '@/types/api'
import { createRunawayHold, listRunawayHolds, releaseRunawayHold } from '@/lib/api'
import { AsyncCard } from '@/components/ui/async-card'
import { DataTable, type DataTableColumn } from '@/components/ui/data-table'
import { useConfirm } from '@/components/ui/confirm-dialog'

const fieldCls =
  'rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100'

/**
 * Runaway protection (review cd:B-09): runs and sessions held after a retry storm or
 * token spike. The gateway refuses calls for a held subject with 429 until it is
 * released or the hold expires; /budgets/check reports it to SDK callers.
 */
export default function RunawayHoldsPanel({ apiKey }: { apiKey: string }) {
  const [holds, setHolds] = useState<RunawayHold[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [subjectType, setSubjectType] = useState<'run' | 'session'>('session')
  const [subjectId, setSubjectId] = useState('')
  const [minutes, setMinutes] = useState('60')
  const [saving, setSaving] = useState(false)
  const { confirm, dialog } = useConfirm()

  const load = useCallback(async () => {
    setError(null)
    try {
      setHolds((await listRunawayHolds(apiKey)).items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runaway holds')
    }
  }, [apiKey])

  useEffect(() => {
    void load()
  }, [load])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await createRunawayHold(apiKey, {
        subject_type: subjectType,
        subject_id: subjectId.trim(),
        minutes: Number(minutes) || 60,
      })
      setSubjectId('')
      toast.success('Hold placed: the gateway now refuses this ' + subjectType)
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to place hold')
    } finally {
      setSaving(false)
    }
  }

  async function handleRelease(hold: RunawayHold) {
    const ok = await confirm({
      title: `Release ${hold.subject_type} ${hold.subject_id}?`,
      description: 'Its calls go through the gateway again immediately.',
      confirmLabel: 'Release',
    })
    if (!ok) return
    try {
      await releaseRunawayHold(apiKey, hold.id)
      toast.success('Hold released')
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to release hold')
    }
  }

  const columns: DataTableColumn<RunawayHold>[] = [
    {
      key: 'subject',
      header: 'Subject',
      value: (h) => `${h.subject_type}:${h.subject_id}`,
      render: (h) => (
        <span className="font-mono text-xs">
          {h.subject_type}:{h.subject_id}
        </span>
      ),
    },
    { key: 'reason', header: 'Reason', sortable: true },
    {
      key: 'calls',
      header: 'Calls in 2 min',
      value: (h) => Number((h.details as { calls_in_window?: number }).calls_in_window ?? 0),
    },
    {
      key: 'created_at',
      header: 'Held at',
      sortable: true,
      render: (h) => new Date(h.created_at).toLocaleString(),
    },
    {
      key: 'state',
      header: 'State',
      value: (h) => (h.active ? 'active' : h.released_at ? 'released' : 'expired'),
      render: (h) =>
        h.active ? (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">
            active until {new Date(h.expires_at).toLocaleTimeString()}
          </span>
        ) : (
          <span className="text-xs text-slate-500">{h.released_at ? 'released' : 'expired'}</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      render: (h) =>
        h.active ? (
          <button
            type="button"
            onClick={() => handleRelease(h)}
            aria-label={`Release hold on ${h.subject_type} ${h.subject_id}`}
            className="rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Release
          </button>
        ) : null,
    },
  ]

  return (
    <div className="space-y-4">
      <form
        onSubmit={handleCreate}
        className="flex flex-wrap items-end gap-2 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
      >
        <label className="text-xs text-slate-600 dark:text-slate-300">
          Subject
          <select
            value={subjectType}
            onChange={(e) => setSubjectType(e.target.value as 'run' | 'session')}
            className={`mt-1 block ${fieldCls}`}
          >
            <option value="session">Session</option>
            <option value="run">Run</option>
          </select>
        </label>
        <label className="flex-1 text-xs text-slate-600 dark:text-slate-300">
          {subjectType === 'session' ? 'Session id (runledger.session_id)' : 'Run id'}
          <input
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            required
            className={`mt-1 block w-full ${fieldCls}`}
          />
        </label>
        <label className="text-xs text-slate-600 dark:text-slate-300">
          Minutes
          <input
            type="number"
            min={1}
            max={10080}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            className={`mt-1 block w-24 ${fieldCls}`}
          />
        </label>
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
        >
          {saving ? 'Holding…' : 'Hold'}
        </button>
      </form>
      <AsyncCard
        title="Runaway holds"
        description="Held after more than 20 calls in 2 minutes (per run or session) or a call above 100k input tokens. Held subjects get 429 from the gateway."
        loading={holds === null && !error}
        error={error}
        onRetry={load}
      >
        <DataTable
          label="Runaway holds"
          rows={holds ?? []}
          columns={columns}
          rowKey={(h) => h.id}
          urlPrefix="h_"
          searchable={false}
          csvFileName="runaway-holds.csv"
          emptyTitle="No holds"
          emptyDescription="Runaway protection hasn't stopped anything."
        />
      </AsyncCard>
      {dialog}
    </div>
  )
}
