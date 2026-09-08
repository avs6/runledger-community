'use client'

import { useState, type ReactNode } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { BarChart3, List, MessageSquare } from 'lucide-react'

type Tab = 'overview' | 'runs' | 'sessions'

const VALID_TABS: Tab[] = ['overview', 'runs', 'sessions']

export default function RunsTabs({
  overview,
  runs,
  sessions,
}: {
  overview: ReactNode
  runs: ReactNode
  sessions?: ReactNode
}) {
  const searchParams = useSearchParams()
  const router = useRouter()
  const pathname = usePathname()
  const paramTab = searchParams.get('tab') as Tab | null
  const initialTab: Tab = paramTab && VALID_TABS.includes(paramTab) ? paramTab : 'overview'
  const [tab, setTab] = useState<Tab>(initialTab)

  function switchTab(key: Tab) {
    setTab(key)
    const params = new URLSearchParams(searchParams.toString())
    if (key === 'overview') {
      params.delete('tab')
    } else {
      params.set('tab', key)
    }
    const qs = params.toString()
    router.replace(`${pathname}${qs ? `?${qs}` : ''}`, { scroll: false })
  }

  const tabs: { key: Tab; label: string; icon: typeof BarChart3 }[] = [
    { key: 'overview', label: 'Overview', icon: BarChart3 },
    { key: 'runs', label: 'Runs', icon: List },
    ...(sessions ? [{ key: 'sessions' as Tab, label: 'Sessions', icon: MessageSquare }] : []),
  ]

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => switchTab(key)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition ${
              tab === key
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && overview}
      {tab === 'runs' && runs}
      {tab === 'sessions' && sessions}
    </div>
  )
}
