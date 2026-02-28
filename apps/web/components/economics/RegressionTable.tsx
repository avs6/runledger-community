import type { RegressionItem } from '@/types/api'

interface Props {
  items: RegressionItem[]
}

export default function RegressionTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500">No cost regressions detected.</p>
    )
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-xs text-gray-500">
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
            <tr key={i} className="border-b last:border-0">
              <td className="py-2 font-mono text-xs">{item.feature_tag ?? '—'}</td>
              <td className="py-2 text-right tabular-nums">
                ${parseFloat(item.current_avg_cost).toFixed(6)}
              </td>
              <td className="py-2 text-right tabular-nums">
                ${parseFloat(item.prior_avg_cost).toFixed(6)}
              </td>
              <td
                className={`py-2 text-right tabular-nums font-bold ${
                  isRegression ? 'text-red-600' : 'text-green-600'
                }`}
              >
                {pct > 0 ? '+' : ''}{pct.toFixed(2)}%
              </td>
              <td className="py-2 text-right tabular-nums">{item.run_count}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
