'use client'

import type { RoutingPolicyAnalysis } from '@/types/api'

export function PolicyAnalysisPanel({ analysis }: { analysis: RoutingPolicyAnalysis }) {
  return (
    <div className="space-y-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/80 p-4 dark:bg-slate-900/20">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">Traffic Analysis</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
          confidence {analysis.confidence}
        </span>
        {analysis.winner_label && (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
            winner {analysis.winner_label}
          </span>
        )}
        {analysis.significance_p_value && (
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
            p={parseFloat(analysis.significance_p_value).toFixed(4)}
          </span>
        )}
        {analysis.auto_promoted && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
            auto-promoted
          </span>
        )}
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-300">{analysis.summary}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-400 dark:border-slate-700 dark:text-slate-500">
              <th className="py-1.5 pr-4 font-medium">Variant</th>
              <th className="py-1.5 pr-4 font-medium text-right">Alloc</th>
              <th className="py-1.5 pr-4 font-medium text-right">Requests</th>
              <th className="py-1.5 pr-4 font-medium text-right">Success</th>
              <th className="py-1.5 pr-4 font-medium text-right">Errors</th>
              <th className="py-1.5 font-medium text-right">Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {analysis.variants.map((variant) => (
              <tr key={variant.route_id}>
                <td className="py-1.5 pr-4 font-mono text-slate-700 dark:text-slate-200">{variant.label}</td>
                <td className="py-1.5 pr-4 text-right text-slate-500 dark:text-slate-400">
                  {(parseFloat(variant.allocation_pct) * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 pr-4 text-right text-slate-500 dark:text-slate-400">{variant.total_requests}</td>
                <td className="py-1.5 pr-4 text-right text-slate-600 dark:text-slate-300">
                  {(parseFloat(variant.success_rate) * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 pr-4 text-right text-slate-600 dark:text-slate-300">
                  {(parseFloat(variant.error_rate) * 100).toFixed(1)}%
                </td>
                <td className="py-1.5 text-right text-slate-600 dark:text-slate-300">
                  {variant.avg_latency_ms ? `${parseFloat(variant.avg_latency_ms).toFixed(0)}ms` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
