import { Skeleton } from '@/components/ui/skeleton'

export default function OptimizationOpportunitiesLoading() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-10 w-40" />
      </div>
      <Skeleton className="h-12 w-full rounded-xl" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-24 rounded-2xl" />)}
      </div>
      <div className="space-y-4">
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-40 rounded-2xl" />)}
      </div>
    </div>
  )
}
