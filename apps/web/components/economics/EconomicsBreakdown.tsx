'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { ValueType } from 'recharts/types/component/DefaultTooltipContent'
import type { RunEconomics } from '@/types/api'

const SPAN_COLOURS: Record<string, string> = {
  llm: '#6366f1',       // indigo
  tool: '#f59e0b',      // amber
  retrieval: '#14b8a6', // teal
  chain: '#64748b',     // slate
  agent: '#475569',     // slate-darker
}

function spanColour(spanType: string): string {
  return SPAN_COLOURS[spanType] ?? '#94a3b8'
}

interface Props {
  data: RunEconomics
}

function valueToNumber(value: ValueType | undefined): number | null {
  if (typeof value === 'number') return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  if (Array.isArray(value) && value.length > 0) {
    return valueToNumber(value[0])
  }
  return null
}

export default function EconomicsBreakdown({ data }: Props) {
  const chartData = data.cost_by_span_type.map((s) => ({
    span_type: s.span_type,
    cost: parseFloat(s.cost_usd),
  }))

  const retryCost = parseFloat(data.retry_cost)

  return (
    <div className="space-y-4">
      {/* Summary callouts */}
      <div className="flex flex-wrap gap-4">
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
          <p className="text-xs text-gray-500 dark:text-gray-400">Total Cost</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            ${parseFloat(data.total_cost_usd).toFixed(6)}
          </p>
        </div>
        {retryCost > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-800 dark:bg-amber-950">
            <p className="text-xs text-amber-600 dark:text-amber-400">Retry Cost (child LLM spans)</p>
            <p className="text-lg font-semibold text-amber-800 dark:text-amber-300">
              ${retryCost.toFixed(6)}
            </p>
          </div>
        )}
      </div>

      {/* Span-type bar chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#374151" />
            <XAxis dataKey="span_type" tick={{ fontSize: 12, fill: '#9ca3af' }} />
            <YAxis
              tickFormatter={(v: number) => `$${v.toFixed(4)}`}
              tick={{ fontSize: 11, fill: '#9ca3af' }}
              width={72}
            />
            <Tooltip
              formatter={(value) => {
                const numeric = valueToNumber(value) ?? 0
                return [`$${numeric.toFixed(6)}`, 'Cost']
              }}
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '6px', color: '#f3f4f6' }}
            />
            <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.span_type} fill={spanColour(entry.span_type)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">No span cost data for this run.</p>
      )}

      {/* Model cost table */}
      {data.cost_by_model.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500 dark:border-gray-700 dark:text-gray-400">
              <th className="pb-1 font-medium">Model</th>
              <th className="pb-1 font-medium">Provider</th>
              <th className="pb-1 text-right font-medium">Calls</th>
              <th className="pb-1 text-right font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.cost_by_model.map((m) => (
              <tr key={`${m.provider}/${m.model}`} className="border-b border-gray-100 last:border-0 dark:border-gray-700">
                <td className="py-1.5 font-mono text-xs dark:text-gray-300">{m.model}</td>
                <td className="py-1.5 text-gray-500 dark:text-gray-400">{m.provider}</td>
                <td className="py-1.5 text-right tabular-nums dark:text-gray-300">{m.call_count}</td>
                <td className="py-1.5 text-right tabular-nums font-medium dark:text-gray-200">
                  ${parseFloat(m.cost_usd).toFixed(6)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
