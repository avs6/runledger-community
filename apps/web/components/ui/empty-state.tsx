import type { ComponentType, ReactNode } from 'react'
import { Inbox } from 'lucide-react'

/** What to show when a list or section has no data: what it is and what to do next. */
export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  compact = false,
}: {
  title: string
  description?: string
  icon?: ComponentType<{ className?: string }>
  action?: ReactNode
  compact?: boolean
}) {
  return (
    <div className={`flex flex-col items-center justify-center text-center ${compact ? 'gap-1 py-6' : 'gap-2 py-12'}`}>
      <Icon className={`${compact ? 'h-5 w-5' : 'h-8 w-8'} text-slate-300 dark:text-slate-600`} aria-hidden="true" />
      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{title}</p>
      {description && <p className="max-w-sm text-xs text-slate-500 dark:text-slate-400">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
