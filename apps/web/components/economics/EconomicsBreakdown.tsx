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
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
          <p className="text-xs text-gray-500">Total Cost</p>
          <p className="text-lg font-semibold text-gray-900">
            ${parseFloat(data.total_cost_usd).toFixed(6)}
          </p>
        </div>
        {retryCost > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-xs text-amber-600">Retry Cost (child LLM spans)</p>
            <p className="text-lg font-semibold text-amber-800">
              ${retryCost.toFixed(6)}
            </p>
          </div>
        )}
      </div>

      {/* Span-type bar chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="span_type" tick={{ fontSize: 12 }} />
            <YAxis
              tickFormatter={(v: number) => `$${v.toFixed(4)}`}
              tick={{ fontSize: 11 }}
              width={72}
            />
            <Tooltip formatter={(v: number | undefined) => [`$${(v ?? 0).toFixed(6)}`, 'Cost']} />
            <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
              {chartData.map((entry) => (
                <Cell key={entry.span_type} fill={spanColour(entry.span_type)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-sm text-gray-500">No span cost data for this run.</p>
      )}

      {/* Model cost table */}
      {data.cost_by_model.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-gray-500">
              <th className="pb-1 font-medium">Model</th>
              <th className="pb-1 font-medium">Provider</th>
              <th className="pb-1 text-right font-medium">Calls</th>
              <th className="pb-1 text-right font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.cost_by_model.map((m) => (
              <tr key={`${m.provider}/${m.model}`} className="border-b last:border-0">
                <td className="py-1.5 font-mono text-xs">{m.model}</td>
                <td className="py-1.5 text-gray-500">{m.provider}</td>
                <td className="py-1.5 text-right tabular-nums">{m.call_count}</td>
                <td className="py-1.5 text-right tabular-nums font-medium">
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
