'use client'

/**
 * API key scopes — mirrors apps/api/runledger_api/core/scopes.py.
 * No scopes selected = full access to the workspace.
 */
export const API_KEY_SCOPES: { value: string; label: string; description: string }[] = [
  { value: 'read', label: 'Read', description: 'Runs, analytics, budgets, prompts, policy checks' },
  { value: 'write', label: 'Write', description: 'Create and change workspace content (includes read)' },
  { value: 'ingest', label: 'Ingest', description: 'SDK / OTLP telemetry, outcomes and scores' },
  { value: 'gateway', label: 'Gateway', description: 'Call models through the RunLedger gateway' },
  { value: 'mcp', label: 'MCP', description: 'Connect to the RunLedger MCP servers' },
]

export const SCOPE_PRESETS: { label: string; scopes: string[] }[] = [
  { label: 'Full access', scopes: [] },
  { label: 'SDK telemetry', scopes: ['read', 'ingest'] },
  { label: 'Gateway only', scopes: ['gateway'] },
  { label: 'MCP client', scopes: ['read', 'ingest', 'mcp'] },
  { label: 'Read only', scopes: ['read'] },
]

const ORDER = API_KEY_SCOPES.map((s) => s.value)

export function normalizeScopes(scopes: string[]): string[] {
  return ORDER.filter((s) => scopes.includes(s))
}

export function ScopeBadges({ scopes }: { scopes: string[] | null | undefined }) {
  if (!scopes || scopes.length === 0) {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800 dark:bg-amber-950/40 dark:text-amber-300" title="No scopes: this key can do anything its workspace allows">
        Full access
      </span>
    )
  }
  return (
    <span className="flex flex-wrap gap-1">
      {normalizeScopes(scopes).map((s) => (
        <span key={s} className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">
          {s}
        </span>
      ))}
    </span>
  )
}

export default function ScopePicker({
  value,
  onChange,
  compact = false,
}: {
  value: string[]
  onChange: (scopes: string[]) => void
  compact?: boolean
}) {
  const selected = new Set(value)
  const toggle = (scope: string) => {
    const next = new Set(selected)
    if (next.has(scope)) next.delete(scope)
    else next.add(scope)
    onChange(normalizeScopes(Array.from(next)))
  }
  const activePreset = SCOPE_PRESETS.find(
    (p) => normalizeScopes(p.scopes).join(',') === normalizeScopes(value).join(','),
  )

  return (
    <fieldset className="space-y-2">
      <legend className="text-xs font-semibold text-slate-600 dark:text-slate-300">
        Scopes{' '}
        <span className="font-normal text-slate-400">— what this key may do. None selected = full access.</span>
      </legend>
      {!compact && (
        <div className="flex flex-wrap gap-1.5">
          {SCOPE_PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => onChange(normalizeScopes(p.scopes))}
              className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
                activePreset?.label === p.label
                  ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      )}
      <div className={compact ? 'flex flex-col gap-1' : 'grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3'}>
        {API_KEY_SCOPES.map((s) => (
          <label key={s.value} className="flex cursor-pointer items-start gap-2 text-xs text-slate-700 dark:text-slate-200">
            <input
              type="checkbox"
              checked={selected.has(s.value)}
              onChange={() => toggle(s.value)}
              className="mt-0.5 h-3.5 w-3.5 rounded border-slate-300 text-indigo-600"
              aria-label={`Scope ${s.label}`}
            />
            <span>
              <span className="font-semibold">{s.label}</span>
              {!compact && <span className="block text-[11px] text-slate-500 dark:text-slate-400">{s.description}</span>}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
