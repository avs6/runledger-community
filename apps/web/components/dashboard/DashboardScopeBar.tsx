'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Filter, Layers } from 'lucide-react'
import { getAccessGroups } from '@/lib/api'
import type { AccessGroupResponse } from '@/types/api'
import { getDashboardWindow, type DashboardRange } from '@/lib/dashboard-window'
export { getDashboardWindow, type DashboardRange } from '@/lib/dashboard-window'

const ranges = [
  { key: '24h', label: '24h' },
  { key: '7d', label: '7d' },
  { key: '30d', label: '30d' },
  { key: '90d', label: '90d' },
] as const

export default function DashboardScopeBar({
  scope,
  context,
  activeRange,
  basePath,
  dimensions,
}: {
  scope: 'Platform' | 'Organization' | 'Workspace'
  context: string
  activeRange: DashboardRange
  basePath: string
  dimensions: string[]
}) {
  const { data: session } = useSession()
  const apiKey = (session as any)?.apiKey
  const router = useRouter()
  const searchParams = useSearchParams()

  const [accessGroups, setAccessGroups] = useState<AccessGroupResponse[]>([])

  const selectedGroupId = searchParams.get('group_id') || ''

  useEffect(() => {
    if (!apiKey) return
    let isMounted = true
    getAccessGroups(apiKey).catch(() => ({ items: [], total: 0 })).then((agRes) => {
      if (isMounted) {
        setAccessGroups(agRes.items || [])
      }
    })
    return () => {
      isMounted = false
    }
  }, [apiKey])

  function updateFilter(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString())
    if (value) {
      params.set(key, value)
    } else {
      params.delete(key)
    }
    router.push(`${basePath}?${params.toString()}`)
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900/90 space-y-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300">
            {scope} scope
          </span>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{context}</span>
          <span className="hidden text-slate-300 sm:inline dark:text-slate-700">/</span>
          <span className="text-xs text-slate-500">Live telemetry and budget telemetry filters</span>
        </div>

        {/* Time range selector */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            Time
          </span>
          <div className="flex rounded-xl bg-slate-100 dark:bg-slate-800 p-1">
            {ranges.map((range) => {
              const params = new URLSearchParams(searchParams.toString())
              params.set('range', range.key)
              return (
                <Link
                  key={range.key}
                  href={`${basePath}?${params.toString()}`}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    activeRange === range.key
                      ? 'bg-white text-blue-700 shadow-sm dark:bg-blue-600 dark:text-white'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  {range.label}
                </Link>
              )
            })}
          </div>
        </div>
      </div>

      {/* Access Group Filter Selectors */}
      <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <Filter className="h-3.5 w-3.5 text-blue-600" /> Filter By:
        </div>

        {/* Access Group Selector */}
        <div className="flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 text-slate-400" />
          <select
            value={selectedGroupId}
            onChange={(e) => updateFilter('group_id', e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
          >
            <option value="">All Access Groups</option>
            {accessGroups.map((ag) => (
              <option key={ag.id} value={ag.id}>
                Access Group: {ag.name}
              </option>
            ))}
          </select>
        </div>

        {selectedGroupId && (
          <button
            onClick={() => {
              const params = new URLSearchParams(searchParams.toString())
              params.delete('group_id')
              router.push(`${basePath}?${params.toString()}`)
            }}
            className="text-xs font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400"
          >
            Clear Filters
          </button>
        )}
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {dimensions.map((dimension) => (
          <span
            key={dimension}
            className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400"
          >
            {dimension}
          </span>
        ))}
      </div>
    </div>
  )
}
