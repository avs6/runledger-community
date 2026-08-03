import { Skeleton } from '@/components/ui/skeleton'

export default function OptimizationSimulatorLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="h-56 rounded-3xl" />
      <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 px-6 py-20">
        <Skeleton className="h-10 w-10 rounded-full" />
        <Skeleton className="mt-4 h-6 w-52" />
        <Skeleton className="mt-2 h-4 w-80" />
      </div>
    </div>
  )
}
