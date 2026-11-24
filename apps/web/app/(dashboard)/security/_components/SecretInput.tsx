'use client'

import { useState } from 'react'
import { KeyRound, Undo2 } from 'lucide-react'
import { SECRET_MASK } from '@/lib/api'

/**
 * Write-only secret field (review S-03). A stored secret is shown masked with a
 * "Replace" button; the value only goes back to the API when the user typed a new
 * one. `onChange(undefined)` means "keep the stored value".
 */
export function SecretInput({
  id,
  label,
  stored,
  value,
  onChange,
  placeholder,
  required,
}: {
  id: string
  label: string
  /** The API's masked value ('••••••••') when a secret is stored, else null. */
  stored: string | null | undefined
  value: string | undefined
  onChange: (value: string | undefined) => void
  placeholder?: string
  required?: boolean
}) {
  const hasStored = Boolean(stored)
  const [replacing, setReplacing] = useState(!hasStored)
  const inputCls =
    'w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100'

  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-xs text-slate-500 dark:text-slate-400">{label}</label>
      {hasStored && !replacing ? (
        <div className="flex items-center gap-2">
          <span id={id} className="flex flex-1 items-center gap-2 rounded border border-slate-200 bg-slate-50 px-3 py-1.5 font-mono text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400">
            <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />
            {SECRET_MASK}
            <span className="sr-only">(stored; not shown)</span>
          </span>
          <button
            type="button"
            onClick={() => setReplacing(true)}
            aria-label={`Replace ${label}`}
            className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Replace
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <input
            id={id}
            type="password"
            autoComplete="new-password"
            value={value ?? ''}
            onChange={(e) => onChange(e.target.value || undefined)}
            placeholder={placeholder ?? (hasStored ? 'New value' : '')}
            required={required && !hasStored}
            className={inputCls}
          />
          {hasStored && (
            <button
              type="button"
              onClick={() => { setReplacing(false); onChange(undefined) }}
              aria-label={`Keep the stored ${label}`}
              className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <Undo2 className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          )}
        </div>
      )}
    </div>
  )
}
