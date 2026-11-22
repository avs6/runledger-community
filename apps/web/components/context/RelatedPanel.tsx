'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { Layers, RefreshCw } from 'lucide-react'
import { getEntityContext, type ContextEntity } from '@/lib/api'
import type { EntityContext } from '@/types/api'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'

/**
 * "Related" drawer: counts and links about one entity (its runs, spend, budgets and
 * policies), loaded only when opened. Replaces the posture cards that every page used to
 * fetch on mount.
 */
export function RelatedPanel({
  entity,
  id,
  label = 'Related',
}: {
  entity: ContextEntity
  id?: string | null
  label?: string
}) {
  const { data: session } = useSession()
  const apiKey = (session as Record<string, unknown> | null)?.apiKey as string | undefined
  const [context, setContext] = useState<EntityContext | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    if (!apiKey || loading) return
    setLoading(true)
    setError(null)
    try {
      setContext(await getEntityContext(apiKey, entity, id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load related context')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Sheet onOpenChange={(open) => { if (open && !context) void load() }}>
      <SheetTrigger asChild>
        <button
          type="button"
          aria-label={`Show related context for this ${entity.replace('_', ' ')}`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          <Layers className="h-3.5 w-3.5" />
          {label}
        </button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{context?.title ?? 'Related'}</SheetTitle>
          <SheetDescription>
            {context ? `Last ${context.window_days} days, with links to where you can act.` : 'Runs, spend, budgets and policies for this item.'}
          </SheetDescription>
        </SheetHeader>
        <div className="mt-4 space-y-2">
          {loading && (
            <p className="flex items-center gap-2 text-sm text-slate-500"><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Loading…</p>
          )}
          {error && (
            <div role="alert" className="flex items-center justify-between rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
              <span>{error}</span>
              <button type="button" onClick={() => void load()} className="font-medium underline">Retry</button>
            </div>
          )}
          {context?.items.map((item) => {
            const body = (
              <div className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700">
                <span className="text-sm text-slate-600 dark:text-slate-300">{item.label}</span>
                <span className="font-mono text-sm font-semibold text-slate-900 dark:text-slate-100">{item.value}</span>
              </div>
            )
            return item.href ? (
              <Link key={item.key} href={item.href} className="block hover:opacity-80">{body}</Link>
            ) : (
              <div key={item.key}>{body}</div>
            )
          })}
        </div>
      </SheetContent>
    </Sheet>
  )
}
