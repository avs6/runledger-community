'use client'

import { useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { Bell, Building2, MessageSquare, RadioTower } from 'lucide-react'
import OrgTab from '@/components/settings/OrgTab'
import { OrgNotificationsPanel } from '@/components/settings/OrgNotificationsPanel'
import { OrgDestinationsPanel } from '@/components/settings/OrgDestinationsPanel'
import type { OrgConsoleTab } from '@/components/settings/OrgNotificationsPanel'
import { useRole } from '@/components/rbac/useRole'

const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const TABS: { id: OrgConsoleTab; label: string; icon: React.ElementType }[] = [
  { id: 'overview', label: 'Organization', icon: Building2 },
  { id: 'destinations', label: 'Destinations', icon: RadioTower },
  { id: 'email', label: 'Email', icon: Bell },
  { id: 'slack', label: 'Slack', icon: MessageSquare },
]

function normalizeTab(tab: string | null): OrgConsoleTab {
  if (tab === 'email' || tab === 'slack' || tab === 'destinations') return tab
  return 'overview'
}

export default function OrganizationPage() {
  const { data: session } = useSession()
  const { canManageOrgSettings, isPlatformAdmin } = useRole()
  const router = useRouter()
  const searchParams = useSearchParams()

  const activeTab = normalizeTab(searchParams.get('tab'))
  const apiKey = (session as { apiKey?: string } | null)?.apiKey ?? ''
  const canAccessConsole = canManageOrgSettings || isPlatformAdmin

  const setTab = (tab: OrgConsoleTab) => {
    const params = new URLSearchParams(searchParams.toString())
    if (tab === 'overview') {
      params.delete('tab')
    } else {
      params.set('tab', tab)
    }
    const query = params.toString()
    router.push(query ? `/organization?${query}` : '/organization')
  }

  const notificationTab = activeTab === 'slack' ? 'slack' : 'email'

  const tabButtonClass = useMemo(
    () => (selected: boolean) =>
      `flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
        selected
          ? 'border-violet-500 text-violet-700 dark:text-violet-400'
          : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
      }`,
    []
  )

  if (!canAccessConsole) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800">
          <Building2 className="h-7 w-7 text-slate-400 dark:text-slate-500" />
        </div>
        <h2 className="mb-1 text-base font-semibold text-slate-800 dark:text-slate-200">
          Org Admin Access Required
        </h2>
        <p className="max-w-xs text-sm text-slate-500 dark:text-slate-400">
          Contact your organization administrator to request access.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Organization Console</h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Manage your organization profile, members, workspaces, destinations, and notification settings.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-700">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={tabButtonClass(activeTab === id)}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' ? (
        <OrgTab apiKey={apiKey} apiBase={apiBase} />
      ) : activeTab === 'destinations' ? (
        <OrgDestinationsPanel />
      ) : (
        <OrgNotificationsPanel activeTab={notificationTab} onTabChange={setTab} />
      )}
    </div>
  )
}
