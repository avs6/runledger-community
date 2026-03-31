'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { ScrollText, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { listAuditEvents } from '@/lib/api'
import type { AuditEvent } from '@/types/api'
import { toast } from 'sonner'

const PAGE_SIZE = 50

const ACTION_COLORS: Record<string, string> = {
  'api_key.created': 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  'api_key.revoked': 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  'budget.created': 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  'budget.deleted': 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  'prompt.promoted': 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
  'approval.approved': 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  'approval.denied': 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  'approval.cancelled': 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

function ActionBadge({ action }: { action: string }) {
  const cls = ACTION_COLORS[action] ?? 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {action}
    </span>
  )
}

function JsonPopover({ data }: { data: Record<string, unknown> | null }) {
  if (!data) return <span className="text-slate-400 text-xs">—</span>
  return (
    <span className="font-mono text-xs text-slate-600 dark:text-slate-400 break-all">
      {JSON.stringify(data)}
    </span>
  )
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

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  function handleFilterChange() {
    setOffset(0)
    fetchEvents()
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ScrollText className="h-6 w-6 text-violet-600 dark:text-violet-400" />
          <div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Audit Log</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Immutable record of all sensitive mutations in this workspace
            </p>
          </div>
        </div>
        <button
          onClick={fetchEvents}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Filter by action (e.g. budget)"
          value={actionFilter}
          onChange={e => setActionFilter(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleFilterChange()}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white placeholder:text-slate-400 w-56"
        />
        <input
          type="text"
          placeholder="Filter by target type"
          value={targetTypeFilter}
          onChange={e => setTargetTypeFilter(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleFilterChange()}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white placeholder:text-slate-400 w-48"
        />
        <button
          onClick={handleFilterChange}
          className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700"
        >
          Apply
        </button>
        {(actionFilter || targetTypeFilter) && (
          <button
            onClick={() => { setActionFilter(''); setTargetTypeFilter(''); setOffset(0) }}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
          >
            Clear
          </button>
        )}
        <span className="ml-auto self-center text-sm text-slate-500 dark:text-slate-400">
          {total} event{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40">
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400 whitespace-nowrap">Time</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400">Action</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400">Target</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400">Actor</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400">After</th>
              </tr>
            </thead>
            <tbody>
              {loading && events.length === 0 ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 rounded bg-slate-200 dark:bg-slate-700 animate-pulse" style={{ width: `${60 + (j * 15) % 40}%` }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-sm text-slate-400 dark:text-slate-500">
                    No audit events found
                  </td>
                </tr>
              ) : events.map(ev => (
                <tr key={ev.id} className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400 whitespace-nowrap font-mono text-xs">
                    {new Date(ev.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <ActionBadge action={ev.action} />
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400 text-xs">
                    {ev.target_type && (
                      <span className="font-medium text-slate-700 dark:text-slate-300">{ev.target_type}</span>
                    )}
                    {ev.target_id && (
                      <span className="ml-1 font-mono text-slate-500 dark:text-slate-500">
                        {ev.target_id.length > 16 ? ev.target_id.slice(0, 8) + '…' : ev.target_id}
                      </span>
                    )}
                    {!ev.target_type && !ev.target_id && <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 font-mono">
                    {ev.actor_api_key_prefix
                      ? <span title="API key prefix">{ev.actor_api_key_prefix}…</span>
                      : ev.actor_user_id
                        ? <span title="User ID">{ev.actor_user_id.slice(0, 8)}…</span>
                        : <span className="text-slate-400">system</span>
                    }
                  </td>
                  <td className="px-4 py-3 max-w-xs truncate">
                    <JsonPopover data={ev.after} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-slate-200 dark:border-slate-700 px-4 py-3">
            <span className="text-sm text-slate-500 dark:text-slate-400">
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm disabled:opacity-40 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                <ChevronLeft className="h-3.5 w-3.5" /> Prev
              </button>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm disabled:opacity-40 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                Next <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
