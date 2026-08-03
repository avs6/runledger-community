import { type LucideIcon, BarChart3 } from 'lucide-react'

interface DashboardEmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
}

export default function DashboardEmptyState({
  icon: Icon = BarChart3,
  title,
  description,
}: DashboardEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-16 text-center dark:border-slate-700 dark:bg-slate-950/30">
      <Icon className="h-10 w-10 text-slate-400 dark:text-slate-500" />
      <h3 className="mt-4 text-base font-semibold text-slate-700 dark:text-slate-300">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-md text-sm text-slate-500 dark:text-slate-400">{description}</p>
      )}
    </div>
  )
}
