'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  SlidersHorizontal, X, Hash, Tag, User, DollarSign,
  Clock, CheckCircle2, AlertCircle, XCircle, Search,
} from 'lucide-react'

// ── Constants ────────────────────────────────────────────────────────────────

const KNOWN_MODELS = [
  { label: 'GPT-4o', value: 'gpt-4o', provider: 'OpenAI' },
  { label: 'GPT-4o Mini', value: 'gpt-4o-mini', provider: 'OpenAI' },
  { label: 'GPT-4 Turbo', value: 'gpt-4-turbo', provider: 'OpenAI' },
  { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo', provider: 'OpenAI' },
  { label: 'o1', value: 'o1', provider: 'OpenAI' },
  { label: 'o3-mini', value: 'o3-mini', provider: 'OpenAI' },
  { label: 'Claude Opus 4.6', value: 'claude-opus-4-6', provider: 'Anthropic' },
  { label: 'Claude Sonnet 4.6', value: 'claude-sonnet-4-6', provider: 'Anthropic' },
  { label: 'Claude Haiku 4.5', value: 'claude-haiku-4-5', provider: 'Anthropic' },
  { label: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro', provider: 'Google' },
  { label: 'Gemini 1.5 Flash', value: 'gemini-1.5-flash', provider: 'Google' },
  { label: 'Llama 3.2 3B', value: 'llama3.2:3b', provider: 'Ollama' },
  { label: 'Llama 3.1', value: 'llama3.1', provider: 'Ollama' },
  { label: 'Mistral', value: 'mistral', provider: 'Ollama' },
  { label: 'Phi-4', value: 'phi4', provider: 'Ollama' },
  { label: 'Qwen 2.5', value: 'qwen2.5', provider: 'Ollama' },
]

const STATUSES = [
  { value: 'running', label: 'Running', icon: Clock, color: 'text-blue-500' },
  { value: 'succeeded', label: 'Succeeded', icon: CheckCircle2, color: 'text-emerald-500' },
  { value: 'failed', label: 'Failed', icon: AlertCircle, color: 'text-red-500' },
  { value: 'cancelled', label: 'Cancelled', icon: XCircle, color: 'text-slate-400' },
]

const CHIP_COLORS: Record<string, string> = {
  search:       'bg-violet-100 text-violet-800 border-violet-200 dark:bg-violet-900/40 dark:text-violet-300 dark:border-violet-800',
  status:       'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800',
  feature_tag:  'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/40 dark:text-orange-300 dark:border-orange-800',
  end_user_id:  'bg-pink-100 text-pink-800 border-pink-200 dark:bg-pink-900/40 dark:text-pink-300 dark:border-pink-800',
  model:        'bg-teal-100 text-teal-800 border-teal-200 dark:bg-teal-900/40 dark:text-teal-300 dark:border-teal-800',
  min_cost:     'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800',
  max_cost:     'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800',
}

const CHIP_LABELS: Record<string, string> = {
  search: 'Run ID', status: 'Status', feature_tag: 'Tag',
  end_user_id: 'User', model: 'Model', min_cost: 'Min $', max_cost: 'Max $',
}

const TIME_PRESETS = [
  { label: '5m', value: '5m', minutes: 5 },
  { label: '15m', value: '15m', minutes: 15 },
  { label: '30m', value: '30m', minutes: 30 },
  { label: '1h', value: '1h', minutes: 60 },
  { label: '3h', value: '3h', minutes: 180 },
  { label: '6h', value: '6h', minutes: 360 },
  { label: '12h', value: '12h', minutes: 720 },
  { label: '24h', value: '24h', minutes: 1440 },
  { label: '7d', value: '7d', minutes: 60 * 24 * 7 },
  { label: '30d', value: '30d', minutes: 60 * 24 * 30 },
]

function minutesAgoIso(minutes: number) {
  return new Date(Date.now() - minutes * 60_000).toISOString()
}

function isoToLocal(iso: string) {
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

// ── Searchable model combobox ─────────────────────────────────────────────────

function ModelPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(value)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { setQuery(value) }, [value])

  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const providers = ['OpenAI', 'Anthropic', 'Google', 'Ollama']
  const filtered = query
    ? KNOWN_MODELS.filter(m =>
        m.value.toLowerCase().includes(query.toLowerCase()) ||
        m.label.toLowerCase().includes(query.toLowerCase()) ||
        m.provider.toLowerCase().includes(query.toLowerCase()),
      )
    : KNOWN_MODELS

  return (
    <div ref={ref} className="relative w-full">
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <input
          className="h-8 w-full rounded-md border border-input bg-background pl-8 pr-8 text-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:ring-offset-1"
          placeholder="Search model…"
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={e => {
            if (e.key === 'Enter') { onChange(query); setOpen(false) }
            if (e.key === 'Escape') setOpen(false)
          }}
        />
        {query && (
          <button
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onMouseDown={e => { e.preventDefault(); setQuery(''); onChange(''); }}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      {open && (
        <div className="absolute z-50 mt-1 w-64 rounded-md border border-border bg-popover shadow-lg overflow-hidden">
          {filtered.length === 0 ? (
            <div className="px-3 py-2.5 text-xs text-muted-foreground">
              No matches — press Enter to use &quot;{query}&quot;
            </div>
          ) : (
            <div className="max-h-56 overflow-y-auto">
              {providers.map(provider => {
                const models = filtered.filter(m => m.provider === provider)
                if (models.length === 0) return null
                return (
                  <div key={provider}>
                    <div className="bg-muted/50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {provider}
                    </div>
                    {models.map(m => (
                      <button
                        key={m.value}
                        className="flex w-full items-center justify-between px-3 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
                        onMouseDown={e => { e.preventDefault(); setQuery(m.value); onChange(m.value); setOpen(false) }}
                      >
                        <span>{m.label}</span>
                        <span className="ml-2 font-mono text-[10px] text-muted-foreground">{m.value}</span>
                      </button>
                    ))}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function RunFilters() {
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()

  const [panelOpen, setPanelOpen] = useState(false)

  // Draft state (uncommitted until Apply is clicked)
  const [draftStatus, setDraftStatus] = useState(params.get('status') ?? '')
  const [draftSearch, setDraftSearch] = useState(params.get('search') ?? '')
  const [draftTag, setDraftTag] = useState(params.get('feature_tag') ?? '')
  const [draftUser, setDraftUser] = useState(params.get('end_user_id') ?? '')
  const [draftModel, setDraftModel] = useState(params.get('model') ?? '')
  const [draftMinCost, setDraftMinCost] = useState(params.get('min_cost') ?? '')
  const [draftMaxCost, setDraftMaxCost] = useState(params.get('max_cost') ?? '')

  const preset = params.get('preset') ?? '7d'
  const fromParam = params.get('from') ?? ''
  const toParam = params.get('to') ?? ''
  const isCustom = preset === 'custom'

  // Sync drafts when URL changes (e.g. time preset changes)
  useEffect(() => {
    setDraftStatus(params.get('status') ?? '')
    setDraftSearch(params.get('search') ?? '')
    setDraftTag(params.get('feature_tag') ?? '')
    setDraftUser(params.get('end_user_id') ?? '')
    setDraftModel(params.get('model') ?? '')
    setDraftMinCost(params.get('min_cost') ?? '')
    setDraftMaxCost(params.get('max_cost') ?? '')
  }, [params])

  const pushParams = useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(params.toString())
      for (const [k, v] of Object.entries(updates)) {
        if (v) next.set(k, v)
        else next.delete(k)
      }
      next.delete('cursor')
      router.push(`${pathname}?${next.toString()}`)
    },
    [params, pathname, router],
  )

  const applyFilters = useCallback(() => {
    pushParams({
      search: draftSearch || null,
      status: draftStatus || null,
      feature_tag: draftTag || null,
      end_user_id: draftUser || null,
      model: draftModel || null,
      min_cost: draftMinCost || null,
      max_cost: draftMaxCost || null,
    })
    setPanelOpen(false)
  }, [draftSearch, draftStatus, draftTag, draftUser, draftModel, draftMinCost, draftMaxCost, pushParams])

  const resetAll = useCallback(() => {
    setDraftStatus(''); setDraftSearch(''); setDraftTag('')
    setDraftUser(''); setDraftModel(''); setDraftMinCost(''); setDraftMaxCost('')
    pushParams({ search: null, status: null, feature_tag: null, end_user_id: null, model: null, min_cost: null, max_cost: null })
  }, [pushParams])

  const removeChip = useCallback((key: string) => {
    pushParams({ [key]: null })
  }, [pushParams])

  const applyPreset = useCallback((value: string, minutes: number) => {
    const next = new URLSearchParams(params.toString())
    next.set('preset', value)
    next.set('from', minutesAgoIso(minutes))
    next.delete('to'); next.delete('cursor')
    router.push(`${pathname}?${next.toString()}`)
  }, [params, pathname, router])

  const switchToCustom = useCallback(() => {
    const next = new URLSearchParams(params.toString())
    next.set('preset', 'custom')
    if (!next.has('from')) next.set('from', minutesAgoIso(60 * 24 * 7))
    if (!next.has('to')) next.set('to', new Date().toISOString())
    next.delete('cursor')
    router.push(`${pathname}?${next.toString()}`)
  }, [params, pathname, router])

  const updateParam = useCallback((key: string, value: string | null) => {
    const next = new URLSearchParams(params.toString())
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('cursor')
    router.push(`${pathname}?${next.toString()}`)
  }, [params, pathname, router])

  // Derive active chips from URL (not drafts)
  const chips = [
    params.get('search')      && { key: 'search',      display: params.get('search')! },
    params.get('status')      && { key: 'status',      display: params.get('status')! },
    params.get('feature_tag') && { key: 'feature_tag', display: params.get('feature_tag')! },
    params.get('end_user_id') && { key: 'end_user_id', display: params.get('end_user_id')! },
    params.get('model')       && { key: 'model',       display: params.get('model')! },
    params.get('min_cost')    && { key: 'min_cost',    display: `≥ $${params.get('min_cost')}` },
    params.get('max_cost')    && { key: 'max_cost',    display: `≤ $${params.get('max_cost')}` },
  ].filter(Boolean) as { key: string; display: string }[]

  const activeCount = chips.length

  return (
    <div className="space-y-2">
      {/* ── Row 1: filter button + active chips ── */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant={panelOpen || activeCount > 0 ? 'default' : 'outline'}
          size="sm"
          className="h-8 gap-1.5 text-sm"
          onClick={() => setPanelOpen(o => !o)}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          Filters
          {activeCount > 0 && (
            <span className="ml-0.5 inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-white/25 px-1 text-[10px] font-bold">
              {activeCount}
            </span>
          )}
        </Button>

        {chips.map(({ key, display }) => (
          <span
            key={key}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${CHIP_COLORS[key] ?? 'bg-muted text-foreground border-border'}`}
          >
            <span className="opacity-60 text-[10px] uppercase tracking-wide font-semibold">
              {CHIP_LABELS[key] ?? key}
            </span>
            <span>{display}</span>
            <button
              onClick={() => removeChip(key)}
              className="ml-0.5 rounded-full opacity-60 hover:opacity-100 transition-opacity"
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}

        {activeCount > 1 && (
          <button
            onClick={resetAll}
            className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      {/* ── Filter panel (expands below) ── */}
      {panelOpen && (
        <div className="rounded-xl border border-border bg-card shadow-sm">
          <div className="space-y-5 p-4">

            {/* Status */}
            <div className="flex items-center gap-4">
              <span className="w-20 shrink-0 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Status
              </span>
              <div className="flex flex-wrap gap-1.5">
                <button
                  onClick={() => setDraftStatus('')}
                  className={`h-7 rounded-full border px-3 text-xs font-medium transition-all ${
                    !draftStatus
                      ? 'border-primary bg-primary text-primary-foreground shadow-sm'
                      : 'border-border text-muted-foreground hover:border-primary/40 hover:text-foreground'
                  }`}
                >
                  All
                </button>
                {STATUSES.map(s => (
                  <button
                    key={s.value}
                    onClick={() => setDraftStatus(draftStatus === s.value ? '' : s.value)}
                    className={`flex h-7 items-center gap-1.5 rounded-full border px-3 text-xs font-medium transition-all ${
                      draftStatus === s.value
                        ? 'border-primary bg-primary text-primary-foreground shadow-sm'
                        : 'border-border text-muted-foreground hover:border-primary/40 hover:text-foreground'
                    }`}
                  >
                    <s.icon className={`h-3 w-3 ${draftStatus === s.value ? 'text-primary-foreground' : s.color}`} />
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Model */}
            <div className="flex items-center gap-4">
              <span className="w-20 shrink-0 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Model
              </span>
              <div className="w-72">
                <ModelPicker value={draftModel} onChange={setDraftModel} />
              </div>
            </div>

            {/* Identity */}
            <div className="flex items-start gap-4">
              <span className="w-20 shrink-0 pt-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Identity
              </span>
              <div className="grid flex-1 grid-cols-1 gap-2 sm:grid-cols-3">
                <div className="relative">
                  <Hash className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Run ID…"
                    className="h-8 pl-8 text-sm font-mono"
                    value={draftSearch}
                    onChange={e => setDraftSearch(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && applyFilters()}
                  />
                </div>
                <div className="relative">
                  <Tag className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Feature tag…"
                    className="h-8 pl-8 text-sm"
                    value={draftTag}
                    onChange={e => setDraftTag(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && applyFilters()}
                  />
                </div>
                <div className="relative">
                  <User className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="End user ID…"
                    className="h-8 pl-8 text-sm"
                    value={draftUser}
                    onChange={e => setDraftUser(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && applyFilters()}
                  />
                </div>
              </div>
            </div>

            {/* Cost */}
            <div className="flex items-center gap-4">
              <span className="w-20 shrink-0 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                Cost ($)
              </span>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <DollarSign className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    type="number"
                    placeholder="min"
                    className="h-8 w-28 pl-8 text-sm"
                    value={draftMinCost}
                    onChange={e => setDraftMinCost(e.target.value)}
                    step="0.000001"
                    min="0"
                  />
                </div>
                <span className="text-sm text-muted-foreground">–</span>
                <div className="relative">
                  <DollarSign className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    type="number"
                    placeholder="max"
                    className="h-8 w-28 pl-8 text-sm"
                    value={draftMaxCost}
                    onChange={e => setDraftMaxCost(e.target.value)}
                    step="0.000001"
                    min="0"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Panel footer */}
          <div className="flex items-center justify-between border-t border-border bg-muted/30 px-4 py-2.5">
            <button
              onClick={resetAll}
              className="text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              Reset all filters
            </button>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setPanelOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" className="h-7 text-xs" onClick={applyFilters}>
                Apply filters
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Time presets ── */}
      <div className="flex flex-wrap items-center gap-1">
        {TIME_PRESETS.map(({ label, value, minutes }) => (
          <Button
            key={value}
            variant={preset === value ? 'default' : 'outline'}
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={() => applyPreset(value, minutes)}
          >
            {label}
          </Button>
        ))}
        <Button
          variant={isCustom ? 'default' : 'outline'}
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={switchToCustom}
        >
          Custom
        </Button>
        {isCustom && (
          <div className="ml-1 flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">from</span>
            <input
              type="datetime-local"
              step="1"
              className="h-7 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              defaultValue={fromParam ? isoToLocal(fromParam) : ''}
              onBlur={e => { if (e.target.value) updateParam('from', new Date(e.target.value).toISOString()) }}
            />
            <span className="text-xs text-muted-foreground">to</span>
            <input
              type="datetime-local"
              step="1"
              className="h-7 rounded-md border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              defaultValue={toParam ? isoToLocal(toParam) : ''}
              onBlur={e => { if (e.target.value) updateParam('to', new Date(e.target.value).toISOString()) }}
            />
          </div>
        )}
      </div>
    </div>
  )
}
