import { getServerSession } from 'next-auth'
import Link from 'next/link'
import { MessageSquare, RefreshCw, Search, SlidersHorizontal } from 'lucide-react'
import { authOptions } from '@/lib/auth'
import { listSessions } from '@/lib/api'
import SessionsExportButton from '@/components/sessions/SessionsExportButton'
import { formatCost, formatDuration } from '@/lib/utils'

type TimePreset = 'all' | '1d' | '7d' | '30d'

function cutoff(preset: TimePreset): string | undefined {
  if (preset === 'all') return undefined
  const d = new Date()
  if (preset === '1d') d.setDate(d.getDate() - 1)
  if (preset === '7d') d.setDate(d.getDate() - 7)
  if (preset === '30d') d.setDate(d.getDate() - 30)
  return d.toISOString()
}

function queryStringFrom(params: Record<string, string | undefined>) {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value) qs.set(key, value)
  }
  return qs.toString()
}

function withParams(
  current: Record<string, string | undefined>,
  updates: Record<string, string | undefined | null>,
) {
  const next = new URLSearchParams()
  for (const [key, value] of Object.entries(current)) {
    if (value) next.set(key, value)
  }
  for (const [key, value] of Object.entries(updates)) {
    if (value) next.set(key, value)
    else next.delete(key)
  }
  const query = next.toString()
  return `/sessions${query ? `?${query}` : ''}`
}

function ResultCount({ loaded, total }: { loaded: number; total: number }) {
  if (loaded === total) {
    return <span className="text-xs text-slate-400">{total} session{total !== 1 ? 's' : ''}</span>
  }
  return (
    <span className="text-xs font-medium text-violet-600 dark:text-violet-400">
      {loaded} of {total} sessions
    </span>
  )
}

export default async function SessionsPage({
  searchParams,
}: {
  searchParams?: {
    q?: string
    end_user_id?: string
    time?: string
    min_turns?: string
    min_cost?: string
    max_cost?: string
    page?: string
  }
}) {
  const session = await getServerSession(authOptions)
  if (!session) return null

  const timePreset: TimePreset =
    searchParams?.time === '1d' || searchParams?.time === '7d' || searchParams?.time === '30d'
      ? searchParams.time
      : 'all'
  const from = cutoff(timePreset)
  const page = Math.max(1, Number.parseInt(searchParams?.page ?? '1', 10) || 1)

  const activeParams: Record<string, string | undefined> = {
    q: searchParams?.q,
    end_user_id: searchParams?.end_user_id,
    time: timePreset !== 'all' ? timePreset : undefined,
    min_turns: searchParams?.min_turns,
    min_cost: searchParams?.min_cost,
    max_cost: searchParams?.max_cost,
    page: page > 1 ? String(page) : undefined,
  }

  const data = await listSessions(session.apiKey, {
    q: searchParams?.q,
    end_user_id: searchParams?.end_user_id,
    from,
    min_turns: searchParams?.min_turns ? Number.parseInt(searchParams.min_turns, 10) : undefined,
    min_cost: searchParams?.min_cost,
    max_cost: searchParams?.max_cost,
    page,
    page_size: 50,
  })

  const pageCount = Math.max(1, Math.ceil(data.total / data.page_size))
  const hasFilters = Boolean(
    searchParams?.q ||
    searchParams?.end_user_id ||
    (timePreset !== 'all') ||
    searchParams?.min_turns ||
    searchParams?.min_cost ||
    searchParams?.max_cost,
  )

  const exportQuery = queryStringFrom({
    q: searchParams?.q,
    end_user_id: searchParams?.end_user_id,
    from,
    min_turns: searchParams?.min_turns,
    min_cost: searchParams?.min_cost,
    max_cost: searchParams?.max_cost,
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Sessions</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Multi-turn conversations grouped by session ID with server-side filtering, paging, and export.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={withParams(activeParams, { page: null })}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Link>
          <SessionsExportButton queryString={exportQuery} />
        </div>
      </div>

      <form action="/sessions" className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/50">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
        </div>

        <div className="grid gap-3 lg:grid-cols-6">
          <div className="lg:col-span-2">
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Search</label>
            <div className="relative mt-1">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                name="q"
                defaultValue={searchParams?.q ?? ''}
                placeholder="Session ID or user..."
                className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-8 pr-3 text-sm text-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">End user</label>
            <input
              name="end_user_id"
              defaultValue={searchParams?.end_user_id ?? ''}
              placeholder="user ID"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Time</label>
            <select
              name="time"
              defaultValue={timePreset}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            >
              <option value="all">All time</option>
              <option value="1d">Today</option>
              <option value="7d">7 days</option>
              <option value="30d">30 days</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Min turns</label>
            <input
              type="number"
              min={1}
              name="min_turns"
              defaultValue={searchParams?.min_turns ?? ''}
              placeholder="3"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Min cost</label>
            <input
              type="number"
              step="0.0001"
              min={0}
              name="min_cost"
              defaultValue={searchParams?.min_cost ?? ''}
              placeholder="0.0100"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            />
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-6">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Max cost</label>
            <input
              type="number"
              step="0.0001"
              min={0}
              name="max_cost"
              defaultValue={searchParams?.max_cost ?? ''}
              placeholder="0.5000"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-violet-700"
          >
            Apply filters
          </button>
          {hasFilters && (
            <Link
              href="/sessions"
              className="text-sm font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
            >
              Reset all
            </Link>
          )}
          <ResultCount loaded={data.items.length} total={data.total} />
        </div>
      </form>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/60">
            <tr>
              {['Session ID', 'User', 'Turns', 'Total Cost', 'Duration', 'Avg Score', 'Started'].map((header) => (
                <th
                  key={header}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.items.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-16 text-center">
                  <MessageSquare className="mx-auto h-10 w-10 text-slate-300 dark:text-slate-600" />
                  <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
                    No sessions match the current filters.
                  </p>
                  {hasFilters && (
                    <Link href="/sessions" className="mt-2 inline-block text-xs text-violet-600 hover:underline">
                      Reset all filters
                    </Link>
                  )}
                </td>
              </tr>
            ) : (
              data.items.map((item) => {
                const durationMs =
                  item.started_at && item.ended_at
                    ? new Date(item.ended_at).getTime() - new Date(item.started_at).getTime()
                    : null

                return (
                  <tr key={item.session_id} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-mono text-xs text-slate-700 dark:text-slate-300">
                      <Link href={`/sessions/${encodeURIComponent(item.session_id)}`} className="hover:text-violet-700 hover:underline">
                        <span title={item.session_id}>
                          {item.session_id.length > 16 ? `${item.session_id.slice(0, 16)}…` : item.session_id}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                      {item.end_user_id ? (
                        <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-mono text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                          {item.end_user_id}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{item.run_count}</td>
                    <td className="px-4 py-3 font-mono text-slate-700 dark:text-slate-200">{formatCost(item.total_cost_usd)}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{durationMs != null ? formatDuration(durationMs) : '—'}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{item.avg_score ?? '—'}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                      {new Date(item.started_at).toLocaleString()}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
        <span>
          Page {data.page} of {pageCount} • {data.total.toLocaleString()} sessions
        </span>
        <div className="flex items-center gap-2">
          {data.page > 1 && (
            <Link
              href={withParams(activeParams, { page: String(data.page - 1) })}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200"
            >
              Previous
            </Link>
          )}
          {data.page < pageCount && (
            <Link
              href={withParams(activeParams, { page: String(data.page + 1) })}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200"
            >
              Next
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
