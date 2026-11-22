'use client'

import { TrendingDown } from 'lucide-react'
import { num } from '@/lib/utils'
import type { RoutingRecommendationResponse } from '@/types/api'

export function RecommendationPanel({ rec }: { rec: RoutingRecommendationResponse }) {
  const hasData = rec.total_outcomes_sampled > 0 && rec.models.some((m) => m.cost_per_success !== null)

  return (
    <div className="py-3 space-y-2">
      {/* Summary message */}
      <div className={`flex items-start gap-2 rounded-lg px-3 py-2 text-sm ${hasData ? 'bg-violet-100 dark:bg-violet-900/20 text-violet-800 dark:text-violet-200' : 'bg-slate-100 dark:bg-slate-700/40 text-slate-500 dark:text-slate-400'}`}>
        <TrendingDown className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{rec.message}</span>
      </div>

      {/* Per-model table */}
      {hasData && (
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="text-left text-slate-400 dark:text-slate-500 border-b border-slate-200 dark:border-slate-700">
              <th className="py-1.5 pr-4 font-medium">Model</th>
              <th className="py-1.5 pr-4 font-medium text-right">Outcomes</th>
              <th className="py-1.5 pr-4 font-medium text-right">Success rate</th>
              <th className="py-1.5 pr-4 font-medium text-right">Cost / success</th>
              <th className="py-1.5 font-medium text-right">vs current</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {rec.models.map((m, i) => {
              const isBest = m.model === rec.best_model
              const imp = m.improvement_vs_current
              return (
                <tr key={m.model} className={isBest ? 'font-semibold' : ''}>
                  <td className="py-1.5 pr-4 dark:text-slate-200 font-mono">
                    {m.model}
                    {isBest && i === 0 && (
                      <span className="ml-1.5 rounded-full bg-violet-100 dark:bg-violet-900/30 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:text-violet-300">best</span>
                    )}
                  </td>
                  <td className="py-1.5 pr-4 text-right text-slate-500 dark:text-slate-400">{m.sample_count}</td>
                  <td className="py-1.5 pr-4 text-right text-slate-600 dark:text-slate-300">
                    {m.success_rate > 0 ? `${(num(m.success_rate) * 100).toFixed(1)}%` : '—'}
                  </td>
                  <td className="py-1.5 pr-4 text-right dark:text-slate-200">
                    {m.cost_per_success != null ? `$${num(m.cost_per_success).toFixed(4)}` : '—'}
                  </td>
                  <td className="py-1.5 text-right">
                    {imp != null ? (
                      <span className={`${imp > 0 ? 'text-emerald-600 dark:text-emerald-400' : imp < 0 ? 'text-red-500 dark:text-red-400' : 'text-slate-400'}`}>
                        {imp > 0 ? `↓${(imp * 100).toFixed(1)}%` : imp < 0 ? `↑${(Math.abs(imp) * 100).toFixed(1)}%` : '—'}
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      <p className="text-[11px] text-slate-400 dark:text-slate-500">
        Last {rec.window_days} days · {rec.total_outcomes_sampled} outcomes sampled
        {rec.workflow_type ? ` · type: ${rec.workflow_type}` : ''}
      </p>
    </div>
  )
}

// ── Optimization flywheel ─────────────────────────────────────────────────────
