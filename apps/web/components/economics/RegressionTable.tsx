import type { RegressionItem } from '@/types/api'

interface Props {
  items: RegressionItem[]
}

export default function RegressionTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">No cost regressions detected.</p>
    )
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
          <th className="pb-1 font-medium">Feature tag</th>
          <th className="pb-1 text-right font-medium">Current avg cost</th>
          <th className="pb-1 text-right font-medium">Prior avg cost</th>
          <th className="pb-1 text-right font-medium">Change %</th>
          <th className="pb-1 text-right font-medium">Runs</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item, i) => {
          const pct = parseFloat(item.change_pct)
          const isRegression = pct > 20
          return (
            <tr key={i} className="border-b border-gray-100 last:border-0 dark:border-gray-700">
              <td className="py-2 font-mono text-xs dark:text-gray-300">{item.feature_tag ?? '—'}</td>
              <td className="py-2 text-right tabular-nums dark:text-gray-300">
                ${parseFloat(item.current_avg_cost).toFixed(6)}
              </td>
              <td className="py-2 text-right tabular-nums dark:text-gray-300">
                ${parseFloat(item.prior_avg_cost).toFixed(6)}
              </td>
              <td
                className={`py-2 text-right tabular-nums font-bold ${
                  isRegression
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-green-600 dark:text-green-400'
                }`}
              >
                {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
              </td>
              <td className="py-2 text-right tabular-nums dark:text-gray-300">{item.run_count}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
