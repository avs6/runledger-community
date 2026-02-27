import Link from 'next/link'
import type { UserSpend } from '@/types/api'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

function fmt$$(value: string): string {
  const n = parseFloat(value)
  if (n >= 1) return `$${n.toFixed(2)}`
  if (n >= 0.001) return `$${n.toFixed(4)}`
  return `$${n.toFixed(6)}`
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

interface Props {
  items: UserSpend[]
}

export default function TopSpendersTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No user spend data for this period
      </p>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>User</TableHead>
          <TableHead className="text-right">Total Spend</TableHead>
          <TableHead className="text-right">Runs</TableHead>
          <TableHead className="text-right">Avg / Run</TableHead>
          <TableHead className="text-right">Last Active</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((user) => (
          <TableRow key={user.end_user_id}>
            <TableCell>
              <Link
                href={`/analytics/users/${encodeURIComponent(user.end_user_id)}`}
                className="font-medium text-indigo-600 hover:underline"
              >
                {user.end_user_id}
              </Link>
            </TableCell>
            <TableCell className="text-right font-medium">{fmt$$(user.cost_usd)}</TableCell>
            <TableCell className="text-right">{user.run_count.toLocaleString()}</TableCell>
            <TableCell className="text-right">{fmt$$(user.avg_cost_per_run)}</TableCell>
            <TableCell className="text-right text-muted-foreground">
              {fmtDate(user.last_active)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
