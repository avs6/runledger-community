'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'
import { ChevronLeft, AlertTriangle } from 'lucide-react'
import { getSpendByUser, getUserCohorts, getUserAnomalies } from '@/lib/api'
import type { UserSpend, CohortSummary, AnomalyItem } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const TIER_COLOURS: Record<string, string> = {
  P0: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  P1: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  P2: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
  P3: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
}

function cohortTierFromCost(cost: string): string {
  const c = parseFloat(cost)
  if (c < 1) return 'P0'
  if (c < 10) return 'P1'
  if (c < 100) return 'P2'
  return 'P3'
}

function isWithinLastWeek(iso: string): boolean {
  const ts = new Date(iso).getTime()
  return Date.now() - ts < 7 * 24 * 3_600_000
}

type Tab = 'all' | 'heavy' | 'anomalous' | 'new'

export default function UsersPage() {
  const { data: session } = useSession()
  const [users, setUsers] = useState<UserSpend[]>([])
  const [cohorts, setCohorts] = useState<CohortSummary[]>([])
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([])
  const [tab, setTab] = useState<Tab>('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!session?.apiKey) return
    const key = session.apiKey as string
    Promise.all([
      getSpendByUser(key, 100),
      getUserCohorts(key),
      getUserAnomalies(key),
    ]).then(([usersResp, cohortsResp, anomaliesResp]) => {
      setUsers(usersResp.items)
      setCohorts(cohortsResp.items)
      setAnomalies(anomaliesResp.items)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [session?.apiKey])

  const anomalySet = new Set(anomalies.map((a) => a.end_user_id))
  const anomalyMap = new Map(anomalies.map((a) => [a.end_user_id, a]))

  const filteredUsers = users.filter((u) => {
    if (tab === 'heavy') return parseFloat(u.cost_usd) >= 100
    if (tab === 'anomalous') return anomalySet.has(u.end_user_id)
    if (tab === 'new') return u.first_seen ? isWithinLastWeek(u.first_seen) : false
    return true
  })

  const tabs: { id: Tab; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'heavy', label: 'Heavy (P3)' },
    { id: 'anomalous', label: `Anomalous${anomalies.length > 0 ? ` (${anomalies.length})` : ''}` },
    { id: 'new', label: 'New this week' },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Link
          href="/analytics"
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
        >
          <ChevronLeft className="h-4 w-4" />
          Analytics
        </Link>
        <span className="text-sm text-gray-400">/</span>
        <h1 className="text-xl font-semibold">Top Spenders</h1>
      </div>

      {/* Cohort distribution strip */}
      {cohorts.length > 0 && (
        <div className="flex gap-3">
          {cohorts.map((c) => (
            <span
              key={c.cohort_tier}
              className={`rounded-full px-3 py-1 text-xs font-medium ${TIER_COLOURS[c.cohort_tier] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}
            >
              {c.cohort_tier}: {c.user_count} users
            </span>
          ))}
        </div>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Users by Spend</CardTitle>
          {/* Segmentation tabs */}
          <div className="flex gap-1 pt-1">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                  tab === t.id
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : filteredUsers.length === 0 ? (
            <p className="text-sm text-gray-400 dark:text-gray-500">No users match this filter.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b dark:border-gray-700 text-left text-xs font-medium text-gray-500 dark:text-gray-400">
                  <th className="pb-2 pr-4">User</th>
                  <th className="pb-2 pr-4">Tier</th>
                  <th className="pb-2 pr-4">Spend</th>
                  <th className="pb-2 pr-4">Runs</th>
                  <th className="pb-2 pr-4">Calls</th>
                  <th className="pb-2">Last active</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const tier = cohortTierFromCost(u.cost_usd)
                  const isAnomaly = anomalySet.has(u.end_user_id)
                  const anomaly = anomalyMap.get(u.end_user_id)
                  return (
                    <tr key={u.end_user_id} className="border-b dark:border-gray-700 last:border-0">
                      <td className="py-2 pr-4">
                        <Link
                          href={`/analytics/users/${encodeURIComponent(u.end_user_id)}`}
                          className="font-mono text-xs hover:underline dark:text-gray-300"
                        >
                          {u.end_user_id}
                        </Link>
                      </td>
                      <td className="py-2 pr-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${TIER_COLOURS[tier]}`}
                        >
                          {tier}
                        </span>
                        {isAnomaly && (
                          <span
                            title={anomaly?.reason}
                            className="ml-1 inline-flex items-center text-amber-500"
                          >
                            <AlertTriangle className="h-3 w-3" />
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 dark:text-gray-200">${parseFloat(u.cost_usd).toFixed(4)}</td>
                      <td className="py-2 pr-4 dark:text-gray-200">{u.run_count}</td>
                      <td className="py-2 pr-4 dark:text-gray-200">{u.call_count}</td>
                      <td className="py-2 text-gray-400 dark:text-gray-500">
                        {u.last_active
                          ? new Date(u.last_active).toLocaleDateString()
                          : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
