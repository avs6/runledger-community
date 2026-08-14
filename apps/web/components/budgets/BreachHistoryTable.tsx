import type { Breach } from '@/types/api'

interface Props {
  items: Breach[]
}

const ACTION_COLOURS: Record<string, string> = {
  block: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300',
  notify: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
  downgrade: 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
  throttle: 'bg-violet-100 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300',
  fallback: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
}

export default function BreachHistoryTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500 dark:border-slate-700 dark:text-slate-400">
        No breaches recorded yet.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-800">
      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-slate-800">
        <thead className="bg-gray-50 dark:bg-slate-900">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-slate-300">Occurred at</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-slate-300">Spend at breach</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-slate-300">Action taken</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-slate-300">Notified at</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white dark:divide-slate-800 dark:bg-slate-950">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-slate-900/70">
              <td className="px-4 py-3 tabular-nums text-gray-700 dark:text-slate-300">
                {new Date(item.occurred_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-slate-700 dark:text-slate-300">
                {item.spend_at_breach_usd != null
                  ? `$${parseFloat(item.spend_at_breach_usd).toFixed(6)}`
                  : '-'}
              </td>
              <td className="px-4 py-3">
                {item.action_taken ? (
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLOURS[item.action_taken] ?? 'bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-300'}`}
                  >
                    {item.action_taken}
                  </span>
                ) : (
                  <span className="text-gray-400 dark:text-slate-500">-</span>
                )}
              </td>
              <td className="px-4 py-3 tabular-nums text-gray-600 dark:text-slate-400">
                {item.notified_at ? new Date(item.notified_at).toLocaleString() : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
