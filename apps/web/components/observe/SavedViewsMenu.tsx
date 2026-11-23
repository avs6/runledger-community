'use client'

import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Bookmark, Check, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { useConfirm } from '@/components/ui/confirm-dialog'
import { deleteSavedView, listSavedViews, saveView } from '@/lib/api/observe'
import type { SavedView, SavedViewPage } from '@/types/api'

/** Query keys that are paging state, not part of a saved view. */
const TRANSIENT_KEYS = new Set(['cursor', 'page', 'offset'])

export function viewQuery(params: URLSearchParams): string {
  const out = new URLSearchParams()
  params.forEach((value, key) => {
    if (!TRANSIENT_KEYS.has(key) && value) out.set(key, value)
  })
  out.sort()
  return out.toString()
}

/**
 * Per-user saved views for an Observe list page: a name plus the page's filter query
 * string, stored by `/runs/saved-views` (minimal until the W2-C preferences API).
 */
function SavedViewsMenuInner({ page }: { page: SavedViewPage }) {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string } | null)?.apiKey
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const { confirm, dialog } = useConfirm()
  const [open, setOpen] = useState(false)
  const [views, setViews] = useState<SavedView[]>([])
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  const current = viewQuery(new URLSearchParams(params.toString()))

  const load = useCallback(async () => {
    if (!apiKey) return
    try {
      setViews(await listSavedViews(apiKey, page))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load saved views')
    }
  }, [apiKey, page])

  useEffect(() => { if (open) void load() }, [open, load])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  async function onSave() {
    if (!apiKey || !name.trim()) return
    try {
      await saveView(apiKey, { page, name: name.trim(), query: current })
      toast.success(`Saved view "${name.trim()}"`)
      setName('')
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not save view')
    }
  }

  async function onDelete(view: SavedView) {
    if (!apiKey) return
    const ok = await confirm({
      title: `Delete saved view "${view.name}"?`,
      description: 'Only the saved filter set is removed; no data changes.',
      confirmLabel: 'Delete',
      destructive: true,
    })
    if (!ok) return
    try {
      await deleteSavedView(apiKey, view.id)
      setViews(v => v.filter(x => x.id !== view.id))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Could not delete view')
    }
  }

  return (
    <div ref={ref} className="relative">
      {dialog}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex h-8 items-center gap-1.5 rounded-lg border border-input bg-background px-3 text-sm font-medium shadow-sm hover:bg-accent"
      >
        <Bookmark className="h-3.5 w-3.5" aria-hidden /> Views
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-30 mt-1 w-72 rounded-xl border border-border bg-popover p-2 shadow-lg">
          {error && <p role="alert" className="px-2 py-1 text-xs text-status-error">{error}</p>}
          {views.length === 0 && !error ? (
            <p className="px-2 py-1.5 text-xs text-muted-foreground">No saved views yet. Set filters, then save them here.</p>
          ) : (
            <ul className="max-h-60 overflow-y-auto">
              {views.map(view => (
                <li key={view.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    role="menuitem"
                    className="flex flex-1 items-center gap-2 truncate rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent"
                    onClick={() => { setOpen(false); router.push(view.query ? `${pathname}?${view.query}` : pathname) }}
                  >
                    {view.query === current ? <Check className="h-3.5 w-3.5 text-status-success" aria-label="Active" /> : <span className="w-3.5" />}
                    <span className="truncate">{view.name}</span>
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete saved view ${view.name}`}
                    onClick={() => void onDelete(view)}
                    className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-status-error"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <form
            className="mt-2 flex gap-1 border-t border-border pt-2"
            onSubmit={e => { e.preventDefault(); void onSave() }}
          >
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Name the current filters"
              aria-label="Saved view name"
              maxLength={120}
              className="h-8 flex-1 rounded-md border border-input bg-background px-2 text-sm"
            />
            <button type="submit" disabled={!name.trim()} className="h-8 rounded-md bg-primary px-3 text-xs font-semibold text-primary-foreground disabled:opacity-50">
              Save
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

export default function SavedViewsMenu({ page }: { page: SavedViewPage }) {
  return (
    <Suspense fallback={null}>
      <SavedViewsMenuInner page={page} />
    </Suspense>
  )
}
