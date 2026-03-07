'use client'

import { useSession } from 'next-auth/react'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { MessageSquare } from 'lucide-react'
import { toast } from 'sonner'
import { listSessions } from '@/lib/api'
import type { SessionItem } from '@/types/api'
import { formatCost, formatDuration } from '@/lib/utils'

function SkeletonRows({ cols }: { cols: number }) {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <tr key={i} className="animate-pulse border-b border-gray-100 dark:border-gray-800">
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 rounded bg-gray-200 dark:bg-gray-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

export default function SessionsPage() {
  const { data: session } = useSession()
  const router = useRouter()
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [endUserFilter, setEndUserFilter] = useState('')

  async function load(userId?: string) {
    if (!session?.apiKey) return
    setLoading(true)
    try {
      const data = await listSessions(session.apiKey, {
        end_user_id: userId || undefined,
      })
      setSessions(data.items)
      setTotal(data.total)
    } catch {
      toast.error('Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.apiKey])

  function handleFilterSubmit(e: React.FormEvent) {
    e.preventDefault()
    load(endUserFilter)
  }

  function handleClearFilter() {
    setEndUserFilter('')
    load('')
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Sessions</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Multi-turn conversations grouped by session_id.
        </p>
      </div>

      {/* Filter bar */}
      <form onSubmit={handleFilterSubmit} className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Filter by end_user_id…"
          value={endUserFilter}
          onChange={(e) => setEndUserFilter(e.target.value)}
          className="w-64 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          type="submit"
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Filter
        </button>
        {endUserFilter && (
          <button
            type="button"
            onClick={handleClearFilter}
            className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Clear
          </button>
        )}
        <span className="ml-auto text-sm text-gray-500 dark:text-gray-400">
          {total} session{total !== 1 ? 's' : ''}
        </span>
      </form>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              {['Session ID', 'User', 'Turns', 'Total Cost', 'Duration', 'Avg Score', 'Started'].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800 bg-white dark:bg-gray-900">
            {loading ? (
              <SkeletonRows cols={7} />
            ) : sessions.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-16 text-center">
                  <MessageSquare className="mx-auto h-10 w-10 text-gray-300 dark:text-gray-600" />
                  <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
                    No sessions yet. Tag runs with a <code className="font-mono">session_id</code> to group them here.
                  </p>
                </td>
              </tr>
            ) : (
              sessions.map((s) => {
                const durationMs =
                  s.started_at && s.ended_at
                    ? new Date(s.ended_at).getTime() - new Date(s.started_at).getTime()
                    : null

                return (
                  <tr
                    key={s.session_id}
                    onClick={() => router.push(`/sessions/${encodeURIComponent(s.session_id)}`)}
                    className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-700 dark:text-gray-300">
                      <span title={s.session_id}>
                        {s.session_id.length > 16 ? s.session_id.slice(0, 16) + '…' : s.session_id}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                      {s.end_user_id ?? <span className="text-gray-400 dark:text-gray-500">—</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">{s.run_count}</td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                      {formatCost(s.total_cost_usd)}
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                      {durationMs != null ? formatDuration(durationMs) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                      {s.avg_score != null ? (
                        <span className="inline-flex items-center rounded-full bg-indigo-50 dark:bg-indigo-950 px-2 py-0.5 text-xs font-medium text-indigo-700 dark:text-indigo-300">
                          {parseFloat(s.avg_score).toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-gray-400 dark:text-gray-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">
                      {new Date(s.started_at).toLocaleString()}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
