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
import { formatCost, formatTokens, formatDuration, formatAge, formatTimestamp, truncateId } from '@/lib/utils'

export default function RunsTable({ items }: { items: RunListItem[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-200 py-16 text-center text-sm text-gray-400 dark:border-gray-700 dark:text-gray-500">
        No runs found.
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <Table>
        <TableHeader>
          <TableRow className="border-gray-200 text-xs dark:border-gray-700">
            <TableHead className="text-gray-600 dark:text-gray-400">Run ID</TableHead>
            <TableHead className="text-gray-600 dark:text-gray-400">Status</TableHead>
            <TableHead className="text-gray-600 dark:text-gray-400">End User</TableHead>
            <TableHead className="text-gray-600 dark:text-gray-400">Feature</TableHead>
            <TableHead className="text-gray-600 dark:text-gray-400">Model</TableHead>
            <TableHead className="text-right text-gray-600 dark:text-gray-400">Cost</TableHead>
            <TableHead className="text-right text-gray-600 dark:text-gray-400">Tokens</TableHead>
            <TableHead className="text-right text-gray-600 dark:text-gray-400">Duration</TableHead>
            <TableHead className="text-right text-gray-600 dark:text-gray-400">Started</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((run) => (
            <TableRow
              key={run.id}
              className="border-gray-100 text-sm hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
            >
              <TableCell className="font-mono">
                <Link
                  href={`/runs/${run.id}`}
                  title={run.id}
                  className="text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  {truncateId(run.id, 12)}
                </Link>
              </TableCell>
              <TableCell>
                <RunStatusBadge status={run.status} />
              </TableCell>
              <TableCell className="text-gray-600 dark:text-gray-400">
                {run.end_user_id ?? '—'}
              </TableCell>
              <TableCell className="text-gray-600 dark:text-gray-400">
                {run.feature_tag ?? '—'}
              </TableCell>
              <TableCell className="font-mono text-xs text-gray-500 dark:text-gray-400">
                {run.primary_model ?? '—'}
              </TableCell>
              <TableCell className="text-right font-mono text-xs text-gray-900 dark:text-gray-100">
                {formatCost(run.total_cost_usd)}
              </TableCell>
              <TableCell className="text-right font-mono text-xs text-gray-900 dark:text-gray-100">
                {formatTokens(
                  (run.total_input_tokens ?? 0) + (run.total_output_tokens ?? 0),
                )}
              </TableCell>
              <TableCell className="text-right text-xs text-gray-500 dark:text-gray-400">
                {formatDuration(run.duration_ms)}
              </TableCell>
              <TableCell className="text-right text-xs text-gray-400 dark:text-gray-500">
                {run.started_at ? (
                  <span title={formatAge(run.started_at)}>
                    {formatTimestamp(run.started_at)}
                  </span>
                ) : '—'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
