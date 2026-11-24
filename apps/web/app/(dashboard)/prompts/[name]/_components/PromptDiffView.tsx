'use client'

/** Server-computed line diff between two prompt versions (ENH prompt diff viewer). */

import { useEffect, useState } from 'react'
import { diffPromptVersions } from '@/lib/api'
import type { PromptDiff } from '@/types/api'
import { SectionError } from '@/components/ui/async-card'

const LINE_CLS: Record<string, string> = {
  add: 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300',
  remove: 'bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-300',
  hunk: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
  context: 'text-slate-700 dark:text-slate-300',
}
const PREFIX: Record<string, string> = { add: '+', remove: '-', hunk: '', context: ' ' }

export function PromptDiffView({
  apiKey,
  name,
  from,
  to,
}: {
  apiKey: string
  name: string
  from: number
  to: number
}) {
  const [diff, setDiff] = useState<PromptDiff | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let live = true
    setError(null)
    diffPromptVersions(apiKey, name, from, to)
      .then((d) => live && setDiff(d))
      .catch((e) => live && setError(e instanceof Error ? e.message : 'Diff failed'))
    return () => {
      live = false
    }
  }, [apiKey, name, from, to, nonce])

  if (error) return <SectionError message={error} onRetry={() => setNonce((n) => n + 1)} />
  if (!diff) return <p className="text-sm text-slate-500">Loading diff…</p>
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">
        v{diff.from_version} ({diff.from_environment}) → v{diff.to_version} ({diff.to_environment}):{' '}
        <span className="text-emerald-600">+{diff.added}</span>{' '}
        <span className="text-rose-600">-{diff.removed}</span>
        {diff.model_hint_changed ? ' · model hint changed' : ''}
        {diff.variables_changed ? ' · variables changed' : ''}
      </p>
      {diff.lines.length === 0 ? (
        <p className="text-sm text-slate-500">No content changes.</p>
      ) : (
        <pre className="max-h-96 overflow-auto rounded border border-slate-200 font-mono text-xs dark:border-slate-700" aria-label="Prompt diff">
          {diff.lines.map((l, i) => (
            <div key={i} className={`whitespace-pre-wrap px-2 ${LINE_CLS[l.kind]}`}>
              {PREFIX[l.kind]}
              {l.text}
            </div>
          ))}
        </pre>
      )}
    </div>
  )
}
