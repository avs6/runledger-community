import Link from 'next/link'
import type { RunListItem } from '@/types/api'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import RunStatusBadge from './RunStatusBadge'
import { formatCost, formatTokens, formatDuration, formatAge, truncateId } from '@/lib/utils'

export default function RunsTable({ items }: { items: RunListItem[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 py-16 text-center text-sm text-gray-400">
        No runs found.
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <Table>
        <TableHeader>
          <TableRow className="text-xs">
            <TableHead>Run ID</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>End User</TableHead>
            <TableHead>Feature</TableHead>
            <TableHead>Model</TableHead>
            <TableHead className="text-right">Cost</TableHead>
            <TableHead className="text-right">Tokens</TableHead>
            <TableHead className="text-right">Duration</TableHead>
            <TableHead className="text-right">Started</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((run) => (
            <TableRow key={run.id} className="text-sm">
              <TableCell className="font-mono">
                <Link
                  href={`/runs/${run.id}`}
                  className="text-blue-600 hover:underline"
                >
                  {truncateId(run.id)}
                </Link>
              </TableCell>
              <TableCell>
                <RunStatusBadge status={run.status} />
              </TableCell>
              <TableCell className="text-gray-500">
                {run.end_user_id ?? '—'}
              </TableCell>
              <TableCell className="text-gray-500">
                {run.feature_tag ?? '—'}
              </TableCell>
              <TableCell className="font-mono text-xs text-gray-500">
                {run.primary_model ?? '—'}
              </TableCell>
              <TableCell className="text-right font-mono text-xs">
                {formatCost(run.total_cost_usd)}
              </TableCell>
              <TableCell className="text-right font-mono text-xs">
                {formatTokens(
                  (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0),
                )}
              </TableCell>
              <TableCell className="text-right text-xs text-gray-500">
                {formatDuration(run.duration_ms)}
              </TableCell>
              <TableCell className="text-right text-xs text-gray-400">
                {run.started_at ? formatAge(run.started_at) : '—'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
