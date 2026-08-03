import { Skeleton } from '@/components/ui/skeleton'

export default function RequestExplorerLoading() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-44" />
          <Skeleton className="h-4 w-72" />
        </div>
        <Skeleton className="h-10 w-36" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-10 flex-1 rounded-lg" />
        <Skeleton className="h-10 w-28 rounded-lg" />
      </div>
      <div className="space-y-1">
        {[0, 1, 2, 3, 4, 5, 6, 7].map(i => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}
      </div>
    </div>
  )
}
