'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutList, BarChart2, ShieldAlert, Receipt, TrendingUp, FlaskConical, ShieldCheck, Settings, Star } from 'lucide-react'

const nav = [
  { href: '/runs', label: 'Runs', icon: LayoutList },
  { href: '/analytics', label: 'Analytics', icon: BarChart2 },
  { href: '/analytics/economics', label: 'Economics', icon: TrendingUp },
  { href: '/budgets', label: 'Budgets', icon: ShieldAlert },
  { href: '/billing', label: 'Billing', icon: Receipt },
  { href: '/replay', label: 'Replay', icon: FlaskConical },
  { href: '/evaluations', label: 'Evaluations', icon: Star },
  { href: '/ledger', label: 'Ledger', icon: ShieldCheck },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex h-full w-56 flex-col border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-4">
      <div className="mb-6 px-2">
        <span className="text-lg font-semibold tracking-tight text-gray-900 dark:text-white">RunLedger</span>
      </div>
      <nav className="flex flex-col gap-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const isActive = pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 rounded-md px-2 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
              }`}
            >
              <Icon
                className={`h-4 w-4 ${
                  isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400'
                }`}
              />
              {label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
