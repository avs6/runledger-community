import { Badge } from '@/components/ui/badge'

const variants: Record<string, string> = {
  running: 'bg-blue-100 text-blue-700 border-blue-200',
  succeeded: 'bg-green-100 text-green-700 border-green-200',
  failed: 'bg-red-100 text-red-700 border-red-200',
  cancelled: 'bg-gray-100 text-gray-600 border-gray-200',
}

export default function RunStatusBadge({ status }: { status: string }) {
  const cls = variants[status] ?? 'bg-gray-100 text-gray-600 border-gray-200'
  return (
    <Badge variant="outline" className={cls}>
      {status}
    </Badge>
  )
}
