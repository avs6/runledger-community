'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { Building2, Users, LayoutGrid } from 'lucide-react'

interface PlatformStats {
  tenant_count: number
  user_count: number
  workspace_count: number
}

export default function AdminDashboardPage() {
  const { data: session } = useSession()
  const s = session as Record<string, unknown> | null
  const apiKey = s?.apiKey as string

  const [stats, setStats] = useState<PlatformStats | null>(null)

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    if (!apiKey) return
    fetch(`${apiBase}/platform/stats`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    })
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {})
  }, [apiKey, apiBase])

  const cards = [
    { label: 'Total Organizations', value: stats?.tenant_count ?? '—', icon: Building2, color: 'text-teal-600 bg-teal-50 dark:bg-teal-900/30' },
    { label: 'Total Users', value: stats?.user_count ?? '—', icon: Users, color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30' },
    { label: 'Total Workspaces', value: stats?.workspace_count ?? '—', icon: LayoutGrid, color: 'text-violet-600 bg-violet-50 dark:bg-violet-900/30' },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Platform Admin</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">System-wide overview and management</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800/50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white mt-1">{value}</p>
              </div>
              <div className={`rounded-xl p-3 ${color}`}>
                <Icon className="h-5 w-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-800/50">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <a href="/admin/tenants" className="flex items-center gap-3 rounded-lg border border-slate-200 p-4 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800 transition-colors">
            <Building2 className="h-5 w-5 text-teal-600" />
            <div>
              <p className="text-sm font-medium text-slate-900 dark:text-white">Manage Organizations</p>
              <p className="text-xs text-slate-500">Create, view and delete tenants</p>
            </div>
          </a>
          <a href="/admin/users" className="flex items-center gap-3 rounded-lg border border-slate-200 p-4 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800 transition-colors">
            <Users className="h-5 w-5 text-blue-600" />
            <div>
              <p className="text-sm font-medium text-slate-900 dark:text-white">Manage Users</p>
              <p className="text-xs text-slate-500">View and manage all platform users</p>
            </div>
          </a>
        </div>
      </div>
    </div>
  )
}
