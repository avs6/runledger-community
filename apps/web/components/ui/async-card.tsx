'use client'

import type { ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { EmptyState } from './empty-state'

/** Inline error for one section, with a retry, instead of a silent empty state. */
export function SectionError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300">
      <span className="flex items-center gap-2"><AlertTriangle className="h-3.5 w-3.5 shrink-0" />{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="shrink-0 rounded-md border border-rose-300 px-2 py-0.5 font-medium hover:bg-rose-100 dark:border-rose-800 dark:hover:bg-rose-900/40">
          Retry
        </button>
      )}
    </div>
  )
}

/**
 * A card whose content loads on its own: shows a skeleton while loading, a SectionError
 * with retry on failure, an EmptyState when there's nothing, and the children otherwise.
 */
export function AsyncCard({
  title,
  description,
  loading,
  error,
  onRetry,
  empty,
  emptyTitle = 'Nothing here yet',
  emptyDescription,
  actions,
  children,
}: {
  title: string
  description?: string
  loading?: boolean
  error?: string | null
  onRetry?: () => void
  empty?: boolean
  emptyTitle?: string
  emptyDescription?: string
  actions?: ReactNode
  children?: ReactNode
}) {
  return (
    <section aria-busy={loading} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 dark:text-white">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{description}</p>}
        </div>
        {actions}
      </div>
      {loading ? (
        <p className="flex items-center gap-2 text-xs text-slate-400"><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Loading…</p>
      ) : error ? (
        <SectionError message={error} onRetry={onRetry} />
      ) : empty ? (
        <EmptyState title={emptyTitle} description={emptyDescription} compact />
      ) : (
        children
      )}
    </section>
  )
}
