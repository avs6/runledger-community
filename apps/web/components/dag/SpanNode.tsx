import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { GraphNodeData } from '@/types/api'
import { formatCost, formatTokens } from '@/lib/utils'

const TYPE_COLORS: Record<string, string> = {
  llm: 'border-blue-300 bg-blue-50 dark:border-blue-600 dark:bg-blue-950/60',
  tool: 'border-amber-300 bg-amber-50 dark:border-amber-600 dark:bg-amber-950/60',
  chain: 'border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-800',
  agent: 'border-violet-300 bg-violet-50 dark:border-violet-600 dark:bg-violet-950/60',
  retrieval: 'border-violet-300 bg-violet-50 dark:border-violet-600 dark:bg-violet-950/60',
  run: 'border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-800',
}

const TYPE_BADGE: Record<string, string> = {
  llm: 'bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300',
  tool: 'bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300',
  chain: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
  agent: 'bg-violet-100 text-violet-700 dark:bg-violet-900/60 dark:text-violet-300',
  retrieval: 'bg-violet-100 text-violet-700 dark:bg-violet-900/60 dark:text-violet-300',
  run: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}

export const SpanNode = memo(function SpanNode({
  data,
  selected,
}: NodeProps) {
  const d = data as unknown as GraphNodeData & { label: string }
  const spanType = d.span_type ?? 'chain'
  const borderCls = TYPE_COLORS[spanType] ?? TYPE_COLORS.chain
  const badgeCls = TYPE_BADGE[spanType] ?? TYPE_BADGE.chain
  const isError = d.status === 'error' || d.status === 'failed'
  const tokens =
    d.input_tokens != null && d.output_tokens != null
      ? (d.input_tokens ?? 0) + (d.output_tokens ?? 0)
      : null

  return (
    <div
      className={[
        'min-w-[160px] rounded-lg border px-3 py-2 shadow-sm transition-shadow',
        isError ? 'border-red-400 bg-red-50 ring-1 ring-red-300 dark:border-red-600 dark:bg-red-950/60 dark:ring-red-700' : borderCls,
        selected ? 'ring-2 ring-offset-1 ring-blue-400' : '',
      ].join(' ')}
    >
      <Handle type="target" position={Position.Top} className="!border-gray-300 !bg-white dark:!border-gray-600 dark:!bg-slate-700" />

      <div className="flex items-center justify-between gap-2">
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${badgeCls}`}
        >
          {spanType}
        </span>
        {isError && (
          <span className="rounded px-1.5 py-0.5 text-[10px] font-medium bg-red-100 text-red-600">
            error
          </span>
        )}
      </div>

      <p className="mt-1.5 text-xs font-medium leading-tight text-gray-800 dark:text-gray-200 line-clamp-2">
        {d.label}
      </p>

      {(d.cost_usd != null || tokens != null) && (
        <div className="mt-1.5 flex gap-2 text-[10px] text-gray-500 dark:text-gray-400">
          {d.cost_usd != null && <span>{formatCost(d.cost_usd)}</span>}
          {tokens != null && <span>{formatTokens(tokens)} tok</span>}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!border-gray-300 !bg-white dark:!border-gray-600 dark:!bg-slate-700" />
    </div>
  )
})
