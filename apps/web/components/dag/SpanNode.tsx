import { memo } from 'react'
import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { GraphNodeData } from '@/types/api'
import { formatCost, formatTokens } from '@/lib/utils'

const TYPE_COLORS: Record<string, string> = {
  llm: 'border-blue-300 bg-blue-50',
  tool: 'border-amber-300 bg-amber-50',
  chain: 'border-slate-300 bg-slate-50',
  agent: 'border-violet-300 bg-violet-50',
  retrieval: 'border-teal-300 bg-teal-50',
  run: 'border-gray-300 bg-gray-100',
}

const TYPE_BADGE: Record<string, string> = {
  llm: 'bg-blue-100 text-blue-700',
  tool: 'bg-amber-100 text-amber-700',
  chain: 'bg-slate-100 text-slate-700',
  agent: 'bg-violet-100 text-violet-700',
  retrieval: 'bg-teal-100 text-teal-700',
  run: 'bg-gray-100 text-gray-600',
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
        isError ? 'border-red-400 bg-red-50 ring-1 ring-red-300' : borderCls,
        selected ? 'ring-2 ring-offset-1 ring-blue-400' : '',
      ].join(' ')}
    >
      <Handle type="target" position={Position.Top} className="!border-gray-300 !bg-white" />

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

      <p className="mt-1.5 text-xs font-medium leading-tight text-gray-800 line-clamp-2">
        {d.label}
      </p>

      {(d.cost_usd != null || tokens != null) && (
        <div className="mt-1.5 flex gap-2 text-[10px] text-gray-500">
          {d.cost_usd != null && <span>{formatCost(d.cost_usd)}</span>}
          {tokens != null && <span>{formatTokens(tokens)} tok</span>}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!border-gray-300 !bg-white" />
    </div>
  )
})
