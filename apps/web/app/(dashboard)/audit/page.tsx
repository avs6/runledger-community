'use client'

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { Download, Layers, Link2, ScrollText, ShieldAlert, ShieldCheck } from 'lucide-react'
import { DataTable, type DataTableColumn, type DataTableQuery } from '@/components/ui/data-table'
import { PageHeader } from '@/components/ui/page-header'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { TIME_RANGES, TimeRangePicker, rangeToWindow, type TimeRange } from '@/components/ui/time-range-picker'
import {
  exportAuditLog,
  getAccessGroups,
  listAuditActors,
  listAuditPage,
  verifyAuditChain,
  type AuditActor,
  type AuditChainVerification,
  type AuditFilters,
  type AuditRow,
} from '@/lib/api'
import type { AccessGroupResponse } from '@/types/api'
import type { StaticRoute } from '@/lib/routes'

const GOVERNANCE_PACK: StaticRoute = '/governance-pack'
const FILTER_KEYS = ['action', 'actor', 'actor_type', 'api_key_prefix', 'access_group_id', 'target_type', 'target_id'] as const
type FilterKey = (typeof FILTER_KEYS)[number]
const ACTOR_TYPES = ['user', 'session', 'api_key', 'oidc', 'admin_secret', 'service', 'system'] as const

const inputCls =
  'rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100'

function actionTone(action: string): string {
  if (/\.(deleted|revoked|denied|rotated)$/.test(action)) return 'bg-status-warning/15 text-status-warning'
  if (/\.(created|approved|requested)$/.test(action)) return 'bg-status-success/15 text-status-success'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
}

function actorText(e: AuditRow): string {
  return e.actor_label ?? e.actor_api_key_prefix ?? (e.actor_user_id ? e.actor_user_id.slice(0, 8) : 'system')
}

function AuditLog() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()

  // Filters live in the URL (shareable links, e.g. from a secret's timeline).
  const filters = useMemo(() => {
    const f: AuditFilters = {}
    for (const k of FILTER_KEYS) {
      const v = params.get(k)
      if (v) f[k] = v
    }
    return f
  }, [params])
  const range = (params.get('range') as TimeRange | null) ?? null
  const effective = useMemo<AuditFilters>(
    () => (range && TIME_RANGES.includes(range) ? { ...filters, ...rangeToWindow(range) } : filters),
    // rangeToWindow uses "now"; recompute only when the inputs change.
    [filters, range],
  )

  const [draft, setDraft] = useState<Record<FilterKey, string>>(() => ({ action: '', actor: '', actor_type: '', api_key_prefix: '', access_group_id: '', target_type: '', target_id: '' }))
  useEffect(() => {
    setDraft({
      action: filters.action ?? '',
      actor: filters.actor ?? '',
      actor_type: filters.actor_type ?? '',
      api_key_prefix: filters.api_key_prefix ?? '',
      access_group_id: filters.access_group_id ?? '',
      target_type: filters.target_type ?? '',
      target_id: filters.target_id ?? '',
    })
  }, [filters])

  const [actors, setActors] = useState<AuditActor[]>([])
  const [groups, setGroups] = useState<AccessGroupResponse[]>([])
  const [chain, setChain] = useState<AuditChainVerification | null>(null)
  const [chainError, setChainError] = useState<string | null>(null)
  const [selected, setSelected] = useState<AuditRow | null>(null)

  useEffect(() => {
    if (!apiKey) return
    listAuditActors(apiKey).then(setActors).catch(() => setActors([]))
    getAccessGroups(apiKey).then((g) => setGroups(g.items)).catch(() => setGroups([]))
  }, [apiKey])

  const runVerify = useCallback(async () => {
    if (!apiKey) return
    setChainError(null)
    try {
      setChain(await verifyAuditChain(apiKey))
    } catch (err) {
      setChainError(err instanceof Error ? err.message : 'Verification failed')
    }
  }, [apiKey])
  useEffect(() => { void runVerify() }, [runVerify])

  const pushParams = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString())
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v)
      else next.delete(k)
    }
    next.delete('audit_page')
    router.replace(`${pathname}${next.toString() ? `?${next}` : ''}`, { scroll: false })
  }

  const applyFilters = (e?: React.FormEvent) => {
    e?.preventDefault()
    pushParams(Object.fromEntries(FILTER_KEYS.map((k) => [k, draft[k].trim() || null])))
  }
  const clearFilters = () => pushParams({ ...Object.fromEntries(FILTER_KEYS.map((k) => [k, null])), range: null })

  const fetchPage = useCallback(
    (q: DataTableQuery) => listAuditPage(apiKey, effective, q.limit, q.offset),
    [apiKey, effective],
  )

  async function download(format: 'csv' | 'json') {
    if (!apiKey) return
    try {
      const body = await exportAuditLog(apiKey, effective, format)
      const blob = new Blob([body], { type: format === 'csv' ? 'text/csv' : 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit-events-${new Date().toISOString().slice(0, 10)}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Export failed')
    }
  }

  const columns: DataTableColumn<AuditRow>[] = [
    {
      key: 'created_at',
      header: 'Time',
      render: (e) => <span className="whitespace-nowrap font-mono text-[11px] text-slate-500">{new Date(e.created_at).toLocaleString()}</span>,
    },
    {
      key: 'action',
      header: 'Action',
      render: (e) => <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${actionTone(e.action)}`}>{e.action}</span>,
    },
    {
      key: 'actor',
      header: 'Actor',
      value: (e) => actorText(e),
      render: (e) => (
        <button
          type="button"
          onClick={(ev) => { ev.stopPropagation(); pushParams({ actor: e.actor_label ?? e.actor_api_key_prefix ?? e.actor_user_id ?? null }) }}
          className="text-left text-xs hover:underline"
          aria-label={`Filter by actor ${actorText(e)}`}
        >
          <span className="text-slate-800 dark:text-slate-200">{actorText(e)}</span>
          <span className="ml-1 text-[10px] uppercase text-slate-400">{e.actor_type ?? ''}</span>
        </button>
      ),
    },
    {
      key: 'target',
      header: 'Target',
      value: (e) => `${e.target_type ?? ''} ${e.target_id ?? ''}`.trim(),
      render: (e) =>
        e.target_type || e.target_id ? (
          <span className="text-[11px]">
            <span className="font-medium text-slate-700 dark:text-slate-300">{e.target_type}</span>
            {e.target_id && <span className="ml-1 font-mono text-slate-500">{e.target_id.length > 16 ? `${e.target_id.slice(0, 8)}…` : e.target_id}</span>}
          </span>
        ) : (
          <span className="text-slate-400">—</span>
        ),
    },
    { key: 'seq', header: '#', defaultHidden: true },
    {
      key: 'hash',
      header: 'Hash',
      defaultHidden: true,
      render: (e) => <span className="font-mono text-[10px] text-slate-400">{e.hash ? e.hash.slice(0, 12) : '—'}</span>,
    },
    {
      key: 'after',
      header: 'Details',
      value: (e) => (e.after ? JSON.stringify(e.after) : ''),
      render: (e) => <span className="block max-w-xs truncate font-mono text-[10px] text-slate-500">{e.after ? JSON.stringify(e.after) : '—'}</span>,
    },
  ]

  const activeCount = FILTER_KEYS.filter((k) => filters[k]).length + (range ? 1 : 0)

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4">
      <PageHeader
        title="Audit Log"
        icon={ScrollText}
        description="Hash-chained record of every sensitive change in this workspace, with who made it."
        actions={
          <div className="flex items-center gap-2">
            <Link href={GOVERNANCE_PACK} className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
              <Layers className="h-3.5 w-3.5" aria-hidden="true" /> Audit pack
            </Link>
            <button type="button" onClick={() => void download('csv')} className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
              <Download className="h-3.5 w-3.5" aria-hidden="true" /> CSV
            </button>
            <button type="button" onClick={() => void download('json')} className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800">
              <Download className="h-3.5 w-3.5" aria-hidden="true" /> JSON
            </button>
          </div>
        }
      />

      <div
        role="status"
        className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border px-4 py-2.5 text-xs ${
          chainError || (chain && !chain.ok)
            ? 'border-status-error/40 bg-status-error/10 text-status-error'
            : 'border-status-success/40 bg-status-success/10 text-status-success'
        }`}
      >
        <span className="flex items-center gap-2">
          {chain && !chain.ok ? <ShieldAlert className="h-4 w-4" aria-hidden="true" /> : <ShieldCheck className="h-4 w-4" aria-hidden="true" />}
          {chainError
            ? `Chain check failed: ${chainError}`
            : !chain
              ? 'Verifying the hash chain…'
              : chain.ok
                ? `Hash chain intact: ${chain.checked} events verified${chain.unchained ? ` (${chain.unchained} legacy events outside the chain)` : ''}.`
                : `Hash chain broken at event #${chain.first_bad_seq}: ${chain.reason}.`}
        </span>
        <span className="flex items-center gap-2">
          {chain?.head_hash && <span className="font-mono text-[10px] opacity-80" title="Head hash">{chain.head_hash.slice(0, 16)}…</span>}
          <button type="button" onClick={() => void runVerify()} className="rounded-md border border-current px-2 py-0.5 font-medium">
            Re-verify
          </button>
        </span>
      </div>

      <form onSubmit={applyFilters} aria-label="Audit filters" className="grid gap-2 rounded-xl border border-slate-200 bg-white p-3 sm:grid-cols-2 lg:grid-cols-4 dark:border-slate-700 dark:bg-slate-900">
        <input aria-label="Action prefix" placeholder="Action (e.g. secret, budget.)" value={draft.action} onChange={(e) => setDraft({ ...draft, action: e.target.value })} className={inputCls} />
        <input aria-label="Actor" list="audit-actors" placeholder="Actor (email, key prefix or user id)" value={draft.actor} onChange={(e) => setDraft({ ...draft, actor: e.target.value })} className={inputCls} />
        <datalist id="audit-actors">
          {actors.map((a, i) => (
            <option key={`${a.actor_label}-${a.actor_api_key_prefix}-${i}`} value={a.actor_label ?? a.actor_api_key_prefix ?? a.actor_user_id ?? ''}>
              {`${a.actor_type ?? ''} · ${a.events} events`}
            </option>
          ))}
        </datalist>
        <select aria-label="Actor type" value={draft.actor_type} onChange={(e) => setDraft({ ...draft, actor_type: e.target.value })} className={inputCls}>
          <option value="">Any actor type</option>
          {ACTOR_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input aria-label="API key prefix" placeholder="API key prefix" value={draft.api_key_prefix} onChange={(e) => setDraft({ ...draft, api_key_prefix: e.target.value })} className={inputCls} />
        <select aria-label="Access group" value={draft.access_group_id} onChange={(e) => setDraft({ ...draft, access_group_id: e.target.value })} className={inputCls}>
          <option value="">Any access group</option>
          {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
        </select>
        <input aria-label="Target type" placeholder="Target type (e.g. secret, approval)" value={draft.target_type} onChange={(e) => setDraft({ ...draft, target_type: e.target.value })} className={inputCls} />
        <input aria-label="Target id" placeholder="Target id" value={draft.target_id} onChange={(e) => setDraft({ ...draft, target_id: e.target.value })} className={inputCls} />
        <div className="flex items-center gap-2">
          <button type="submit" className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700">Apply</button>
          {activeCount > 0 && (
            <button type="button" onClick={clearFilters} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
              Clear {activeCount}
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 sm:col-span-2 lg:col-span-4">
          <TimeRangePicker value={range ?? '90d'} onChange={(r) => pushParams({ range: r })} label="Audit time range" />
          {!range && <span className="text-[11px] text-slate-400">All time</span>}
        </div>
      </form>

      {apiKey && (
        <DataTable
          key={JSON.stringify(effective)}
          label="Audit events"
          urlPrefix="audit_"
          fetchPage={fetchPage}
          rowKey={(e) => e.id}
          columns={columns}
          pageSize={50}
          searchable={false}
          csvFileName="audit-events.csv"
          emptyTitle="No audit events match"
          emptyDescription="Change or clear the filters."
          onRowClick={setSelected}
        />
      )}

      <Sheet open={selected !== null} onOpenChange={(o) => { if (!o) setSelected(null) }}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{selected?.action}</SheetTitle>
            <SheetDescription>Full before/after payload and its place in the hash chain.</SheetDescription>
          </SheetHeader>
          {selected && (
            <div className="mt-4 space-y-4 text-xs">
              <dl className="grid grid-cols-3 gap-2">
                <dt className="text-slate-500">When</dt><dd className="col-span-2">{new Date(selected.created_at).toLocaleString()}</dd>
                <dt className="text-slate-500">Actor</dt><dd className="col-span-2">{actorText(selected)} <span className="text-slate-400">({selected.actor_type ?? 'unknown'})</span></dd>
                <dt className="text-slate-500">User id</dt><dd className="col-span-2 font-mono">{selected.actor_user_id ?? '—'}</dd>
                <dt className="text-slate-500">API key</dt><dd className="col-span-2 font-mono">{selected.actor_api_key_prefix ?? '—'}</dd>
                <dt className="text-slate-500">Target</dt><dd className="col-span-2 font-mono">{selected.target_type ?? '—'} {selected.target_id ?? ''}</dd>
                <dt className="text-slate-500">Chain #</dt><dd className="col-span-2">{selected.seq ?? '—'}</dd>
                <dt className="text-slate-500">Hash</dt><dd className="col-span-2 break-all font-mono text-[10px]">{selected.hash ?? '—'}</dd>
                <dt className="text-slate-500">Previous</dt><dd className="col-span-2 break-all font-mono text-[10px]">{selected.prev_hash ?? '—'}</dd>
              </dl>
              {selected.target_type && selected.target_id && (
                <button
                  type="button"
                  onClick={() => { pushParams({ target_type: selected.target_type, target_id: selected.target_id }); setSelected(null) }}
                  className="flex items-center gap-1 font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  <Link2 className="h-3 w-3" aria-hidden="true" /> All events for this target
                </button>
              )}
              {(['before', 'after'] as const).map((k) => (
                <div key={k}>
                  <p className="mb-1 font-semibold capitalize text-slate-700 dark:text-slate-300">{k}</p>
                  <pre className="max-h-64 overflow-auto rounded-lg bg-slate-50 p-3 font-mono text-[11px] dark:bg-slate-900">
                    {selected[k] ? JSON.stringify(selected[k], null, 2) : '—'}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}

export default function AuditPage() {
  return (
    <Suspense fallback={<div className="p-4 text-xs text-slate-400">Loading…</div>}>
      <AuditLog />
    </Suspense>
  )
}
