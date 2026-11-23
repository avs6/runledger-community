'use client'

/**
 * Playground sessions (review B-24): create, select, rename, favourite and delete.
 * Selecting a session loads its system prompt and scopes new requests and history to it.
 */

import { useState } from 'react'
import { Pencil, Plus, Star, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { createPlaygroundSession, deletePlaygroundSession, updatePlaygroundSession } from '@/lib/api'
import type { PlaygroundSessionResponse } from '@/types/api'
import { useConfirm } from '@/components/ui/confirm-dialog'

export function SessionsBar({
  apiKey,
  sessions,
  activeId,
  systemPrompt,
  onSessionsChange,
  onSelect,
}: {
  apiKey: string
  sessions: PlaygroundSessionResponse[]
  activeId: string | null
  systemPrompt: string
  onSessionsChange: (sessions: PlaygroundSessionResponse[]) => void
  onSelect: (session: PlaygroundSessionResponse | null) => void
}) {
  const { confirm, dialog } = useConfirm()
  const [busy, setBusy] = useState(false)
  const active = sessions.find((s) => s.id === activeId) ?? null

  const run = async (fn: () => Promise<void>) => {
    setBusy(true)
    try {
      await fn()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Session update failed')
    } finally {
      setBusy(false)
    }
  }

  const create = () =>
    run(async () => {
      const name = window.prompt('Session name')?.trim()
      if (!name) return
      const s = await createPlaygroundSession(apiKey, { name, system_prompt: systemPrompt || undefined })
      onSessionsChange([s, ...sessions])
      onSelect(s)
    })

  const rename = (s: PlaygroundSessionResponse) =>
    run(async () => {
      const name = window.prompt('Rename session', s.name ?? '')?.trim()
      if (!name || name === s.name) return
      const u = await updatePlaygroundSession(apiKey, s.id, { name })
      onSessionsChange(sessions.map((x) => (x.id === u.id ? u : x)))
    })

  const favorite = (s: PlaygroundSessionResponse) =>
    run(async () => {
      const u = await updatePlaygroundSession(apiKey, s.id, { is_favorite: !s.is_favorite })
      onSessionsChange(sessions.map((x) => (x.id === u.id ? u : x)))
    })

  const saveSystemPrompt = (s: PlaygroundSessionResponse) =>
    run(async () => {
      const u = await updatePlaygroundSession(apiKey, s.id, { system_prompt: systemPrompt })
      onSessionsChange(sessions.map((x) => (x.id === u.id ? u : x)))
      toast.success('System prompt saved to the session')
    })

  const remove = (s: PlaygroundSessionResponse) =>
    run(async () => {
      const ok = await confirm({
        title: `Delete session "${s.name ?? 'Untitled'}"?`,
        description: 'Its requests stay in history.',
        confirmLabel: 'Delete',
        destructive: true,
      })
      if (!ok) return
      await deletePlaygroundSession(apiKey, s.id)
      onSessionsChange(sessions.filter((x) => x.id !== s.id))
      if (activeId === s.id) onSelect(null)
    })

  const ordered = [...sessions].sort((a, b) => Number(b.is_favorite) - Number(a.is_favorite))

  return (
    <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label="Playground sessions">
      {dialog}
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Session</span>
      <button
        type="button"
        onClick={() => onSelect(null)}
        aria-pressed={activeId === null}
        className={`rounded-full px-2 py-0.5 text-[10px] ${activeId === null ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}
      >
        None
      </button>
      {ordered.map((s) => (
        <span key={s.id} className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-[10px] ${activeId === s.id ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>
          <button type="button" onClick={() => onSelect(s)} aria-pressed={activeId === s.id}>
            {s.name ?? 'Untitled'}
          </button>
          <button type="button" aria-label={`${s.is_favorite ? 'Unfavourite' : 'Favourite'} ${s.name ?? 'session'}`} onClick={() => void favorite(s)} disabled={busy}>
            <Star className={`h-3 w-3 ${s.is_favorite ? 'fill-current' : ''}`} />
          </button>
          <button type="button" aria-label={`Rename ${s.name ?? 'session'}`} onClick={() => void rename(s)} disabled={busy}>
            <Pencil className="h-3 w-3" />
          </button>
          <button type="button" aria-label={`Delete ${s.name ?? 'session'}`} onClick={() => void remove(s)} disabled={busy}>
            <Trash2 className="h-3 w-3" />
          </button>
        </span>
      ))}
      <button type="button" onClick={() => void create()} disabled={busy} className="inline-flex items-center gap-0.5 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300">
        <Plus className="h-3 w-3" /> New
      </button>
      {active && systemPrompt !== (active.system_prompt ?? '') ? (
        <button type="button" onClick={() => void saveSystemPrompt(active)} disabled={busy} className="rounded-full border border-indigo-300 px-2 py-0.5 text-[10px] text-indigo-700 dark:border-indigo-700 dark:text-indigo-300">
          Save system prompt to session
        </button>
      ) : null}
    </div>
  )
}
