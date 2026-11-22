import Link from 'next/link'
import type { ComponentType, ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'

export interface Crumb {
  label: string
  href?: string
}

/** Standard page header: breadcrumbs, title, one-line description and actions on the right. */
export function PageHeader({
  title,
  description,
  icon: Icon,
  breadcrumbs,
  actions,
}: {
  title: ReactNode
  description?: ReactNode
  icon?: ComponentType<{ className?: string }>
  breadcrumbs?: Crumb[]
  actions?: ReactNode
}) {
  return (
    <header className="space-y-1">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
            {breadcrumbs.map((c, i) => (
              <li key={`${c.label}-${i}`} className="flex items-center gap-1">
                {i > 0 && <ChevronRight className="h-3 w-3" aria-hidden="true" />}
                {c.href ? <Link href={c.href} className="hover:text-slate-800 dark:hover:text-slate-200">{c.label}</Link> : <span aria-current="page">{c.label}</span>}
              </li>
            ))}
          </ol>
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 shadow-sm">
              <Icon className="h-5 w-5 text-white" />
            </div>
          )}
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h1>
            {description && <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>}
          </div>
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  )
}
