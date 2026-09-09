'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { ScrollText, RefreshCw, ChevronLeft, ChevronRight, Download, X, Layers, Search, Filter } from 'lucide-react'
import { listAuditEvents, exportAuditEvents, getAuditEvent, getEvidenceAuditCrossPosture, getGovernanceInternalPosture, getAuditLogRuntimePosture } from '@/lib/api'
import type { AuditEvent, EvidenceAuditCrossPosture, GovernanceInternalPosture, AuditLogRuntimePosture } from '@/types/api'
import { toast } from 'sonner'

const PAGE_SIZE = 50

const inputCls =
  'w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-2.5 py-1.5 text-xs placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500'

const ACTION_COLORS: Record<string, string> = {
  'api_key.created': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  'api_key.revoked': 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  'budget.created': 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  'budget.deleted': 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
  'prompt.promoted': 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
  'approval.approved': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  'approval.denied': 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  'approval.cancelled': 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
}

export default function AuditPage() {
  const { data: session } = useSession()
  const apiKey = (session as { apiKey?: string })?.apiKey ?? ''

  const [events, setEvents] = useState<AuditEvent[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [actionFilter, setActionFilter] = useState('')
  const [targetTypeFilter, setTargetTypeFilter] = useState('')
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [crossPosture, setCrossPosture] = useState<EvidenceAuditCrossPosture | null>(null)
  const [govInternal, setGovInternal] = useState<GovernanceInternalPosture | null>(null)
  const [runtimePosture, setRuntimePosture] = useState<AuditLogRuntimePosture | null>(null)

  const fetchEvents = useCallback(async () => {
    if (!apiKey) return
    setLoading(true)
    try {
      const res = await listAuditEvents(apiKey, {
        action: actionFilter || undefined,
        target_type: targetTypeFilter || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      setEvents(res.items)
      setTotal(res.total)
    } catch {
      toast.error('Failed to load audit events')
    } finally {
      setLoading(false)
    }
  }, [apiKey, actionFilter, targetTypeFilter, offset])

  useEffect(() => { fetchEvents() }, [fetchEvents])

  useEffect(() => {
    if (!apiKey) return
    getEvidenceAuditCrossPosture(apiKey).then(setCrossPosture).catch(() => {})
    getGovernanceInternalPosture(apiKey).then(setGovInternal).catch(() => {})
    getAuditLogRuntimePosture(apiKey).then(setRuntimePosture).catch(() => {})
  }, [apiKey])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  function handleFilterChange() {
    setOffset(0)
    fetchEvents()
  }

  async function openEventDetail(eventId: string) {
    if (!apiKey) return
    setDetailLoading(true)
    try {
      const event = await getAuditEvent(apiKey, eventId)
      setSelectedEvent(event)
    } catch {
      toast.error('Failed to load audit event detail')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-4">
      {/* Hero header */}
      <div className="rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 ring-1 ring-violet-200 dark:bg-violet-500/20 dark:ring-violet-400/30">
              <ScrollText className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-950 dark:text-white">Audit Log</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Immutable record of all sensitive mutations in this workspace</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={async () => {
                if (!apiKey) return
                try {
                  const csv = await exportAuditEvents(apiKey, 'csv', actionFilter || undefined, targetTypeFilter || undefined)
                  const blob = new Blob([csv], { type: 'text/csv' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `audit-events-${new Date().toISOString().slice(0, 10)}.csv`
                  a.click()
                  URL.revokeObjectURL(url)
                  toast.success('Audit log exported')
                } catch { toast.error('Export failed') }
              }}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <Download className="h-3.5 w-3.5" /> Export CSV
            </button>
            <button
              onClick={fetchEvents}
              disabled={loading}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>
        </div>

        {/* KPI strip */}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {crossPosture && (
            <>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{crossPosture.observe_context.audit_events_30d}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Audit Events 30d</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{crossPosture.finops_context.active_budgets}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Active Budgets</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{crossPosture.org_context.workspace_users}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Workspace Users</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{crossPosture.gateway_context.total_routes}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Gateway Routes</p>
              </div>
            </>
          )}
          {runtimePosture && (
            <>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{runtimePosture.evidence_scope.audit_events_30d}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Evidence Events</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{runtimePosture.observe_lineage.runs_30d}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Runs 30d</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{runtimePosture.gateway_lineage.cache_configs}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Cache Configs</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-lg font-bold text-slate-900 dark:text-white">{runtimePosture.finops_lineage.ledger_snapshots_30d}</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400">Ledger Snapshots</p>
              </div>
            </>
          )}
        </div>

        {/* Governance chips */}
        {govInternal && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {[
              { label: `${govInternal.tool_registry_context.total_tools} Tools`, sub: `${govInternal.tool_registry_context.enforced_tools} enforced` },
              { label: `${govInternal.tool_policies_context.active_policies} Policies`, sub: 'active' },
              { label: `${govInternal.security_context.security_events_30d} Security`, sub: '30d' },
              { label: `${govInternal.tags_context.active_tags} Tags`, sub: 'active' },
            ].map((c) => (
              <span key={c.label} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                <span className="font-semibold text-slate-900 dark:text-white">{c.label}</span> {c.sub}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <Filter className="h-3.5 w-3.5 text-slate-400" />
        <input
          type="text"
          placeholder="Filter by action..."
          value={actionFilter}
          onChange={e => setActionFilter(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleFilterChange()}
          className={`w-48 ${inputCls}`}
        />
        <input
          type="text"
          placeholder="Filter by target type..."
          value={targetTypeFilter}
          onChange={e => setTargetTypeFilter(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleFilterChange()}
          className={`w-44 ${inputCls}`}
        />
        <button onClick={handleFilterChange} className="rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 px-3 py-1.5 text-xs font-semibold text-white hover:from-violet-500 hover:to-purple-500">Apply</button>
        {(actionFilter || targetTypeFilter) && (
          <button onClick={() => { setActionFilter(''); setTargetTypeFilter(''); setOffset(0) }} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">Clear</button>
        )}
        <span className="ml-auto text-xs text-slate-500 dark:text-slate-400">{total} event{total !== 1 ? 's' : ''}</span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40">
                <th className="px-3 py-2 text-left font-medium text-slate-500 whitespace-nowrap">Time</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">Action</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">Target</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">Actor</th>
                <th className="px-3 py-2 text-left font-medium text-slate-500">After</th>
              </tr>
            </thead>
            <tbody>
              {loading && events.length === 0 ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <td key={j} className="px-3 py-2">
                        <div className="h-3 rounded bg-slate-100 dark:bg-slate-700 animate-pulse" style={{ width: `${60 + (j * 15) % 40}%` }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-10 text-center text-xs text-slate-400">No audit events found</td>
                </tr>
              ) : events.map(ev => (
                <tr key={ev.id} onClick={() => openEventDetail(ev.id)} className="cursor-pointer border-b border-slate-100 dark:border-slate-800 hover:bg-violet-50/30 dark:hover:bg-violet-950/10">
                  <td className="px-3 py-2 text-slate-500 dark:text-slate-400 whitespace-nowrap font-mono text-[10px]">
                    {new Date(ev.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${ACTION_COLORS[ev.action] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'}`}>
                      {ev.action}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-[11px] text-slate-600 dark:text-slate-400">
                    {ev.target_type && <span className="font-medium text-slate-700 dark:text-slate-300">{ev.target_type}</span>}
                    {ev.target_id && <span className="ml-1 font-mono text-slate-500">{ev.target_id.length > 16 ? ev.target_id.slice(0, 8) + '...' : ev.target_id}</span>}
                    {!ev.target_type && !ev.target_id && <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-3 py-2 text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                    {ev.actor_api_key_prefix
                      ? <span title="API key prefix">{ev.actor_api_key_prefix}...</span>
                      : ev.actor_user_id
                        ? <span title="User ID">{ev.actor_user_id.slice(0, 8)}...</span>
                        : <span className="text-slate-400">system</span>
                    }
                  </td>
                  <td className="px-3 py-2 max-w-xs truncate font-mono text-[10px] text-slate-500 dark:text-slate-400">
                    {ev.after ? JSON.stringify(ev.after) : <span className="text-slate-400">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-slate-200 dark:border-slate-700 px-3 py-2">
            <span className="text-[11px] text-slate-500">Page {currentPage} of {totalPages}</span>
            <div className="flex gap-1.5">
              <button onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0} className="flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-[11px] disabled:opacity-40 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                <ChevronLeft className="h-3 w-3" /> Prev
              </button>
              <button onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total} className="flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-[11px] disabled:opacity-40 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                Next <ChevronRight className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail slide-over */}
      {(selectedEvent || detailLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/40">
          <div className="h-full w-full max-w-xl overflow-y-auto bg-white p-5 shadow-2xl dark:bg-slate-950">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">Audit Event Detail</h2>
                <p className="mt-0.5 text-[11px] text-slate-500">Full before/after payload for governance evidence.</p>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            {detailLoading || !selectedEvent ? (
              <div className="text-xs text-slate-500">Loading event detail...</div>
            ) : (
              <div className="space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-lg border border-slate-200 p-2.5 dark:border-slate-700">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Action</p>
                    <p className="mt-1 font-medium text-slate-900 dark:text-white">{selectedEvent.action}</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-2.5 dark:border-slate-700">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Created</p>
                    <p className="mt-1 font-medium text-slate-900 dark:text-white">{new Date(selectedEvent.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-lg border border-slate-200 p-2.5 dark:border-slate-700">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target</p>
                    <p className="mt-1 text-slate-900 dark:text-white">{selectedEvent.target_type ?? '-'} {selectedEvent.target_id ?? ''}</p>
                  </div>
                  <div className="rounded-lg border border-slate-200 p-2.5 dark:border-slate-700">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Actor</p>
                    <p className="mt-1 text-slate-900 dark:text-white">{selectedEvent.actor_api_key_prefix ?? selectedEvent.actor_user_id ?? 'system'}</p>
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 p-2.5 dark:border-slate-700">
                  <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">Before</p>
                  <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-slate-50 p-2.5 text-[10px] text-slate-700 dark:bg-slate-900 dark:text-slate-300">{JSON.stringify(selectedEvent.before, null, 2)}</pre>
                </div>
                <div className="rounded-lg border border-slate-200 p-2.5 dark:border-slate-700">
                  <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">After</p>
                  <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-slate-50 p-2.5 text-[10px] text-slate-700 dark:bg-slate-900 dark:text-slate-300">{JSON.stringify(selectedEvent.after, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quick nav footer */}
      <div className="flex flex-wrap gap-1.5 pt-2">
        {[
          { href: '/approvals', label: 'Approvals' },
          { href: '/security', label: 'Security' },
          { href: '/data-capture', label: 'Data Capture' },
          { href: '/tool-registry', label: 'Tool Governance' },
          { href: '/governance-pack', label: 'Audit Pack' },
          { href: '/alert-rules', label: 'Alert Rules' },
          { href: '/tags', label: 'Tags' },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-medium text-violet-700 ring-1 ring-violet-200 hover:bg-violet-100 dark:bg-violet-950/30 dark:text-violet-400 dark:ring-violet-800 dark:hover:bg-violet-950/50">
            {l.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
