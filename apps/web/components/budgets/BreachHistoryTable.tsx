import type { Breach } from '@/types/api'

interface Props {
  items: Breach[]
}

const ACTION_COLOURS: Record<string, string> = {
  block: 'bg-red-100 text-red-700',
  notify: 'bg-yellow-100 text-yellow-700',
  downgrade: 'bg-blue-100 text-blue-700',
}

export default function BreachHistoryTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500">
        No breaches recorded yet.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Occurred at</th>
            <th className="px-4 py-3 text-right font-medium text-gray-600">Spend at breach</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Action taken</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Notified at</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {items.map((b) => (
            <tr key={b.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 tabular-nums text-gray-700">
                {new Date(b.occurred_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-right tabular-nums">
                {b.spend_at_breach_usd != null
                  ? `$${parseFloat(b.spend_at_breach_usd).toFixed(6)}`
                  : '—'}
              </td>
              <td className="px-4 py-3">
                {b.action_taken ? (
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLOURS[b.action_taken] ?? 'bg-gray-100 text-gray-600'}`}
                  >
                    {b.action_taken}
                  </span>
                ) : (
                  <span className="text-gray-400">—</span>
                )}
              </td>
              <td className="px-4 py-3 tabular-nums text-gray-600">
                {b.notified_at ? new Date(b.notified_at).toLocaleString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
