import type { RunDetailResponse } from '@/types/api'
import RunStatusBadge from './RunStatusBadge'
import { formatCost, formatTokens, formatDuration } from '@/lib/utils'

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )
}

export default function RunSummaryBar({ run }: { run: RunDetailResponse }) {
  const totalTokens =
    (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0)

  return (
    <div className="flex flex-wrap items-center gap-6 rounded-lg border border-gray-200 bg-white px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-gray-400">{run.id.slice(0, 8)}…</span>
        <RunStatusBadge status={run.status} />
      </div>
      <Stat label="Cost" value={formatCost(run.total_cost_usd)} />
      <Stat label="Tokens" value={formatTokens(totalTokens)} />
      <Stat label="Duration" value={formatDuration(run.duration_ms)} />
      {run.end_user_id && <Stat label="User" value={run.end_user_id} />}
      {run.feature_tag && <Stat label="Feature" value={run.feature_tag} />}
    </div>
  )
}
