'use client'

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { RotateCcw, Trash2 } from 'lucide-react'
import {
  apiErrorMessage,
  discardIngestDeadLetter,
  listIngestDeadLetters,
  replayAllIngestDeadLetters,
  replayIngestDeadLetter,
} from '@/lib/api'
import type { IngestDeadLetter } from '@/types/api'

const PAGE = 20

/**
 * Ingest events the pipeline could not apply (bad data, constraint or FK errors).
 * Workspace admins replay them through the normal, idempotent pipeline or discard them.
 */
export default function DeadLettersPanel({ apiKey }: { apiKey: string }) {
  const [items, setItems] = useState<IngestDeadLetter[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [open, setOpen] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listIngestDeadLetters(apiKey, 'pending', PAGE, offset)
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Failed to load dead letters'))
    } finally {
      setLoading(false)
    }
  }, [apiKey, offset])

  useEffect(() => {
    void load()
  }, [load])

  async function replay(id: string) {
    setBusy(id)
    try {
      await replayIngestDeadLetter(apiKey, id)
      toast.success('Event re-queued')
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Replay failed'))
    } finally {
      setBusy(null)
    }
  }

  async function replayAll() {
    setBusy('all')
    try {
      const res = await replayAllIngestDeadLetters(apiKey)
      toast.success(`${res.requeued} event(s) re-queued`)
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Replay failed'))
    } finally {
      setBusy(null)
    }
  }

  async function discard(id: string) {
    if (!confirm('Discard this event? It will not be ingested.')) return
    setBusy(id)
    try {
      await discardIngestDeadLetter(apiKey, id)
      toast.success('Event discarded')
      await load()
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Discard failed'))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white/90 p-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">Dead letters</p>
          <p className="text-[10px] text-slate-400">Events the pipeline could not apply. Replays are idempotent.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-400">{total} pending</span>
          <button
            type="button"
            disabled={total === 0 || busy !== null}
            onClick={() => void replayAll()}
            className="rounded border border-slate-300 px-2 py-0.5 text-[10px] font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300"
          >
            {busy === 'all' ? 'Replaying…' : 'Replay all'}
          </button>
        </div>
      </div>
      {loading && items.length === 0 ? (
        <div className="h-6 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
      ) : items.length === 0 ? (
        <div className="rounded border border-dashed border-slate-300 py-4 text-center text-[11px] text-slate-400 dark:border-slate-700">
          No failed events. Everything sent was applied.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr>
                {['When', 'Event', 'Run', 'Error', 'Attempts', ''].map((h) => (
                  <th key={h} className="px-2 py-1 text-left text-[10px] font-semibold uppercase tracking-widest text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((item) => (
                <tr key={item.id} className="align-top">
                  <td className="whitespace-nowrap px-2 py-1 font-mono text-slate-500">{new Date(item.created_at).toLocaleString()}</td>
                  <td className="px-2 py-1 font-medium text-slate-700 dark:text-slate-300">{item.event_type ?? '—'}</td>
                  <td className="px-2 py-1 font-mono text-[10px] text-slate-500">{item.run_id?.slice(0, 8) ?? '—'}</td>
                  <td className="max-w-md px-2 py-1 text-[11px] text-red-600 dark:text-red-400">
                    <button type="button" className="text-left hover:underline" onClick={() => setOpen(open === item.id ? null : item.id)}>
                      {item.error.slice(0, 120)}
                    </button>
                    {open === item.id && (
                      <pre className="mt-1 max-h-48 overflow-auto rounded bg-slate-950 p-2 text-[10px] text-green-400">
                        {JSON.stringify(item.event, null, 2)}
                      </pre>
                    )}
                  </td>
                  <td className="px-2 py-1 text-right text-slate-500">{item.attempts}</td>
                  <td className="whitespace-nowrap px-2 py-1 text-right">
                    <button
                      type="button"
                      aria-label="Replay event"
                      disabled={busy !== null}
                      onClick={() => void replay(item.id)}
                      className="mr-1 rounded p-1 text-indigo-600 hover:bg-indigo-50 disabled:opacity-50 dark:text-indigo-400 dark:hover:bg-indigo-950/30"
                    >
                      <RotateCcw className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      aria-label="Discard event"
                      disabled={busy !== null}
                      onClick={() => void discard(item.id)}
                      className="rounded p-1 text-red-500 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-red-950/30"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-1 flex justify-end gap-1.5 text-[10px]">
            <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}
              className="rounded border border-slate-300 px-2 py-0.5 disabled:opacity-50 dark:border-slate-700">Prev</button>
            <button type="button" disabled={offset + items.length >= total} onClick={() => setOffset(offset + PAGE)}
              className="rounded border border-slate-300 px-2 py-0.5 disabled:opacity-50 dark:border-slate-700">Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
