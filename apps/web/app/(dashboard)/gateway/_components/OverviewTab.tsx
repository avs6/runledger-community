'use client'

import Link from 'next/link'
import { useGateway } from './useGatewayState'

export function OverviewTab() {
  const {
  } = useGateway()
  return (
  <div className="space-y-3">
      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
        <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">FinOps & Spend</h3>
        <div className="flex flex-wrap gap-1.5">
        </div>
      </div>

      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
        <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">Observe & Traffic</h3>
        <div className="flex flex-wrap gap-1.5">
        </div>
      </div>

      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
        <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">Safety & Governance</h3>
        <div className="flex flex-wrap gap-1.5">
        </div>
      </div>

      <div className="rounded-lg border border-slate-200/80 dark:border-slate-700/60 bg-white/60 dark:bg-slate-900/40 p-3 space-y-2">
        <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">Build & Improve</h3>
        <div className="flex flex-wrap gap-1.5">
        </div>
      </div>

      {/* Quick nav links */}
      <div className="flex flex-wrap gap-1.5">
        {[
          { label: 'Org Settings', href: '/org-settings' },
          { label: 'Onboarding', href: '/onboarding' },
          { label: 'Users', href: '/users' },
          { label: 'Workspaces', href: '/workspace' },
          { label: 'Access Groups', href: '/access-groups' },
          { label: 'Budgets', href: '/budgets' },
          { label: 'Billing', href: '/billing' },
          { label: 'Chargeback', href: '/chargeback' },
          { label: 'Audit Log', href: '/audit' },
          { label: 'Governance', href: '/governance-pack' },
          { label: 'Analytics', href: '/analytics/users?detail=true' },
          { label: 'Platform Settings', href: '/settings' },
        ].map(({ label, href }) => (
          <Link key={label} href={href} className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors">{label}</Link>
        ))}
      </div>
    </div>
  )
}
