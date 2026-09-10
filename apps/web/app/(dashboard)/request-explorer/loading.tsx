import { Skeleton } from '@/components/ui/skeleton'

export default function RequestExplorerLoading() {
  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <Skeleton className="h-8 w-52" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="flex gap-1.5">
          <Skeleton className="h-7 w-20 rounded-lg" />
          <Skeleton className="h-7 w-16 rounded-lg" />
          <Skeleton className="h-7 w-28 rounded-lg" />
        </div>
      </div>

      <Skeleton className="h-10 w-full rounded-xl" />

      <div className="flex flex-wrap items-center gap-1.5">
        {[0, 1, 2, 3].map(i => (
          <Skeleton key={i} className="h-7 w-28 rounded-lg" />
        ))}
        <Skeleton className="ml-auto h-4 w-32" />
      </div>

      <div className="grid gap-3 xl:grid-cols-[280px_1fr]">
        <div className="space-y-1">
          {[0, 1, 2, 3, 4, 5, 6, 7].map(i => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-[600px] rounded-xl" />
      </div>

      <div className="grid gap-2 lg:grid-cols-3">
        {[0, 1, 2].map(i => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    </div>
  )
}
