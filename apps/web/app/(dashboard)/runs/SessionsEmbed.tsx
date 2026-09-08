import Link from 'next/link'
import { MessageSquare } from 'lucide-react'
import { formatCost, formatDuration } from '@/lib/utils'
import type { SessionItem } from '@/types/api'

export default function SessionsEmbed({
  items,
  total,
  page,
  pageCount,
}: {
  items: SessionItem[]
  total: number
  page: number
  pageCount: number
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {total.toLocaleString()} sessions total
        </p>
        <Link
          href="/sessions"
          className="text-xs font-semibold text-violet-600 hover:underline dark:text-violet-400"
        >
          Open full Sessions page
        </Link>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <table className="min-w-full text-sm">
          <thead className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/60">
            <tr>
              {['Session ID', 'User', 'Turns', 'Cost', 'Duration', 'Started'].map((header) => (
                <th
                  key={header}
                  className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <MessageSquare className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600" />
                  <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">No sessions found.</p>
                </td>
              </tr>
            ) : (
              items.map((item) => {
                const durationMs =
                  item.started_at && item.ended_at
                    ? new Date(item.ended_at).getTime() - new Date(item.started_at).getTime()
                    : null
                return (
                  <tr key={item.session_id} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-700 dark:text-slate-300">
                      <Link href={`/sessions/${encodeURIComponent(item.session_id)}`} className="hover:text-violet-700 hover:underline dark:hover:text-violet-400">
                        {item.session_id.length > 16 ? `${item.session_id.slice(0, 16)}…` : item.session_id}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300">
                      {item.end_user_id ? (
                        <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-mono text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                          {item.end_user_id}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">{item.run_count}</td>
                    <td className="px-4 py-2.5 font-mono text-slate-700 dark:text-slate-200">{formatCost(item.total_cost_usd)}</td>
                    <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">{durationMs != null ? formatDuration(durationMs) : '—'}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-600 dark:text-slate-300">
                      {new Date(item.started_at).toLocaleString()}
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
