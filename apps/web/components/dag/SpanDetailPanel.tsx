'use client'

import type { GraphNode } from '@/types/api'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { formatCost, formatTokens, formatDuration } from '@/lib/utils'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 text-sm">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-right font-medium text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  )
}

export default function SpanDetailPanel({
  node,
  onClose,
}: {
  node: GraphNode | null
  onClose: () => void
}) {
  return (
    <Sheet open={node !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-96 overflow-y-auto">
        {node && (
          <>
            <SheetHeader>
              <SheetTitle className="text-base">{node.label}</SheetTitle>
              <Badge variant="outline" className="w-fit text-xs">
                {node.data.span_type ?? 'span'}
              </Badge>
            </SheetHeader>
            <Separator className="my-4" />
            <div className="space-y-0.5">
              <Row label="Status" value={node.data.status ?? '—'} />
              <Row label="Cost" value={formatCost(node.data.cost_usd)} />
              {node.data.input_tokens != null && (
                <Row
                  label="Input tokens"
                  value={formatTokens(node.data.input_tokens)}
                />
              )}
              {node.data.output_tokens != null && (
                <Row
                  label="Output tokens"
                  value={formatTokens(node.data.output_tokens)}
                />
              )}
              {node.data.model && (
                <Row
                  label="Model"
                  value={
                    <span className="font-mono text-xs">{node.data.model}</span>
                  }
                />
              )}
              {node.data.duration_ms != null && (
                <Row
                  label="Duration"
                  value={formatDuration(node.data.duration_ms)}
                />
              )}
            </div>
            {node.data.metadata &&
              Object.keys(node.data.metadata).length > 0 && (
                <>
                  <Separator className="my-4" />
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    Payload / Metadata
                  </p>
                  <pre className="overflow-auto rounded bg-gray-50 p-3 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                    {JSON.stringify(node.data.metadata, null, 2)}
                  </pre>
                </>
              )}
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
